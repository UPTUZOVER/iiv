from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Max
from django.utils import timezone

# =========================
# GROUP & USER MODELLARI
# =========================
class Group(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Users(AbstractUser):
    hemis_id = models.CharField(max_length=255, unique=True)
    group = models.CharField(max_length=30,null=True, blank=True)

    first_name = models.CharField(max_length=255,null=True, blank=True)
    last_name = models.CharField(max_length=255,null=True, blank=True)
    third_name = models.CharField(max_length=255,null=True, blank=True)
    imgage = models.ImageField(null=True, blank=True)
    kurs = models.CharField(max_length=30,null=True, blank=True)
    avg_mark = models.DecimalField(max_digits=5, decimal_places=2, default=0,null=True, blank=True)
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    USERNAME_FIELD = 'hemis_id'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.hemis_id} ({self.role})"


# =========================
# CATEGORY & COURSE MODELLARI
# =========================
class Category(models.Model):
    title = models.CharField(max_length=255)
    img = models.ImageField(upload_to="category/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.title


class Course(models.Model):
    title = models.CharField(max_length=255)
    teacher = models.ManyToManyField(
        Users,
        limit_choices_to={'role': 'teacher'},
        blank=True,
        related_name='teaching_courses'
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    img = models.ImageField(upload_to='courses/', null=True, blank=True)
    author = models.CharField(max_length=255)
    video = models.FileField(upload_to='courses/', null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    small_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CourseProgress(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)


# =========================
# SECTION, MISSIYA, VAZIFA MODELLARI
# =========================
class Section(models.Model):
    title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    small_description = models.TextField()
    is_blocked = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.order is None:
            last_order = Section.objects.filter(course=self.course).aggregate(max_order=Max('order'))['max_order']
            self.order = (last_order or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SectionProgress(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    score_percent = models.FloatField(default=0)

    class Meta:
        unique_together = ('user', 'section')


class Missiya(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='missiyas')
    description = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to='missiya/', null=True, blank=True)


class Vazifa_bajarish(models.Model):
    file = models.FileField(upload_to='vazifalar/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    is_approved = models.BooleanField(default=False)
    missiya = models.ForeignKey(Missiya, on_delete=models.CASCADE, related_name='vazifalar')
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# =========================
# VIDEO MODELLARI
# =========================
class Video(models.Model):
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    small_description = models.TextField(null=True, blank=True)
    is_blocked = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_next_video(self):
        return Video.objects.filter(section=self.section, order__gt=self.order).order_by('order').first()

    def check_video_access(self, user):
        if user.role in ['admin', 'teacher']:
            return True

        section_videos = Video.objects.filter(section=self.section).order_by('order')
        if not section_videos.exists():
            return False

        first_video = section_videos.first()
        if self.id == first_video.id:
            return True  # birinchi video har doim ochiq

        # avvalgi videoni tekshirish
        previous_video = section_videos.filter(order__lt=self.order).order_by('-order').first()
        if not previous_video:
            return False

        return VideoProgress.objects.filter(user=user, video=previous_video, is_completed=True).exists()


class VideoProgress(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'video')


class VideoRating(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.video.title} - {self.rating} ⭐"


class Comment(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.hemis_id} - {self.comment}"


class Quiz(models.Model):
    section = models.OneToOneField(Section, related_name='quiz', on_delete=models.SET_NULL, null=True, blank=True)
    is_blocked = models.BooleanField(default=True)
    pass_percent = models.PositiveSmallIntegerField(default=60)
    time_limit = models.PositiveIntegerField(default=20)

    # ✅ ADMIN BELGILAYDI: frontendga nechta savol yuborilsin
    questions_count = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quiz - {self.section.title}"

import random
from django.db import transaction
from django.utils import timezone

class QuizSessionManager(models.Manager):
    def get_active(self, user, quiz):
        return self.filter(user=user, quiz=quiz, is_submitted=False).order_by('-created_at').first()

    def get_or_create_active(self, user, quiz):
        session = self.get_active(user, quiz)

        # Quizdagi jami savollar
        all_ids = list(quiz.questions.values_list('id', flat=True))
        k = min(int(quiz.questions_count or 0), len(all_ids))

        if session:
            # Agar admin questions_count ni o‘zgartirgan bo‘lsa yoki savollar o‘chgani bo‘lsa — yangilaymiz
            valid_ids = [qid for qid in session.question_ids if qid in all_ids]
            if len(valid_ids) != k:
                session.question_ids = random.sample(all_ids, k) if k else []
                session.save(update_fields=['question_ids', 'updated_at'])
            else:
                # hammasi joyida
                session.question_ids = valid_ids
                session.save(update_fields=['question_ids', 'updated_at'])
            return session

        # Session yo‘q bo‘lsa — yaratamiz
        selected = random.sample(all_ids, k) if k else []
        return self.create(user=user, quiz=quiz, question_ids=selected)


class QuizSession(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='quiz_sessions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='sessions')
    question_ids = models.JSONField(default=list)  # [1,5,9,...]
    is_submitted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    objects = QuizSessionManager()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'quiz', 'is_submitted', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.hemis_id} | quiz={self.quiz_id} | submitted={self.is_submitted}"



class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField(max_length=600)
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=[('1','Option1'),('2','Option2'),('3','Option3'),('4','Option4')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question


class QuizResult(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='quiz_results')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results')
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    percent = models.FloatField()
    is_passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.user.hemis_id} - {self.quiz.section.title} - {self.percent}%"










# =========================
# CERTIFICATE MODEL
# =========================
class Certificate(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')  # bir user faqat bir marta sertifikat oladi

    def __str__(self):
        return f"{self.user.hemis_id} - {self.course.title} - {self.completed_at.date()}"

    @property
    def student_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    @property
    def course_title(self):
        return self.course.title

    @property
    def category_title(self):
        return self.category.title if self.category else None

    @property
    def teacher_names(self):
        teachers = self.course.teacher.all()
        return ", ".join([f"{teacher.first_name} {teacher.last_name}" for teacher in teachers])