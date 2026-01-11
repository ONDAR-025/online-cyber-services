"""
Payment-related Celery tasks.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging
import uuid

logger = logging.getLogger('payments')


@shared_task(bind=True, max_retries=3)
def initiate_subscription_payment(self, renewal_attempt_id):
    """
    Initiate payment for subscription renewal.
    
    Args:
        renewal_attempt_id: UUID of SubscriptionRenewalAttempt
    """
    from subscriptions.models import SubscriptionRenewalAttempt
    from payments.models import PaymentIntent, PaymentMethod
    from payments.providers import MPesaProvider, AirtelProvider
    
    try:
        attempt = SubscriptionRenewalAttempt.objects.get(id=renewal_attempt_id)
        subscription = attempt.subscription
        order = attempt.order
        
        # Get user's default payment method
        payment_method = PaymentMethod.objects.filter(
            user=subscription.user,
            is_default=True,
            is_active=True
        ).first()
        
        if not payment_method:
            logger.error(f'No default payment method for user {subscription.user.id}')
            attempt.status = 'failed'
            attempt.error_message = 'No default payment method'
            attempt.save()
            
            subscription.status = 'past_due'
            subscription.save()
            return
        
        # Create payment intent
        idempotency_key = f'sub_{subscription.id}_{attempt.attempt_number}_{uuid.uuid4().hex[:8]}'
        
        payment_intent = PaymentIntent.objects.create(
            order=order,
            user=subscription.user,
            amount=order.total,
            currency='KES',
            provider=payment_method.method_type if payment_method.method_type in ['mpesa', 'airtel'] else 'mpesa',
            payment_method=payment_method,
            status='created',
            next_action='stk_push' if payment_method.method_type == 'mpesa' else 'collect',
            idempotency_key=idempotency_key,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        attempt.payment_intent = payment_intent
        attempt.status = 'processing'
        attempt.save()
        
        # Initiate payment based on provider
        callback_url = f"{settings.MPESA_CALLBACK_URL}?intent_id={payment_intent.id}"
        
        if payment_method.method_type == 'mpesa':
            provider = MPesaProvider()
            response = provider.initiate_stk_push(
                phone_number=payment_method.phone_number,
                amount=order.total,
                account_reference=str(order.id)[:12],
                transaction_desc=f'Subscription renewal',
                callback_url=callback_url
            )
            
            payment_intent.checkout_request_id = response.get('CheckoutRequestID')
            payment_intent.merchant_request_id = response.get('MerchantRequestID')
            payment_intent.status = 'requires_action'
            payment_intent.save()
            
        elif payment_method.method_type == 'airtel':
            provider = AirtelProvider()
            response = provider.initiate_collect(
                phone_number=payment_method.phone_number,
                amount=order.total,
                reference=str(order.id),
                callback_url=callback_url
            )
            
            payment_intent.provider_transaction_id = response.get('data', {}).get('id', '')
            payment_intent.status = 'requires_action'
            payment_intent.save()
        
        logger.info(f'Payment initiated for renewal attempt {attempt.id}')
        
    except Exception as e:
        logger.error(f'Failed to initiate payment for renewal {renewal_attempt_id}: {str(e)}')
        try:
            attempt = SubscriptionRenewalAttempt.objects.get(id=renewal_attempt_id)
            attempt.status = 'failed'
            attempt.error_message = str(e)
            attempt.save()
        except:
            pass
        raise


@shared_task(bind=True)
def reconcile_daily_payments(self):
    """
    Nightly reconciliation of payments with provider exports.
    """
    from payments.models import Payment, WebhookEvent
    from commerce.models import Order
    
    logger.info('Starting daily payment reconciliation')
    
    yesterday = timezone.now() - timedelta(days=1)
    start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Get payments from yesterday
    payments = Payment.objects.filter(
        created_at__gte=start_of_yesterday,
        created_at__lte=end_of_yesterday
    )
    
    mismatches = []
    
    for payment in payments:
        # Check if payment has corresponding successful order
        if payment.order.status != 'paid':
            mismatches.append({
                'payment_id': str(payment.id),
                'order_id': str(payment.order.id),
                'issue': 'Order not marked as paid'
            })
        
        # Check if webhook event exists
        webhook_exists = WebhookEvent.objects.filter(
            payment=payment,
            status='processed'
        ).exists()
        
        if not webhook_exists:
            mismatches.append({
                'payment_id': str(payment.id),
                'issue': 'No processed webhook event'
            })
    
    if mismatches:
        logger.warning(f'Reconciliation found {len(mismatches)} mismatches: {mismatches}')
        
        # Send alert to admin
        from notifications.tasks import send_admin_alert
        send_admin_alert.delay(
            'Payment Reconciliation Alert',
            f'Found {len(mismatches)} payment mismatches during reconciliation'
        )
    else:
        logger.info('Payment reconciliation completed successfully with no mismatches')
    
    return {
        'total_payments': payments.count(),
        'mismatches': len(mismatches)
    }


@shared_task(bind=True)
def cleanup_expired_intents(self):
    """
    Clean up expired payment intents.
    """
    from payments.models import PaymentIntent
    
    logger.info('Starting payment intent cleanup')
    
    expired_intents = PaymentIntent.objects.filter(
        status__in=['created', 'requires_action'],
        expires_at__lt=timezone.now()
    )
    
    count = expired_intents.count()
    
    expired_intents.update(
        status='cancelled',
        error_message='Payment intent expired'
    )
    
    logger.info(f'Cleaned up {count} expired payment intents')
    return {'cleaned': count}
