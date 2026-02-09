from django.urls import path, include
from rest_framework.routers import DefaultRouter

from main_video.views import (
    MyTokenObtainPairView,
    UserViewSet,
    GroupViewSet,
    CategoryViewSet,
    CourseViewSet,
    CourseProgressViewSet,
    SectionViewSet,
    SectionProgressViewSet,
    MissiyaViewSet,
    VazifaBajarishViewSet,
    VideoViewSet,
    VideoRatingViewSet,
    CommentViewSet, CategoryMainViewSet, CourseMainViewSet, UserOneViewSet, SectionOneViewSet,
    AdminVazifaApproveViewSet, SectionVazifasViewSet, QuizViewSet, QuizResultViewSet, CertificateViewSet
)

router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet, basename='groups')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'sections', SectionViewSet, basename='sections')
router.register(r'videos', VideoViewSet, basename='videos')
router.register(r'course-progress', CourseProgressViewSet, basename='course-progress')
router.register(r'section-progress', SectionProgressViewSet, basename='section-progress')
router.register(r'missiyas', MissiyaViewSet, basename='missiyas')
router.register(r'vazifas', VazifaBajarishViewSet, basename='vazifas')
router.register(r"category_main", CategoryMainViewSet, basename='category-main')
router.register(r"course_main", CourseMainViewSet, basename='cource-main')
router.register(r"user_one",UserOneViewSet, basename='user-one')
router.register(r'section_one', SectionOneViewSet, basename='SectionOneViewSet')
router.register(r'section_vazifalar', SectionVazifasViewSet, basename='vazifalar_sections')
router.register(r'admin-vazifalar', AdminVazifaApproveViewSet, basename='admin-vazifalar')
router.register("video_progres",VideoViewSet, basename='video_progres')


router.register(r'comments', CommentViewSet, basename='comments')
router.register(r'ratings', VideoRatingViewSet, basename='rating')
router.register(r'quiz', QuizViewSet, basename='quiz'),
router.register(r'quiz-results', QuizResultViewSet, basename='quiz-results')
router.register(r'certificates', CertificateViewSet, basename='certificate')

router.register(r'certificates', CertificateViewSet, basename='certificates')

urlpatterns = [
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),

    path('api/', include(router.urls)),
]












