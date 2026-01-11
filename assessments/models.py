"""
Assessments app models - Quizzes, questions, and certificates.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json


class Quiz(models.Model):
    """Quiz/Assessment model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Quiz settings
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70.00)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    max_attempts = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited')
    randomize_questions = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=True, help_text='Show answers after completion')
    
    # Certificate
    issues_certificate = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Quizzes'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Question(models.Model):
    """Question model for quizzes."""
    
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    text = models.TextField()
    explanation = models.TextField(blank=True, help_text='Explanation shown after answering')
    
    # Points
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    
    # Order
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.quiz.title} - {self.text[:50]}"


class QuestionChoice(models.Model):
    """Answer choices for multiple choice questions."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text


class Attempt(models.Model):
    """Quiz attempt model."""
    
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    enrollment = models.ForeignKey('courses.Enrollment', on_delete=models.CASCADE, related_name='quiz_attempts')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    # Scoring
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    passed = models.BooleanField(default=False)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    
    # Attempt number
    attempt_number = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'quiz', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} (Attempt {self.attempt_number})"


class Answer(models.Model):
    """User answers for quiz questions."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    
    # Answer data (JSON for flexibility)
    selected_choice = models.ForeignKey(QuestionChoice, on_delete=models.SET_NULL, null=True, blank=True)
    answer_text = models.TextField(blank=True)  # For short answer/essay
    
    # Grading
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Timing
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.text[:50]}"


class Certificate(models.Model):
    """Certificate issued upon course/quiz completion."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='certificates')
    enrollment = models.ForeignKey('courses.Enrollment', on_delete=models.CASCADE, related_name='certificates')
    
    # Certificate details
    certificate_number = models.CharField(max_length=50, unique=True)
    
    # PDF stored in Azure Blob
    pdf_url = models.CharField(max_length=500, help_text='Azure Blob URL')
    
    # Verification
    verification_code = models.CharField(max_length=100, unique=True)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['user', '-issued_at']),
            models.Index(fields=['certificate_number']),
            models.Index(fields=['verification_code']),
        ]
    
    def __str__(self):
        return f"Certificate {self.certificate_number} - {self.user.username}"

