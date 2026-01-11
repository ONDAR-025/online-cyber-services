from django.contrib import admin
from .models import Quiz, Question, QuestionChoice, Attempt, Answer, Certificate


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'passing_score', 'issues_certificate', 'created_at')
    list_filter = ('issues_certificate', 'created_at')
    search_fields = ('title', 'course__title')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question_type', 'points', 'order')
    list_filter = ('question_type', 'quiz')
    search_fields = ('text', 'quiz__title')


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'passed', 'status', 'started_at')
    list_filter = ('status', 'passed', 'started_at')
    search_fields = ('user__username', 'quiz__title')
    date_hierarchy = 'started_at'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_number', 'user', 'course', 'issued_at')
    search_fields = ('certificate_number', 'verification_code', 'user__username')
    date_hierarchy = 'issued_at'

