
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.views import TokenObtainPairView

from django.db.models.signals import post_save
from django.dispatch import receiver

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

import math

from main_video.models import *
from main_video.serializers import (
    CertificateSerializer,
    MyTokenObtainPairSerializer,
    UserModelSerializer,
    CourseWithProgressSerializer,
    CategoryWithCoursesSerializer,
    SectionWithAccessSerializer,
    CategoryMainSerializer,
    SectionOneSerializer,
    SectionVazifaSerializer,
    VazifaSerializer,
    VideoProgressSerializer,
    CommentSerializer,
    MissiyaOneSerializer
)

from .serializers import VideosSerializer, VideoAccessSerializer, CourseMainSerializer

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class UserViewSet(ModelViewSet):
    queryset = Users.objects.all()
    serializer_class = UserModelSerializer
    parser_classes = (FormParser, MultiPartParser)




class UserOneViewSet(ModelViewSet):
    serializer_class = UserModelSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (FormParser, MultiPartParser)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Users.objects.none()
        return Users.objects.filter(hemis_id=self.request.user.hemis_id)



from rest_framework import viewsets, permissions

from .models import (
    Group, Users, Category, Course, CourseProgress, Section, Missiya,
    Vazifa_bajarish, SectionProgress, VideoRating, Comment
)
from .serializers import (
    GroupSerializer, CourseProgressSerializer, MissiyaSerializer, VazifaBajarishSerializer, SectionProgressSerializer,
    VideoRatingSerializer
)

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    # permission_classes = [permissions.IsAuthenticated]




class CourseProgressViewSet(viewsets.ModelViewSet):
    queryset = CourseProgress.objects.all()
    serializer_class = CourseProgressSerializer
    # permission_classes = [permissions.IsAuthenticated]


class MissiyaViewSet(viewsets.ModelViewSet):
    queryset = Missiya.objects.all()
    serializer_class = MissiyaSerializer
    # permission_classes = [permissions.IsAuthenticated]

class SectionProgressViewSet(viewsets.ModelViewSet):
    queryset = SectionProgress.objects.all()
    serializer_class = SectionProgressSerializer
    permission_classes = [permissions.IsAuthenticated]


from rest_framework import viewsets


class CategoryMainViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class =CategoryMainSerializer



import django_filters
from django.db.models import Q
from .models import Course

class CourseFilter(django_filters.FilterSet):

    teacher_name = django_filters.CharFilter(method="filter_teacher_name")

    class Meta:
        model = Course
        fields = ["category", "is_blocked"]

    def filter_teacher_name(self, queryset, name, value):
        return queryset.filter(
            Q(teacher__first_name__icontains=value) |
            Q(teacher__last_name__icontains=value)
        ).distinct()


class CourseMainViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseMainSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = CourseFilter
    search_fields = [
        'title',
        'small_description',
        'author',
        'teacher__first_name',
        'teacher__last_name',
        'teacher__username',
        '=teacher__hemis_id',  # mana shu MUHIM
    ]

    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryWithCoursesSerializer

    def get_serializer_context(self):
        """Request contextini serializer'ga o'tkazish"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


from django.db import transaction


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideosSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


    @action(detail=True, methods=['post'])
    def mark_as_watched(self, request, pk=None):
        """User videoni ko'rib bo'ldi deb belgilaydi"""
        try:
            video = self.get_object()
            user = request.user

            # Video'ga kirish huquqini tekshirish
            if not video.check_video_access(user):
                return Response({
                    'success': False,
                    'error': 'Bu videoni ko‘rish huquqingiz yo‘q. Avval oldingi videoni ko‘rib bo‘lishingiz kerak.'
                }, status=status.HTTP_403_FORBIDDEN)

            # Transaction bilan birga saqlash
            with transaction.atomic():
                # VideoProgressni yangilash yoki yaratish
                video_progress, created = VideoProgress.objects.update_or_create(
                    user=user,
                    video=video,
                    defaults={
                        'is_completed': True,
                        'completed_at': timezone.now()
                    }
                )

                # Section progressni yangilash
                section = video.section
                videos_in_section = Video.objects.filter(section=section)
                completed_videos = VideoProgress.objects.filter(
                    user=user,
                    video__in=videos_in_section,
                    is_completed=True
                ).count()

                progress_percent = (
                                               completed_videos / videos_in_section.count()) * 100 if videos_in_section.count() > 0 else 0

                section_progress, _ = SectionProgress.objects.update_or_create(
                    user=user,
                    section=section
                )
                section_progress.score_percent = progress_percent
                section_progress.save()

                # Course progressni yangilash
                course = section.course
                sections_in_course = Section.objects.filter(course=course)
                completed_sections = SectionProgress.objects.filter(
                    user=user,
                    section__in=sections_in_course,
                    is_completed=True
                ).count()

                course_progress_percent = (
                                                      completed_sections / sections_in_course.count()) * 100 if sections_in_course.count() > 0 else 0

                course_progress, _ = CourseProgress.objects.update_or_create(
                    user=user,
                    course=course,
                    defaults={
                        'progress_percent': course_progress_percent,
                        'is_completed': course_progress_percent >= 100
                    }
                )

            next_video = video.get_next_video()

            return Response({
                'success': True,
                'message': 'Video muvaffaqiyatli ko‘rib bo‘ldingiz',
                'data': {
                    'video_id': video.id,
                    'video_title': video.title,
                    'is_completed': True,
                    'completed_at': timezone.now().isoformat(),
                    'section_progress': progress_percent,
                    'course_progress': course_progress_percent,
                    'next_video': {
                        'id': next_video.id if next_video else None,
                        'title': next_video.title if next_video else None,
                        'has_access': next_video.check_video_access(user) if next_video else False
                    } if next_video else None
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def mark_as_unwatched(self, request, pk=None):
        """Videoni ko'rilmagan deb belgilash"""
        try:
            video = self.get_object()
            user = request.user

            # VideoProgress ni o'chirish
            VideoProgress.objects.filter(user=user, video=video).delete()

            # Progresslarni yangilash
            section = video.section
            self._update_section_progress(user, section)
            self._update_course_progress(user, section.course)

            return Response({
                'success': True,
                'message': 'Video ko‘rilmagan deb belgilandi'
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _update_section_progress(self, user, section):
        videos = Video.objects.filter(section=section)
        total_videos = videos.count()

        if total_videos == 0:
            return

        completed_videos = VideoProgress.objects.filter(
            user=user,
            video__in=videos,
            is_completed=True
        ).count()

        progress_percent = math.floor((completed_videos / total_videos) * 100) if total_videos > 0 else 0

        section_progress, _ = SectionProgress.objects.get_or_create(
            user=user,
            section=section
        )

        section_progress.score_percent = progress_percent
        section_progress.save()


    def _update_course_progress(self, user, course):
        sections = Section.objects.filter(course=course)
        total_sections = sections.count()

        if total_sections == 0:
            return

        completed_sections = 0
        for section in sections:
            try:
                section_progress = SectionProgress.objects.get(user=user, section=section)
                if section_progress.score_percent >= 100:  # 100% progress bo'lsa
                    completed_sections += 1
            except SectionProgress.DoesNotExist:
                pass

        progress_percent = math.floor((completed_sections / total_sections) * 100) if total_sections > 0 else 0
        is_completed = progress_percent >= 100

        course_progress, _ = CourseProgress.objects.update_or_create(
            user=user,
            course=course,
            defaults={
                'progress_percent': progress_percent,
                'is_completed': is_completed,
                'completed_at': timezone.now() if is_completed else None
            }
        )
from rest_framework.decorators import action
from rest_framework.response import Response

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionWithAccessSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def videos_with_access(self, request, pk=None):
        section = self.get_object()
        videos = Video.objects.filter(section=section).order_by('order')  # order bo'yicha

        result = []
        for video in videos:
            has_access = video.check_video_access(request.user)
            progress = VideoProgress.objects.filter(user=request.user, video=video).first()
            user_progress = {
                'is_completed': progress.is_completed if progress else False,
                'completed_at': progress.completed_at if progress else None
            }

            result.append({
                'id': video.id,
                'title': video.title,
                'order': video.order,
                'has_access': has_access,
                'user_progress': user_progress,
                'is_blocked': video.is_blocked,
                'small_description': video.small_description
            })

        return Response(result)



class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseWithProgressSerializer
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['get'])
    def user_progress(self, request, pk=None):
        course = self.get_object()
        user = request.user

        try:
            progress = CourseProgress.objects.get(
                user=user,
                course=course
            )
            serializer = CourseProgressSerializer(progress)
            return Response(serializer.data)
        except CourseProgress.DoesNotExist:
            return Response({
                'progress_percent': 0,
                'is_completed': False,
                'completed_at': None
            })



class SectionOneViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related('course', 'course__category')
    serializer_class = SectionOneSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'course': ['exact'],
        'course__category': ['exact'],
    }
    search_fields = ['title', 'small_description', 'course__title', 'course__category__title']
    ordering_fields = ['order', 'created_at']
    ordering = ['order']

    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def quiz(self, request, pk=None):
        """Sectiondagi quizni olish va is_accessible tekshirish"""
        section = self.get_object()

        # ✅ TO'G'RI: OneToOneField uchun related_name='quiz' bo'lsa
        quiz = section.quiz  # section.quiz_set emas, section.quiz

        if not quiz:
            return Response({"detail": "Quiz mavjud emas"}, status=status.HTTP_404_NOT_FOUND)

        serializer = QuizSerializer(quiz, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_quiz(self, request, pk=None):
        section = self.get_object()

        # ✅ quiz_id ixtiyoriy (frontend yubormasa ham ishlaydi)
        quiz_id = request.data.get("quiz_id")

        if quiz_id:
            # Agar frontend yuborsa — sectionga tegishliligini tekshiramiz
            try:
                quiz = Quiz.objects.get(id=quiz_id, section=section)
            except Quiz.DoesNotExist:
                return Response({"error": "Quiz bu sectionga tegishli emas"}, status=404)
        else:
            # ✅ yubormasa — OneToOne bo'lgani uchun sectiondan topamiz
            quiz = Quiz.objects.filter(section=section).first()
            if not quiz:
                return Response({"detail": "Quiz mavjud emas"}, status=status.HTTP_404_NOT_FOUND)

        # Video progresslarni tekshirish
        videos = Video.objects.filter(section=section).order_by('order')
        for idx, video in enumerate(videos):
            if idx == 0:
                continue
            previous_video = videos[idx - 1]
            if not VideoProgress.objects.filter(user=request.user, video=previous_video, is_completed=True).exists():
                return Response({
                    "detail": "Avvalgi videolarni ko'rmaganingiz sababli testga kirish mumkin emas",
                    "required_video_id": previous_video.id,
                    "required_video_title": previous_video.title
                }, status=status.HTTP_403_FORBIDDEN)

        serializer = QuizSubmitSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save(quiz)

        if result.percent >= quiz.pass_percent:
            section_progress, _ = SectionProgress.objects.get_or_create(
                user=request.user,
                section=section
            )
            section_progress.is_completed = True
            section_progress.completed_at = timezone.now()
            section_progress.save()

            next_section = Section.objects.filter(
                course=section.course,
                order__gt=section.order
            ).order_by('order').first()

            if next_section:
                next_section.is_blocked = False
                next_section.save()

                first_video = Video.objects.filter(section=next_section).order_by('order').first()
                if first_video:
                    first_video.is_blocked = False
                    first_video.save()

        return Response({
            "total_questions": result.total_questions,
            "correct_answers": result.correct_answers,
            "percent": result.percent,
            "is_passed": result.is_passed,
            "pass_percent_required": quiz.pass_percent,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "message": "Test muvaffaqiyatli topshirildi" if result.is_passed else "Testdan o'tolmadingiz"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def check_quiz_status(self, request, pk=None):
        """Quiz holatini tekshirish"""
        section = self.get_object()

        try:
            quiz = section.quiz

            # Video progresslarini tekshirish
            videos = Video.objects.filter(section=section).order_by('order')
            required_videos = []
            all_watched = True

            for idx, video in enumerate(videos):
                if idx == 0:
                    continue
                previous_video = videos[idx - 1]
                if not VideoProgress.objects.filter(user=request.user, video=previous_video, is_completed=True).exists():
                    all_watched = False
                    required_videos.append({
                        "id": previous_video.id,
                        "title": previous_video.title,
                        "order": previous_video.order
                    })

            # Oldingi natijani tekshirish
            try:
                previous_result = QuizResult.objects.get(user=request.user, quiz=quiz)
                has_previous_result = True
                previous_score = previous_result.percent
                previous_passed = previous_result.is_passed
            except QuizResult.DoesNotExist:
                has_previous_result = False
                previous_score = None
                previous_passed = False

            return Response({
                "quiz_exists": True,
                "quiz_id": quiz.id,
                "can_take_quiz": all_watched,
                "all_videos_watched": all_watched,
                "required_videos": required_videos if not all_watched else [],
                "has_previous_result": has_previous_result,
                "previous_score": previous_score,
                "previous_passed": previous_passed,
                "pass_percent": quiz.pass_percent
            })

        except AttributeError:
            return Response({
                "quiz_exists": False,
                "can_take_quiz": False,
                "message": "Bu section uchun quiz mavjud emas"
            })

    @action(detail=True, methods=['get'])
    def videos(self, request, pk=None):
        """Sectiondagi videolarni access bilan olish"""
        section = self.get_object()
        videos = Video.objects.filter(section=section).order_by('order')

        video_data = []
        for video in videos:
            has_access = video.check_video_access(request.user)
            progress = VideoProgress.objects.filter(user=request.user, video=video).first()

            video_data.append({
                'id': video.id,
                'title': video.title,
                'order': video.order,
                'has_access': has_access,
                'is_completed': progress.is_completed if progress else False,
                'completed_at': progress.completed_at if progress else None,
                'is_blocked': video.is_blocked,
                'small_description': video.small_description,
                'video_file': video.video_file.url if video.video_file else None
            })

        return Response(video_data)

    @action(detail=True, methods=['get'])
    def missiyalar(self, request, pk=None):
        """Sectiondagi missiyalarni olish"""
        section = self.get_object()
        missiyalar = Missiya.objects.filter(section=section)

        serializer = MissiyaOneSerializer(missiyalar, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Section uchun user progressini olish"""
        section = self.get_object()
        user = request.user

        try:
            section_progress = SectionProgress.objects.get(user=user, section=section)
            return Response({
                'is_completed': section_progress.is_completed,
                'completed_at': section_progress.completed_at,
                'score_percent': section_progress.score_percent
            })
        except SectionProgress.DoesNotExist:
            return Response({
                'is_completed': False,
                'completed_at': None,
                'score_percent': 0
            })

    @action(detail=True, methods=['get'])
    def full_info(self, request, pk=None):
        """Section to'liq ma'lumotlari"""
        section = self.get_object()

        # Asosiy ma'lumotlar
        section_serializer = self.get_serializer(section)
        data = section_serializer.data

        # Videolar
        videos = Video.objects.filter(section=section).order_by('order')
        video_serializer = VideosSerializer(videos, many=True, context={'request': request})
        data['videos_with_access'] = video_serializer.data

        # Quiz holati
        try:
            quiz = section.quiz
            data['has_quiz'] = True
            data['quiz_id'] = quiz.id

            # Quizga kirish huquqi
            all_watched = True
            for idx, video in enumerate(videos):
                if idx == 0:
                    continue
                previous_video = videos[idx - 1]
                if not VideoProgress.objects.filter(user=request.user, video=previous_video,
                                                    is_completed=True).exists():
                    all_watched = False
                    break
            data['quiz_accessible'] = all_watched

            # ✅ Barcha urinishlarni olish
            all_results = QuizResult.objects.filter(user=request.user, quiz=quiz).order_by('-percent', 'finished_at')
            # eng yuqori natija birinchi, qolganlari tartibini saqlab beradi
            data['quiz_results'] = [
                {
                    'id': r.id,
                    'total_questions': r.total_questions,
                    'correct_answers': r.correct_answers,
                    'percent': r.percent,
                    'is_passed': r.is_passed,
                    'started_at': getattr(r, 'started_at', None),
                    'finished_at': r.finished_at
                }
                for r in all_results
            ]

        except AttributeError:
            data['has_quiz'] = False
            data['quiz_accessible'] = False
            data['quiz_results'] = []

        # Missiyalar
        missiyalar = Missiya.objects.filter(section=section)
        missiya_serializer = MissiyaOneSerializer(missiyalar, many=True)
        data['missiyalar'] = missiya_serializer.data

        # Progress
        try:
            section_progress = SectionProgress.objects.get(user=request.user, section=section)
            data['user_progress'] = {
                'is_completed': section_progress.is_completed,
                'completed_at': section_progress.completed_at,
                'score_percent': section_progress.score_percent
            }
        except SectionProgress.DoesNotExist:
            data['user_progress'] = {
                'is_completed': False,
                'completed_at': None,
                'score_percent': 0
            }

        return Response(data)


def can_start_vazifalar(user, section):

    last_video = Video.objects.filter(section=section).order_by('order').first()
    if not last_video:
        return False
    return VideoProgress.objects.filter(user=user, video=last_video, is_completed=True).exists()


def update_section_progress(user, section):
    vazifalar = Vazifa_bajarish.objects.filter(missiya__section=section)
    total_vazifalar = vazifalar.values('missiya').distinct().count()

    if total_vazifalar == 0:
        return

    approved_scores = vazifalar.filter(user=user, is_approved=True).count()
    percent = (approved_scores / total_vazifalar) * 100

    section_progress, _ = SectionProgress.objects.get_or_create(user=user, section=section)
    section_progress.score_percent = percent
    section_progress.is_completed = percent >= 80
    if section_progress.is_completed and not section_progress.completed_at:
        section_progress.completed_at = timezone.now()
    section_progress.save()

    # keyingi sectionni ochish
    if section_progress.is_completed:
        next_section = Section.objects.filter(course=section.course, order__gt=section.order).order_by('order').first()
        if next_section:
            next_section.is_blocked = False
            next_section.save()





class SectionVazifasViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionVazifaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def vazifalar(self, request, pk=None):
        """Sectiondagi vazifalarni olish"""
        section = self.get_object()

        if not can_start_vazifalar(request.user, section):
            return Response({"error": "Vazifalarni ishlash uchun avval videoni ko‘rishingiz kerak."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(section)
        return Response(serializer.data)


class VazifaBajarishViewSet(viewsets.ModelViewSet):
    queryset = Vazifa_bajarish.objects.all()
    serializer_class = VazifaBajarishSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """User vazifa javobini yuboradi"""
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # section progressni yangilash
        section = serializer.instance.missiya.section
        update_section_progress(request.user, section)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Admin vazifani tasdiqlaydi"""
        vazifa = self.get_object()
        if request.user.role != 'admin':
            return Response({"error": "Faqat admin tasdiqlashi mumkin"}, status=status.HTTP_403_FORBIDDEN)

        score = request.data.get('score', 0)
        is_approved = request.data.get('is_approved', True)

        vazifa.score = score
        vazifa.is_approved = is_approved
        vazifa.save()

        # section progressni yangilash
        section = vazifa.missiya.section
        update_section_progress(vazifa.user, section)

        return Response({"success": True, "score": vazifa.score, "is_approved": vazifa.is_approved})



class AdminVazifaApproveViewSet(viewsets.ModelViewSet):
    queryset = Vazifa_bajarish.objects.all()
    serializer_class = VazifaSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        submission = self.get_object()
        score = request.data.get('score', 0)
        is_approved = request.data.get('is_approved', True)

        submission.is_approved = is_approved
        submission.score = score
        submission.save()

        # Section progressni tekshirish
        section = submission.missiya.section
        total = section.missiya_set.count() * 1  # har bir missiya uchun 1 ball (yoki foiz)
        approved = Vazifa_bajarish.objects.filter(
            missiya__section=section,
            user=submission.user,
            is_approved=True
        ).count()

        percent = (approved / total) * 100
        if percent >= 80:
            section.unlock_next_section()

        return Response({'success': True, 'percent_completed': percent})

class VideoProgresViews(viewsets.ModelViewSet):
    queryset = VideoProgress.objects.all()
    serializer_class = VideoProgressSerializer
    permission_classes = [IsAuthenticated]
# videolarni kurilgan qilib order bilan qilish kerak



class CommentPagination(PageNumberPagination):
    page_size = 10 # har bir sahifada 5 comment
    page_size_query_param = 'page_size'  # foydalanuvchi ?page_size=10 bilan o'zgartirishi mumkin
    max_page_size = 50


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-created_at')
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CommentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['video']



class RatingPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50


class VideoRatingViewSet(viewsets.ModelViewSet):
    queryset = VideoRating.objects.all()
    serializer_class = VideoRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RatingPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['video']

    def get_queryset(self):
        """Faqat joriy userga tegishli ratinglar"""
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_authenticated:
            # Faqat o'zining ratinglarini ko'rsatish
            return queryset.filter(user=user)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Rating yaratish/yangilash"""
        video_id = request.data.get('video')

        if not video_id:
            return Response(
                {"detail": "Video ID kiritilmagan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            return Response(
                {"detail": "Video topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mavjud ratingni tekshirish
        rating, created = VideoRating.objects.update_or_create(
            user=request.user,
            video=video,
            defaults={'rating': request.data.get('rating')}
        )

        serializer = self.get_serializer(rating)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from main_video.models import Quiz, Question, QuizResult, VideoProgress, Section, SectionProgress
from main_video.serializers import QuizSubmitSerializer, QuizSerializer


class QuizViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Userning barcha quiz natijalarini ko‘rsatish"""
        user = request.user
        results = QuizResult.objects.filter(user=user).select_related('quiz', 'quiz__section')
        data = []
        for r in results:
            data.append({
                "quiz_id": r.quiz.id,
                "section_id": r.quiz.section.id,
                "section_title": r.quiz.section.title,
                "total_questions": r.total_questions,
                "correct_answers": r.correct_answers,
                "percent": r.percent,
                "is_passed": r.is_passed,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
            })
        return Response(data)


    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Frontenddan quiz javoblarini qabul qilish, ball hisoblash va natijani saqlash"""
        try:
            quiz = Quiz.objects.get(id=pk)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Video progresslarni tekshirish: barcha section videolari ko‘rilgan bo‘lishi kerak
        videos = quiz.section.video_set.all()
        for video in videos:
            if not VideoProgress.objects.filter(user=request.user, video=video, is_completed=True).exists():
                return Response({"detail": "Barcha videolarni ko‘rmaganingiz sababli testga kirish mumkin emas"},
                                status=status.HTTP_403_FORBIDDEN)

        # Javoblarni serializer orqali tekshirish
        serializer = QuizSubmitSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save(quiz)

        # Agar quiz pass bo‘lsa (60% yoki quiz.pass_percent)
        if result.percent >= quiz.pass_percent:
            # SectionProgress update
            section = quiz.section
            section_progress, _ = SectionProgress.objects.get_or_create(user=request.user, section=section)
            section_progress.is_completed = True
            section_progress.completed_at = timezone.now()
            section_progress.save()

            # Keyingi sectionni ochish
            next_section = Section.objects.filter(course=section.course, order__gt=section.order).order_by('order').first()
            if next_section:
                next_section.is_blocked = False
                next_section.save()

                # Keyingi sectiondagi birinchi video ham ochilsin
                first_video = next_section.video_set.order_by('order').first()
                if first_video:
                    first_video.is_accessible = True
                    first_video.save()

        return Response({
            "quiz_id": quiz.id,
            "section_id": quiz.section.id,
            "total_questions": result.total_questions,
            "correct_answers": result.correct_answers,
            "percent": result.percent,
            "is_passed": result.is_passed,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
        })



# main_video/views.py

class QuizResultViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user

        # faqat shu userga tegishli natijalar
        queryset = QuizResult.objects.filter(
            user=user
        ).select_related(
            'quiz',
            'quiz__section',
            'quiz__section__course'
        )

        # 🔹 section bo‘yicha filter
        section_id = request.query_params.get('section')
        if section_id:
            queryset = queryset.filter(quiz__section_id=section_id)

        data = []
        for r in queryset:
            data.append({
                "quiz_id": r.quiz.id,
                "section_id": r.quiz.section.id,
                "section_title": r.quiz.section.title,
                "course_id": r.quiz.section.course.id,
                "course_title": r.quiz.section.course.title,

                "total_questions": r.total_questions,
                "correct_answers": r.correct_answers,
                "percent": r.percent,
                "is_passed": r.is_passed,

                "started_at": r.started_at,
                "finished_at": r.finished_at,
            })

        return Response(data, status=status.HTTP_200_OK)





@receiver(post_save, sender=SectionProgress)
def create_certificate_on_course_completion(sender, instance, created, **kwargs):

    user = instance.user
    course = instance.section.course

    # Kursdagi barcha sectionlar soni
    total_sections = course.section_set.count()

    # User tomonidan tugatilgan sectionlar soni
    completed_sections = SectionProgress.objects.filter(
        user=user,
        section__course=course,
        is_completed=True
    ).count()

    # Agar barcha sectionlar tugatilgan bo‘lsa va sertifikat hali yo‘q bo‘lsa
    if total_sections > 0 and completed_sections == total_sections:
        if not Certificate.objects.filter(user=user, course=course).exists():
            Certificate.objects.create(
                user=user,
                course=course,
                category=course.category,
                completed_at=timezone.now()
            )
            print(f"Sertifikat avtomatik yaratildi: {user.hemis_id} - {course.title}")

class CertificateFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category_id')
    course = django_filters.NumberFilter(field_name='course__id')
    user = django_filters.NumberFilter(field_name='user__id')

    class Meta:
        model = Certificate
        fields = ['category', 'course', 'user']



class CertificateViewSet(viewsets.ModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CertificateFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = ['course__title', 'category__title']
    ordering_fields = ['completed_at', 'course__title']
    ordering = ['-completed_at']

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).select_related('course', 'category', 'user')

    # =========================
    # check_course action uchun swagger
    check_course_param = openapi.Parameter(
        'course_id', openapi.IN_QUERY, description="Course ID", type=openapi.TYPE_INTEGER
    )

    @swagger_auto_schema(
        method='get',
        manual_parameters=[check_course_param],
        responses={200: CertificateSerializer(many=False)}
    )
    @action(detail=False, methods=['get'])
    def check_course(self, request):
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response({'error': 'course_id kiritilishi kerak'}, status=400)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course topilmadi'}, status=404)

        user = request.user
        has_certificate = Certificate.objects.filter(user=user, course=course).exists()
        total_sections = course.section_set.count()
        completed_sections = SectionProgress.objects.filter(
            user=user, section__course=course, is_completed=True
        ).count()

        can_get_certificate = (total_sections > 0 and completed_sections == total_sections) and not has_certificate

        return Response({
            'course_id': course.id,
            'course_title': course.title,
            'has_certificate': has_certificate,
            'can_get_certificate': can_get_certificate,
            'completed_sections': completed_sections,
            'total_sections': total_sections
        })

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, description="Category ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('course', openapi.IN_QUERY, description="Course ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('user', openapi.IN_QUERY, description="User ID", type=openapi.TYPE_INTEGER),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

