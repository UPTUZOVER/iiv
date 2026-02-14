from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


admin.site.register(Certificate)# Users admin
# ----------------------------
@admin.register(Users)
class UsersAdmin(UserAdmin):
    list_display = ("id",'hemis_id', 'first_name', 'last_name', 'group', 'role', 'is_staff')
    list_filter = ('role', 'group', 'is_staff', 'is_superuser')
    search_fields = ('hemis_id', 'first_name', 'last_name')
    ordering = ('hemis_id',)
    fieldsets = (
        (None, {'fields': ('hemis_id', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'group')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('hemis_id', 'first_name', 'last_name', 'group', 'role', 'password1', 'password2'),
        }),
    )

# ----------------------------
# Inline klasslar
# ----------------------------
class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    show_change_link = True

class VideoInline(admin.TabularInline):
    model = Video
    extra = 1
    show_change_link = True

class MissiyaInline(admin.TabularInline):
    model = Missiya
    extra = 1
    show_change_link = True

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

class QuizResultInline(admin.TabularInline):
    model = QuizResult
    extra = 0
    readonly_fields = ('total_questions', 'correct_answers', 'percent', 'is_passed', 'started_at', 'finished_at')
    can_delete = False
    show_change_link = True

# ----------------------------
# Section admin
# ----------------------------
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id",'title', 'course', 'order', 'is_blocked')
    list_display = ("id",'title', 'course', 'order', 'is_blocked')
    list_filter = ('is_blocked', 'course')
    search_fields = ('title', 'course__title')
    ordering = ('course', 'order')
    inlines = [VideoInline, MissiyaInline]

# ----------------------------
# Course admin
# ----------------------------
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_teachers', 'category', 'is_blocked', 'created_at')
    list_filter = ('is_blocked', 'category')
    search_fields = ('title', 'teacher__hemis_id')
    inlines = [SectionInline]

    def get_teachers(self, obj):
        return ", ".join([f"{t.first_name} {t.last_name}" for t in obj.teacher.all()])
    get_teachers.short_description = "Teachers"

# ----------------------------
# Video admin
# ----------------------------
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("id",'title', 'section', 'order', 'is_blocked')
    list_filter = ('is_blocked', 'section__course')
    search_fields = ('title', 'section__title')
    ordering = ('section', 'order')

# ----------------------------
# Missiya admin
# ----------------------------
@admin.register(Missiya)
class MissiyaAdmin(admin.ModelAdmin):
    list_display = ('section', 'description_preview')
    search_fields = ('section__title', 'description')

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return ''
    description_preview.short_description = 'Description'

# ----------------------------
# VazifaBajarish admin
# ----------------------------
@admin.register(Vazifa_bajarish)
class VazifaBajarishAdmin(admin.ModelAdmin):
    list_display = ('user', 'missiya', 'created_at')
    list_filter = ('created_at', 'user__group')
    search_fields = ('user__hemis_id', 'missiya__section__title')

# ----------------------------
# CourseProgress admin
# ----------------------------
@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'progress_percent', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'course', 'user__group')
    search_fields = ('user__hemis_id', 'course__title')

# ----------------------------
# SectionProgress admin
# ----------------------------
@admin.register(SectionProgress)
class SectionProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_section', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'user__group')
    search_fields = ('user__hemis_id', 'section__title')

    def get_section(self, obj):
        return obj.section.title
    get_section.short_description = 'Section'

# ----------------------------
# VideoProgress admin
# ----------------------------
@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_video', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'user__group')
    search_fields = ('user__hemis_id', 'video__title')

    def get_video(self, obj):
        return obj.video.title
    get_video.short_description = 'Video'

# ----------------------------
# VideoRating admin
# ----------------------------
@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display = ("id",'video', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('video__title', 'user__hemis_id')

# ----------------------------
# Comment admin
# ----------------------------
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'comment_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__hemis_id', 'comment', 'video__title')

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'

# ----------------------------
# Category admin
# ----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title',)

# ----------------------------
# Group admin


# ----------------------------
# Quiz admin with inline Questions & QuizResults
# ----------------------------
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'questions_count', 'pass_percent', 'time_limit', 'is_blocked')
    list_filter = ('is_blocked', 'section__course')
    search_fields = ('section__title',)
    inlines = [QuestionInline, QuizResultInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuizResult)
class QuizResult(admin.ModelAdmin):
    list_filter = ('finished_at', 'completed_at')




