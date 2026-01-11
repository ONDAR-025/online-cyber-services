"""
Management command to seed the database with sample data for development and testing.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta, time
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed database with sample data for Kenya LMS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        from courses.models import Course, Tag, Section, Lesson, Enrollment, CourseTag
        from commerce.models import Product, Price, Coupon
        from payments.models import ProviderAccount, PaymentMethod
        from subscriptions.models import DunningSchedule
        from notifications.models import NotificationTemplate, NotificationPreference
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            User.objects.filter(username__in=['instructor', 'learner']).delete()
            Course.objects.all().delete()
            Tag.objects.all().delete()

        self.stdout.write('Seeding database...')
        
        # Create admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@lms.co.ke',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
        
        # Create instructor
        instructor, created = User.objects.get_or_create(
            username='instructor',
            defaults={'email': 'instructor@lms.co.ke', 'is_staff': True}
        )
        if created:
            instructor.set_password('instructor123')
            instructor.save()
        
        # Create learner
        learner, created = User.objects.get_or_create(
            username='learner',
            defaults={'email': 'learner@lms.co.ke'}
        )
        if created:
            learner.set_password('learner123')
            learner.save()
        
        # Create provider accounts
        ProviderAccount.objects.get_or_create(
            tenant_name='default',
            provider='mpesa',
            defaults={
                'mpesa_shortcode': '174379',
                'mpesa_environment': 'sandbox',
                'is_active': False,
            }
        )
        
        # Create dunning schedule
        DunningSchedule.objects.get_or_create(
            name='Default',
            defaults={
                'retry_schedule': [0, 1, 3, 7],
                'grace_period_days': 7,
                'is_active': True,
                'is_default': True,
            }
        )
        
        # Create tags
        tag, _ = Tag.objects.get_or_create(name='Python', defaults={'slug': 'python'})
        
        # Create course
        course, created = Course.objects.get_or_create(
            slug='intro-to-python',
            defaults={
                'title': 'Introduction to Python',
                'description': 'Learn Python from scratch',
                'instructor': instructor,
                'status': 'published',
                'is_free': False,
                'difficulty_level': 'beginner',
            }
        )
        
        if created:
            CourseTag.objects.get_or_create(course=course, tag=tag)
            section = Section.objects.create(course=course, title='Module 1', order=1)
            Lesson.objects.create(
                section=section,
                title='Welcome to Python',
                lesson_type='video',
                order=1,
                is_preview=True
            )
        
        # Create product and price
        product, created = Product.objects.get_or_create(
            course=course,
            defaults={'name': course.title, 'product_type': 'course'}
        )
        if created:
            Price.objects.create(
                product=product,
                amount=Decimal('5000.00'),
                billing_interval='one_time'
            )
        
        # Create payment method
        PaymentMethod.objects.get_or_create(
            user=learner,
            method_type='mpesa',
            defaults={'phone_number': '254712345678', 'is_default': True}
        )
        
        # Create notification preferences
        NotificationPreference.objects.get_or_create(
            user=learner,
            defaults={
                'quiet_hours_start': time(22, 0),
                'quiet_hours_end': time(7, 0),
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Database seeded!'))
        self.stdout.write('Users: admin/admin123, instructor/instructor123, learner/learner123')
