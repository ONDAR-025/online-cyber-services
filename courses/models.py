"""
Courses app models - Core learning content management.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Course(models.Model):
    """Main course model."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    instructor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='courses_taught')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Pricing and access
    is_free = models.BooleanField(default=False)
    requires_enrollment = models.BooleanField(default=True)
    
    # Media
    thumbnail = models.CharField(max_length=500, blank=True, help_text='Azure Blob URL')
    preview_video = models.CharField(max_length=500, blank=True, help_text='Azure Blob URL')
    
    # Metadata
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ], default='beginner')
    language = models.CharField(max_length=10, default='en')
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.title


class Tag(models.Model):
    """Tags for categorizing courses."""
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class CourseTag(models.Model):
    """Many-to-many relationship for course tags."""
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='tagged_courses')
    
    class Meta:
        unique_together = ['course', 'tag']


class Prerequisite(models.Model):
    """Course prerequisites."""
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prerequisites')
    required_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='unlocks_courses')
    is_mandatory = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['course', 'required_course']
    
    def __str__(self):
        return f"{self.required_course.title} required for {self.course.title}"


class Section(models.Model):
    """Course sections/modules."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    """Individual lessons within sections."""
    
    LESSON_TYPE_CHOICES = [
        ('video', 'Video'),
        ('document', 'Document'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPE_CHOICES, default='video')
    order = models.PositiveIntegerField(default=0)
    
    # Content
    content = models.TextField(blank=True, help_text='Text/HTML content')
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Access control
    is_preview = models.BooleanField(default=False, help_text='Available without enrollment')
    requires_previous_completion = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['section', 'order']
    
    def __str__(self):
        return f"{self.section.course.title} - {self.title}"


class Asset(models.Model):
    """Media assets for lessons (videos, documents, etc.)."""
    
    ASSET_TYPE_CHOICES = [
        ('video_hls', 'Video (HLS)'),
        ('video_mp4', 'Video (MP4)'),
        ('pdf', 'PDF Document'),
        ('doc', 'Document'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assets')
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES)
    
    # Azure Blob Storage URLs
    url = models.CharField(max_length=500, help_text='Azure Blob URL')
    thumbnail_url = models.CharField(max_length=500, blank=True)
    
    # Metadata
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text='Size in bytes')
    mime_type = models.CharField(max_length=100)
    
    # For HLS videos
    hls_manifest_url = models.CharField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.lesson.title} - {self.file_name}"


class Enrollment(models.Model):
    """Student enrollment in courses."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Access control
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Progress tracking
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['course', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


class LessonProgress(models.Model):
    """Track user progress through individual lessons."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    
    # Progress tracking
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    
    # For video lessons
    last_position_seconds = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
        indexes = [
            models.Index(fields=['enrollment', 'is_completed']),
        ]
    
    def __str__(self):
        return f"{self.enrollment.user.username} - {self.lesson.title}"

