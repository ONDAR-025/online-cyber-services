"""
Subscription-related Celery tasks for renewals and dunning.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('subscriptions')


@shared_task(bind=True, max_retries=3)
def process_subscription_renewals(self):
    """
    Process subscription renewals that are due.
    Called hourly by Celery Beat.
    """
    from subscriptions.models import Subscription, SubscriptionRenewalAttempt
    from commerce.models import Order
    from payments.models import PaymentIntent
    
    logger.info('Starting subscription renewal processing')
    
    # Get subscriptions that need renewal
    now = timezone.now()
    subscriptions_due = Subscription.objects.filter(
        status='active',
        current_period_end__lte=now
    )
    
    renewed_count = 0
    failed_count = 0
    
    for subscription in subscriptions_due:
        try:
            # Check if renewal attempt already exists for this period
            existing_attempt = SubscriptionRenewalAttempt.objects.filter(
                subscription=subscription,
                scheduled_at__gte=subscription.current_period_end - timedelta(hours=1),
                status__in=['pending', 'processing']
            ).first()
            
            if existing_attempt:
                logger.info(f'Renewal attempt already exists for subscription {subscription.id}')
                continue
            
            # Create order for renewal
            # Note: VAT calculation is intentionally set to 0 for B2C transactions
            # as VAT is typically absorbed by the merchant in Kenya B2C e-commerce.
            # For B2B transactions, implement proper VAT calculation (16% in Kenya).
            order = Order.objects.create(
                user=subscription.user,
                status='pending',
                subtotal=subscription.price.amount,
                tax_amount=Decimal('0.00'),  # VAT absorbed by merchant for B2C
                total=subscription.price.amount
            )
            
            # Create line item
            from commerce.models import LineItem
            LineItem.objects.create(
                order=order,
                product=subscription.product,
                price=subscription.price,
                quantity=1,
                unit_price=subscription.price.amount,
                total_price=subscription.price.amount
            )
            
            # Create renewal attempt
            attempt = SubscriptionRenewalAttempt.objects.create(
                subscription=subscription,
                attempt_number=subscription.renewal_attempts.count() + 1,
                status='pending',
                order=order,
                scheduled_at=now
            )
            
            # Trigger payment (STK Push or Collect)
            from payments.tasks import initiate_subscription_payment
            initiate_subscription_payment.delay(str(attempt.id))
            
            renewed_count += 1
            logger.info(f'Initiated renewal for subscription {subscription.id}')
            
        except Exception as e:
            failed_count += 1
            logger.error(f'Failed to process renewal for subscription {subscription.id}: {str(e)}')
    
    logger.info(f'Renewal processing complete: {renewed_count} initiated, {failed_count} failed')
    return {
        'renewed': renewed_count,
        'failed': failed_count
    }


@shared_task(bind=True, max_retries=3)
def process_dunning_schedule(self):
    """
    Process dunning schedule for failed subscription renewals.
    Called every 6 hours by Celery Beat.
    """
    from subscriptions.models import Subscription, SubscriptionRenewalAttempt, DunningSchedule
    
    logger.info('Starting dunning schedule processing')
    
    # Get default dunning schedule
    dunning_schedule = DunningSchedule.objects.filter(is_active=True, is_default=True).first()
    if not dunning_schedule:
        logger.warning('No active dunning schedule found')
        return {'processed': 0}
    
    retry_days = dunning_schedule.get_retry_days()
    now = timezone.now()
    processed_count = 0
    
    # Get subscriptions in past_due status
    past_due_subscriptions = Subscription.objects.filter(status='past_due')
    
    for subscription in past_due_subscriptions:
        try:
            # Get latest failed renewal attempt
            latest_attempt = subscription.renewal_attempts.filter(
                status='failed'
            ).order_by('-created_at').first()
            
            if not latest_attempt:
                continue
            
            # Calculate days since first failure
            days_since_failure = (now - latest_attempt.created_at).days
            
            # Check if we should retry based on dunning schedule
            should_retry = False
            for retry_day in retry_days:
                if days_since_failure == retry_day:
                    should_retry = True
                    break
            
            if should_retry:
                # Create new renewal attempt
                attempt = SubscriptionRenewalAttempt.objects.create(
                    subscription=subscription,
                    attempt_number=subscription.renewal_attempts.count() + 1,
                    status='pending',
                    order=latest_attempt.order,
                    scheduled_at=now
                )
                
                # Trigger payment
                from payments.tasks import initiate_subscription_payment
                initiate_subscription_payment.delay(str(attempt.id))
                
                # Send dunning notification
                from notifications.tasks import send_dunning_notification
                send_dunning_notification.delay(str(subscription.id), attempt.attempt_number)
                
                processed_count += 1
                logger.info(f'Retry initiated for subscription {subscription.id} (attempt {attempt.attempt_number})')
            
            # Check if grace period has expired
            if subscription.grace_until and now > subscription.grace_until:
                if dunning_schedule.cancel_subscription:
                    subscription.status = 'cancelled'
                    subscription.ended_at = now
                elif dunning_schedule.downgrade_to_free:
                    subscription.status = 'unpaid'
                
                subscription.save()
                logger.info(f'Subscription {subscription.id} grace period expired')
                
        except Exception as e:
            logger.error(f'Failed to process dunning for subscription {subscription.id}: {str(e)}')
    
    logger.info(f'Dunning processing complete: {processed_count} retries initiated')
    return {'processed': processed_count}
