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
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

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


# =========================
# QUIZ MODELLARI
# =========================
class Quiz(models.Model):
    section = models.OneToOneField(Section, related_name='quiz',on_delete=models.SET_NULL,null=True,blank=True)
    is_blocked = models.BooleanField(default=True)
    pass_percent = models.PositiveSmallIntegerField(default=60)
    time_limit = models.PositiveIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quiz - {self.section.title}"
    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("Bu quizni o‘chirish mumkin emas. Quiz sectionga biriktirilgan.")

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