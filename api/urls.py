from django.urls import path
from .views import (
    Signup,
    LoginView,
    NotificationView,
    UpdateUser,
    MostUseAppsView,
    Children,
    UploadProfileImage,
    NotificationAPIView,
    ImageContentAnalysis,
)
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("signup/", Signup.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("notification/", NotificationView.as_view(), name="notification"),
    path("notifications/", NotificationAPIView.as_view(), name="notifications"),
    path("mostUseApps/", MostUseAppsView.as_view(), name="mostUseApps"),
    path("Children/", Children.as_view(), name="Children"),
    path(
        "uploadProfileImage/", UploadProfileImage.as_view(), name="uploadProfileImage"
    ),
    path("Analysis/", ImageContentAnalysis.as_view(), name="Analysis"),
    path("updateUser/", UpdateUser.as_view(), name="updateUser"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


