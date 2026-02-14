from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from main_video.models import (
    Users, QuizResult, Question, Quiz, Certificate
)


# ----------------------------
# JWT Token Serializer
# ----------------------------
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(  user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        return data


# ----------------------------
# User Serializer
# ----------------------------
class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = '__all__'


from rest_framework import serializers
from .models import (
    Group, Users, Category, Course, CourseProgress, Section, Missiya,
    Vazifa_bajarish, SectionProgress, Video, VideoProgress, VideoRating, Comment
)


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)

    class Meta:
        model = Users
        fields = ['id', 'hemis_id', 'first_name', 'last_name', 'role', 'group']








from rest_framework import serializers
from main_video.models import Video, Comment, VideoRating, Users

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # userni hemid ko‘rsatadi

    class Meta:
        model = Comment
        fields = ['id', 'user', 'video', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class VideoRatingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = VideoRating
        fields = ['id', 'user', 'video', 'rating', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating 1 dan 5 gacha bo‘lishi kerak")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        video = validated_data['video']

        # Agar user oldin rating bergan bo‘lsa, update qilamiz
        obj, created = VideoRating.objects.update_or_create(
            user=user,
            video=video,
            defaults={'rating': validated_data['rating']}
        )
        return obj




class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'video_file', 'small_description',
            'is_blocked', 'order', 'created_at', 'updated_at'
        ]

class VazifaBajarishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vazifa_bajarish
        fields = ['id', 'file', 'description', 'score', 'is_approved', 'missiya', 'user', 'created_at']

class Missiyas(serializers.ModelSerializer):
    vazifalar = VazifaBajarishSerializer(many=True, read_only=True)  # related_name='vazifalar'

    class Meta:
        model = Missiya
        fields = ['id', 'description', 'file', 'vazifalar']

class SectionVazifaSerializer(serializers.ModelSerializer):
    missiyas = Missiyas(many=True, read_only=True)  # related_name='missiyas'

    class Meta:
        model = Section
        fields = ['id', 'title', 'course', 'small_description', 'is_blocked', 'missiyas']



class MissiyaSerializer(serializers.ModelSerializer):
    vazifalar = VazifaBajarishSerializer(source='vazifa_bajarish_set', many=True, read_only=True)

    class Meta:
        model = Missiya
        fields = ['id', 'description', 'file', 'vazifalar']



class MissiyaOneSerializer(serializers.ModelSerializer):

    class Meta:
        model = Missiya
        fields = ['id', 'description', 'file'   ]


class SectionSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(source='video_set', many=True, read_only=True)
    missiyalar = MissiyaSerializer(source='missiya_set', many=True, read_only=True)

    class Meta:
        model = Section
        fields = [
            'id', 'title', 'small_description', 'is_blocked', 'order',
            'created_at', 'updated_at', 'videos', 'missiyalar'
        ]



# -----------------------------
# COURSE SERIALIZER
# -----------------------------
class CourseSerializer(serializers.ModelSerializer):
    # teacher ManyToMany -> nested serializer, many=True
    teacher = UserSerializer(many=True, read_only=True)
    sections = SectionSerializer(source='section_set', many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'teacher', 'category', 'img', 'author',
            'video', 'is_blocked', 'small_description', 'created_at',
            'updated_at', 'sections'
        ]


class CategorySerializer(serializers.ModelSerializer):
    courses = CourseSerializer(source='course_set', many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'title', 'img',"courses", 'created_at', 'updated_at']




class CategoryMainSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()  # 🆕 qo'shildi

    class Meta:
        model = Category
        fields = ['id', 'title', 'img', 'created_at', 'updated_at', 'average_rating']  # 🆕 qo‘shildi

    def get_average_rating(self, obj):
        courses = Course.objects.filter(category=obj)

        if not courses.exists():
            return 0

        # Barcha kurslardagi barcha videolarning ratinglarini yig'ish
        all_ratings = []
        for course in courses:
            videos = Video.objects.filter(  section__course=course)
            for video in videos:
                ratings = VideoRating.objects.filter(video=video).values_list('rating', flat=True)
                all_ratings.extend(ratings)

        if not all_ratings:
            return 0

        # O'rtacha hisoblash
        average = sum(all_ratings) / len(all_ratings)
        return round(average, 2)


class CourseMainSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    has_certificate = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()  # 🆕 qo‘shildi

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "category",
            "img",
            "teachers",  # 🆕 shu yerda
            "author",
            "video",
            "is_blocked",
            "small_description",
            "created_at",
            "updated_at",
            "average_rating",
            "has_certificate"
        ]

    def get_teachers(self, obj):
        return [
            {
                "first_name": teacher.first_name,
                "last_name": teacher.last_name
            }
            for teacher in obj.teacher.all()
        ]

    def get_average_rating(self, obj):
        videos = Video.objects.filter(section__course=obj)
        if not videos.exists():
            return 0

        all_ratings = []
        for video in videos:
            ratings = VideoRating.objects.filter(
                video=video
            ).values_list('rating', flat=True)
            all_ratings.extend(ratings)

        if not all_ratings:
            return 0

        return round(sum(all_ratings) / len(all_ratings), 2)

    def get_has_certificate(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        return Certificate.objects.filter(
            user=request.user,
            course=obj
        ).exists()

# -----------------------------zz
# COURSE PROGRESS SERIALIZER
# -----------------------------
class CourseProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)


    class Meta:
        model = CourseProgress
        fields = ['id', 'user', 'course', 'progress_percent', 'is_completed', 'completed_at']


# -----------------------------
# SECTION PROGRESS SERIALIZER
# -----------------------------
class SectionProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    section = SectionSerializer(read_only=True)

    class Meta:
        model = SectionProgress
        fields = ['id', 'user', 'section', 'is_completed', 'completed_at']


class VideoProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    video = VideoSerializer(read_only=True)

    class Meta:
        model = VideoProgress
        fields = ['id', 'user', 'video', 'is_completed', 'completed_at']
        read_only_fields = ['user', 'video']

    def create(self, validated_data):
        # Avtomatik user ni qo'shish
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

# serializers.py ga qo'shimcha

from django.utils import timezone


class VideoAccessSerializer(serializers.Serializer):
    """Video'ga kirish huquqini tekshirish uchun"""
    has_access = serializers.BooleanField()
    message = serializers.CharField()
    next_video_id = serializers.IntegerField(required=False)



from django.db.models import Avg

class VideosSerializer(serializers.ModelSerializer):
    is_accessible = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()  # 🆕 yangi field
    user_rating = serializers.SerializerMethodField()  # ✅ QO‘SHILDI

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'video_file',
            'section',
            'small_description',
            'order',
            'is_accessible',
            'user_progress',
            'user_rating',  # ✅ QO‘SHILDI
            'average_rating',
            'created_at',
            'updated_at'
        ]

    def get_user_rating(self, obj):
            request = self.context.get('request')
            if not request or not request.user.is_authenticated:
                return None

            rating = VideoRating.objects.filter(
                video=obj,
                user=request.user
            ).first()

            return rating.rating if rating else None

    def get_is_accessible(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.check_video_access(request.user)

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return {
                'is_completed': False,
                'completed_at': None
            }

        progress = VideoProgress.objects.filter(
            user=request.user,
            video=obj
        ).first()

        if not progress:
            return {
                'is_completed': False,
                'completed_at': None
            }

        return {
            'is_completed': progress.is_completed,
            'completed_at': progress.completed_at
        }

    def get_average_rating(self, obj):
        """
        Video uchun barcha ratinglarning o'rtachasi
        """
        avg = VideoRating.objects.filter(video=obj).aggregate(avg_rating=Avg('rating'))['avg_rating']
        if avg is None:
            return 0  # agar hali rating berilmagan bo'lsa
        return round(avg, 2)  # 2 ta onlik raqam bilan




class SectionWithAccessSerializer(serializers.ModelSerializer):
    """User uchun bo'limdagi videolarni access bilan"""
    videos = VideosSerializer(many=True, read_only=True)
    accessible_videos_count = serializers.SerializerMethodField()
    total_videos_count = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = [
            'id', 'title', 'course', 'small_description', 'is_blocked',
            'order', 'videos', 'accessible_videos_count', 'total_videos_count',
            'created_at', 'updated_at'
        ]

    def get_videos(self, obj):
        request = self.context.get('request')
        videos = Video.objects.filter(section=obj).order_by('order')

        if request and request.user.is_authenticated:
            serializer = VideosSerializer(
                videos,
                many=True,
                context={'request': request}
            )
            return serializer.data
        return []


    def get_accessible_videos_count(self, obj):
        """User uchun ochiq videolar soni"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            count = 0
            videos = Video.objects.filter(section=obj)
            for video in videos:
                if video.check_video_access(request.user):
                    count += 1
            return count
        return 0

    def get_total_videos_count(self, obj):
        """Jami videolar soni"""
        return Video.objects.filter(section=obj).count()

from django.db.models import Avg

class CourseWithProgressSerializer(serializers.ModelSerializer):
    """Kursni progress bilan birga, videolar o'rtacha rating bilan"""
    sections = serializers.SerializerMethodField()
    total_progress = serializers.SerializerMethodField()
    average_video_rating = serializers.SerializerMethodField()  # 🆕 yangi field
    teacher = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'teacher', 'category', 'img', 'author',
            'video', 'is_blocked', 'small_description', 'sections',
            'total_progress', 'average_video_rating',  # 🆕 qo‘shildi
            'created_at', 'updated_at'
        ]

    def get_sections(self, obj):
        """Kursning bo'limlari"""
        request = self.context.get('request')
        sections = Section.objects.filter(course=obj).order_by('order')

        if request and request.user.is_authenticated:
            serializer = SectionWithAccessSerializer(
                sections,
                many=True,
                context={'request': request}
            )
            return serializer.data
        return []

    def get_total_progress(self, obj):
        """Kurs bo'yicha umumiy progress"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = CourseProgress.objects.get(
                    user=request.user,
                    course=obj
                )
                return progress.progress_percent
            except CourseProgress.DoesNotExist:
                return 0
        return 0

    def get_average_video_rating(self, obj):
        """Kursdagi barcha videolarning o'rtacha ratingini hisoblash"""
        videos = Video.objects.filter(section__course=obj)
        # related_name bo‘yicha to‘g‘riladik
        avg = videos.aggregate(avg_rating=Avg('ratings__rating'))['avg_rating']
        if avg is None:
            return 0
        return round(avg, 2)



class CategoryWithCoursesSerializer(serializers.ModelSerializer):
    """Kategoriya va kurslari"""
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'title', 'img', 'courses', 'created_at', 'updated_at'
        ]

    def get_courses(self, obj):
        request = self.context.get('request')
        courses = Course.objects.filter(category=obj)

        serializer = CourseWithProgressSerializer(
            courses,
            many=True,
            context={'request': request}
        )
        return serializer.data

# =========================
# Question Serializer
# =========================
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'question', 'option1', 'option2', 'option3', 'option4', 'correct_answer'
        ]
        read_only_fields = ['correct_answer']  # frontendga javoblar yuborilmasin

    # Frontendga faqat savol va variantlar
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['options'] = [
            {'value': '1', 'text': rep.pop('option1')},
            {'value': '2', 'text': rep.pop('option2')},
            {'value': '3', 'text': rep.pop('option3')},
            {'value': '4', 'text': rep.pop('option4')},
        ]
        return rep

from django.db.models import Case, When, IntegerField
from django.utils import timezone
from main_video.models import QuizSession

class QuizSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    is_accessible = serializers.SerializerMethodField()
    user_result = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'section', 'is_blocked', 'time_limit', 'pass_percent',
            'questions', 'is_accessible', 'user_result'
        ]

    def get_questions(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        user = request.user

        # ✅ user uchun session yaratib/olib, o‘sha session savollarini qaytaramiz
        session = QuizSession.objects.get_or_create_active(user=user, quiz=obj)
        ids = session.question_ids or []

        if not ids:
            return []

        # ✅ random tartib saqlansin (ids tartibini DBda ham shunday order qilamiz)
        order_case = Case(
            *[When(id=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField()
        )

        qs = obj.questions.filter(id__in=ids).order_by(order_case)
        return QuestionSerializer(qs, many=True).data

    def get_is_accessible(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False

        videos = obj.section.video_set.all()
        for video in videos:
            if not VideoProgress.objects.filter(user=user, video=video, is_completed=True).exists():
                return False
        return True

    def get_user_result(self, obj):
        user = self.context.get('request').user
        try:
            result = QuizResult.objects.get(user=user, quiz=obj)
            return {
                'total_questions': result.total_questions,
                'correct_answers': result.correct_answers,
                'percent': result.percent,
                'is_passed': result.is_passed,
                'started_at': result.started_at,
                'finished_at': result.finished_at,
            }
        except QuizResult.DoesNotExist:
            return None

class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate(self, attrs):
        if not self.context.get('request').user.is_authenticated:
            raise serializers.ValidationError("User autentifikatsiya qilinmagan")
        return attrs

    def save(self, quiz):
        user = self.context.get('request').user
        answers = self.validated_data['answers']

        # ✅ active sessionni olamiz (quizda userga yuborilgan random savollar)
        session = QuizSession.objects.filter(user=user, quiz=quiz, is_submitted=False).order_by('-created_at').first()
        if not session or not session.question_ids:
            raise serializers.ValidationError("Quiz savollari topilmadi. Quizni qayta ochib kiring.")

        question_ids = session.question_ids
        total_questions = len(question_ids)

        # ✅ answers -> dict (question_id => answer)
        answers_map = {}
        for item in answers:
            if 'question_id' not in item or 'answer' not in item:
                raise serializers.ValidationError("Har bir javobda question_id va answer bo‘lishi kerak")

            try:
                qid = int(item['question_id'])
            except (TypeError, ValueError):
                raise serializers.ValidationError("question_id noto‘g‘ri")

            if qid in answers_map:
                raise serializers.ValidationError("Bir savolga 2 marta javob yuborilgan")

            answers_map[qid] = str(item['answer'])

        # ✅ Faqat sessiondagi savollar qabul qilinadi (cheat bo‘lmasin)
        extra_ids = [qid for qid in answers_map.keys() if qid not in question_ids]
        if extra_ids:
            raise serializers.ValidationError("Yuborilgan javoblar orasida sessionga kirmaydigan savollar bor")

        # ✅ Correct answerlarni bitta query bilan olamiz
        qs = quiz.questions.filter(id__in=question_ids).values_list('id', 'correct_answer')
        correct_map = {qid: str(ca) for qid, ca in qs}

        correct_answers = 0
        for qid in question_ids:
            user_answer = answers_map.get(qid)  # javob bermagan bo‘lsa None -> noto‘g‘ri hisoblanadi
            if user_answer is not None and correct_map.get(qid) == str(user_answer):
                correct_answers += 1

        percent = (correct_answers / total_questions) * 100 if total_questions else 0
        is_passed = percent >= quiz.pass_percent
        now = timezone.now()

        result, created = QuizResult.objects.update_or_create(
            user=user,
            quiz=quiz,
            defaults={
                'total_questions': total_questions,
                'correct_answers': correct_answers,
                'percent': percent,
                'is_passed': is_passed,
                'started_at': session.created_at,
                'finished_at': now,
            }
        )

        # ✅ sessionni yopamiz (keyingi urinishda yangi random savollar beriladi)
        session.is_submitted = True
        session.submitted_at = now
        session.save(update_fields=['is_submitted', 'submitted_at'])

        # ✅ PASS bo‘lsa section ochish (sizdagi eski logika)
        if is_passed:
            section = quiz.section
            section_progress, _ = SectionProgress.objects.get_or_create(user=user, section=section)
            section_progress.is_completed = True
            section_progress.completed_at = now
            section_progress.save()

            next_section = Section.objects.filter(course=section.course, order__gt=section.order).order_by('order').first()
            if next_section:
                next_section.is_blocked = False
                next_section.save()

        return result


class SectionOneSerializer(serializers.ModelSerializer):
    videos = VideosSerializer(source='video_set', many=True, read_only=True)
    quiz = serializers.SerializerMethodField()

    category_id = serializers.IntegerField(source='course.category_id', read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "category_id",
            "title",
            "course",
            "order",
            "small_description",
            "is_blocked",
            "videos",
            "quiz",
        ]

    def get_quiz(self, obj):
        request = self.context.get('request')
        quiz = getattr(obj, 'quiz', None)  # OneToOneField orqali
        if quiz:
            serializer = QuizSerializer(quiz, context={'request': request})
            return serializer.data
        return None



class VazifaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vazifa_bajarish
        fields = ['id', 'missiya', "user",'description', 'file', 'is_approved', 'score']


# ----------------------------
# CERTIFICATE SERIALIZERS
# ----------------------------
class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    category_title = serializers.CharField(source='category.title', read_only=True)
    teacher_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id',
            'user',
            'course',
            'category',
            'student_name',
            'course_title',
            'category_title',
            'teacher_names',
            'completed_at',
            'created_at'
        ]
        read_only_fields = ['user', 'course', 'category', 'completed_at']

    def get_teacher_names(self, obj):
        teachers = obj.course.teacher.all()
        return ", ".join([f"{teacher.first_name} {teacher.last_name}" for teacher in teachers])


class CertificateGenerateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()

    def validate(self, data):
        user = self.context['request'].user
        course_id = data['course_id']

        # Course tekshirish
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course topilmadi")

        # Kurs progressini tekshirish (100% bo'lishi kerak)
        try:
            course_progress = CourseProgress.objects.get(
                user=user,
                course=course
            )
            if course_progress.progress_percent < 100:
                raise serializers.ValidationError("Kursni tugatmadingiz")
        except CourseProgress.DoesNotExist:
            raise serializers.ValidationError("Kursni boshlaganingiz yo'q")

        # Sertifikat allaqachon mavjudligini tekshirish
        if Certificate.objects.filter(user=user, course=course).exists():
            raise serializers.ValidationError("Siz allaqachon bu kurs uchun sertifikat olgansiz")

        data['user'] = user
        data['course'] = course
        return data

    def create(self, validated_data):
        user = validated_data['user']
        course = validated_data['course']

        # Course progress orqali tugatilgan vaqtni olish
        try:
            course_progress = CourseProgress.objects.get(user=user, course=course)
            completed_at = course_progress.completed_at or timezone.now()
        except CourseProgress.DoesNotExist:
            completed_at = timezone.now()

        certificate = Certificate.objects.create(
            user=user,
            course=course,
            category=course.category,
            completed_at=completed_at
        )
        return certificate
