from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    CustomUserSerializer,
    LoginSerializer,
    NotificationsSerializer,
    MostUseAppsSerializer,
    ChildSerializer,
    UpdateUserSerializer,
    ProfileImageSerializer,
    NotificationSerializer,
    ImageContentAnalysisSerializer,
)
from .models import Notifications, CustomUser, MostUseApps, Child, Notification
from django.http import QueryDict
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
import base64
from django.core.files.base import ContentFile


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            if user.userType == "1":
                child_instance = Child.objects.filter(ChildUser=user.id).first()
                if child_instance.FatherUser:
                    return Response(
                        {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                            "username": user.username,
                            "gender": user.gender,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "profileImage": (
                                user.profileImage.url if user.profileImage else None
                            ),
                            "key": child_instance.key,
                            "father_last_name": child_instance.FatherUser.last_name,
                            "father_gender": child_instance.FatherUser.gender,
                            "father_first_name": child_instance.FatherUser.first_name,
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                            "username": user.username,
                            "gender": user.gender,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "profileImage": (
                                user.profileImage.url if user.profileImage else None
                            ),
                            "key": child_instance.key,
                        },
                        status=status.HTTP_200_OK,
                    )

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "username": user.username,
                    "gender": user.gender,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "profileImage": (
                        user.profileImage.url if user.profileImage else None
                    ),
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Signup(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            if user.userType == "1":
                child_instance = Child.objects.filter(ChildUser=user.id).first()
                return Response(
                    {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "username": user.username,
                        "gender": user.gender,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profileImage": (
                            user.profileImage.url if user.profileImage else None
                        ),
                        "key": child_instance.key,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "username": user.username,
                    "gender": user.gender,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "profileImage": (
                        request.build_absolute_uri(user.profileImage.url)
                        if user.profileImage
                        else None
                    ),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = NotificationsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Notification created successfully",  # رسالة نجاح
                    "notification": serializer.data,  # البيانات المحفوظة
                },
                status=status.HTTP_201_CREATED,
            )  # استخدام 201 بدلاً من 200 عند إنشاء بيانات جديدة
        else:
            return Response(
                {"error": serializer.errors},  # عرض الأخطاء بدلاً من error_messages
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, *args, **kwargs):
        user = request.user
        notifications = Notification.objects.filter(user=user, is_read=False)
        for noti in notifications:
            noti.is_read = True
            noti.save()
        notifications = Notifications.objects.filter(
            ChildUser__FatherUser__username=request.user.username
        )
        serializer = NotificationsSerializer(notifications, many=True)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        try:
            notification = Notifications.objects.get(
                ChildUser__FatherUser__username=request.user.username,
                id=request.data["NoteId"],
            )
            serializer = NotificationsSerializer()
            result = serializer.delete(notification)
            return Response(result, status=status.HTTP_200_OK)
        except Notifications.DoesNotExist:
            return Response(
                {"error": "العنصر غير موجود"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": f"{e}"}, status=status.HTTP_304_NOT_MODIFIED)


class MostUseAppsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        usage_data = request.data.dict()

        excluded_apps = {
            "com.flet.child_app",
            "شاشة One UI الرئيسية",
            "screenshot_recorder",
        }

        usage_data = {
            app: int(values[0])
            for app, values in usage_data.items()
            if app not in excluded_apps
        }

        total_usage = sum(usage_data.values()) or 1

        usage_percentages = {
            app: (usage / total_usage) * 100 for app, usage in usage_data.items()
        }

        user = CustomUser.objects.get(username=request.user.username)
        child = Child.objects.get(ChildUser__id=user.id)

        for app, usage in usage_data.items():
            usage_time = timedelta(minutes=usage)
            hours, remainder = divmod(usage_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            most_use_app, created = MostUseApps.objects.get_or_create(
                ChildUser=child,
                appName=app,
                defaults={
                    "hour": f"{hours:02}:{minutes:02}:00",
                },
            )

            if not created:
                most_use_app.hour = f"{hours:02}:{minutes:02}:00"
                most_use_app.save()

        return Response(
            {
                "message": "MostUseApps updated successfully",
                "usage_percentages": usage_percentages,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, *args, **kwargs):
        try:
            Father = MostUseApps.objects.filter(
                ChildUser__FatherUser=request.user.id,
                ChildUser__ChildUser=request.data["ChildUser"],
            ).order_by("-hour")
        except MostUseApps.DoesNotExist:
            return Response(
                {"error": "No data found"},
                status=status.HTTP_302_FOUND,
            )
        serializer = MostUseAppsSerializer(Father, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class Children(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        parent = request.user
        qd = QueryDict("", mutable=True)
        qd.update(
            {
                key: value[0] if isinstance(value, list) else value
                for key, value in request.data.items()
            }
        )
        qd.update({"FatherUser": parent.id})
        serializer = ChildSerializer(data=qd, context={"request": request})
        if serializer.is_valid():
            return Response({"key": "تم اضافة الطفل بنجاح"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_200_OK)

    def get(self, request):
        if "type" not in request.query_params:
            user = request.user
            children = Child.objects.filter(FatherUser=user.id)
            childrenIdes = [
                child.id for child in children
            ]
            mostUseApps = MostUseApps.objects.filter(
                ChildUser__id__in=childrenIdes
            ).order_by("-hour")[:5]

            childSerializer = ChildSerializer(children, many=True)
            mostUseAppsSerializer = MostUseAppsSerializer(mostUseApps, many=True)
            data = {}
            for index, child in enumerate(list(childSerializer.data)):
                data[index] = [child]
                apps = [
                    app
                    for app in list(mostUseAppsSerializer.data)
                    if app["ChildUser"] == child["id"]
                ]
                data[index].append(apps)
            return Response(data, status=status.HTTP_200_OK)
        else:
            user = request.user
            child_instance = Child.objects.filter(ChildUser=user.id).first()
            if child_instance.FatherUser:
                return Response(
                    {
                        "username": user.username,
                        "gender": user.gender,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profileImage": (
                            user.profileImage.url if user.profileImage else None
                        ),
                        "key": child_instance.key,
                        "father_last_name": child_instance.FatherUser.last_name,
                        "father_gender": child_instance.FatherUser.gender,
                        "father_first_name": child_instance.FatherUser.first_name,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "username": user.username,
                        "gender": user.gender,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profileImage": (
                            user.profileImage.url if user.profileImage else None
                        ),
                        "key": child_instance.key,
                    },
                    status=status.HTTP_200_OK,
                )

    def delete(self, request):
        parent = request.user
        qd = QueryDict("", mutable=True)
        qd.update(
            {
                key: value[0] if isinstance(value, list) else value
                for key, value in request.data.items()
            }
        )
        qd.update({"FatherUser": parent.id})
        serializer = ChildSerializer(data=qd, context={"request": request})
        if serializer.is_valid():
            return Response({"key": "تم ازالة الطفل"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)


class UploadProfileImage(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        request.data["username"] = request.user.username
        serializer = ProfileImageSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            return Response(
                {
                    "username": user.username,
                    "gender": user.gender,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "profileImage": (
                        user.profileImage.url if user.profileImage else None
                    ),
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ImageContentAnalysis(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # دمج بيانات المستخدم مع الملف المرسل
        request_data = request.data.copy()
        request_data["username"] = request.user.username

        # التأكد من وجود ملف مرفق
        if "file" not in request.FILES:
            return Response(
                {"error": "الصورة غير مرفقة بالطلب!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_data["Image"] = request.FILES["file"]

        serializer = ImageContentAnalysisSerializer(data=request_data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            saved_path = serializer.validated_data["saved_file_path"]

            return Response(
                {
                    "username": user.username,
                    "gender": user.gender,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "image_path": saved_path,
                    "message": "✅ تم تخزين الصورة بنجاح!",
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateUser(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UpdateUserSerializer(
            instance=request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            try:
                updated_user = serializer.save()
                return Response(
                    {
                        "username": updated_user.username,
                        "gender": updated_user.gender,
                        "first_name": updated_user.first_name,
                        "last_name": updated_user.last_name,
                        "profileImage": (
                            updated_user.profileImage.url
                            if updated_user.profileImage
                            else None
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                error_message = e.args[0] if e.args else "حدث خطأ غير متوقع."
                return Response(
                    error_message,
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        notifications = Notification.objects.filter(user=user, is_read=False)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@receiver(post_save, sender=Notifications)
def create_notification(sender, instance, created, **kwargs):
    if hasattr(instance, "ChildUser") and hasattr(instance.ChildUser, "FatherUser"):
        Notification.objects.create(
            user=instance.ChildUser.FatherUser, message=f"تم إنشاء {instance} بنجاح."
        )
