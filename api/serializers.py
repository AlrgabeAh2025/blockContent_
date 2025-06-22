from rest_framework import serializers
from .models import CustomUser, Child, Notifications, MostUseApps, Notification
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from django.conf import settings
from io import BytesIO
from .detect import detect_image


class EncryptionHandler:
    def __init__(self):
        """
        Initializes the encryption handler with the given key.
        :param key: The key used for encryption (should be 16, 24, or 32 bytes for AES).
        """
        self.key = settings.SECRET_KEY.encode()[:32]
        self.backend = default_backend()

    def encrypt(self, data):
        """
        Encrypts the data using AES encryption and returns a Base64 encoded string.
        :param data: The data to encrypt.
        :return: The encrypted data as a Base64 string.
        """
        # Add padding to the data to ensure it's a multiple of the block size (AES block size is 128-bit = 16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode()) + padder.finalize()

        # Generate a random IV (Initialization Vector)
        iv = os.urandom(16)

        # Create AES cipher object
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()

        # Encrypt the data
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV and ciphertext
        encrypted_data = iv + ciphertext

        # Convert encrypted data to Base64 and return
        return base64.b64encode(encrypted_data).decode("utf-8")

    def decrypt(self, base64_encrypted_data):
        """
        Decrypts the Base64 encoded encrypted data using AES decryption.
        :param base64_encrypted_data: The encrypted data as a Base64 encoded string.
        :return: The decrypted data (original message).
        """
        # Decode the Base64 encoded encrypted data
        encrypted_data = base64.b64decode(base64_encrypted_data)

        # Extract the IV and ciphertext from the encrypted data
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        # Create AES cipher object
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()

        # Decrypt the data
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()

        return data.decode()  # Decode back to string


class CustomUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        error_messages={
            "blank": "اسم المستخدم لا يمكن أن يكون فارغًا.",
            "max_length": "اسم المستخدم يجب ألا يتجاوز 35 حرف.",
            "required": "اسم المستخدم مطلوب.",
        },
    )
    first_name = serializers.CharField(
        max_length=50,
        error_messages={
            "blank": "الاسم الأول لا يمكن أن يكون فارغًا.",
            "max_length": "الاسم الأول يجب ألا يتجاوز 50 حرفًا.",
            "required": "الاسم الأول مطلوب.",
        },
    )
    last_name = serializers.CharField(
        max_length=50,
        error_messages={
            "blank": "اسم العائلة لا يمكن أن يكون فارغًا.",
            "max_length": "اسم العائلة يجب ألا يتجاوز 50 حرفًا.",
            "required": "اسم العائلة مطلوب.",
        },
    )

    userType = serializers.ChoiceField(
        choices=[("0", "نوع 0"), ("1", "نوع 1")],
        error_messages={
            "invalid_choice": "نوع المستخدم غير صالح.",
            "required": "نوع المستخدم مطلوب.",
        },
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "كلمة المرور لا يمكن أن تكون فارغة.",
            "required": "كلمة المرور مطلوبة.",
        },
    )

    gender = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "يجب تحديد الجنس",
            "required": "الجنس مطلوب",
        },
    )

    encryption = EncryptionHandler()

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "first_name",
            "last_name",
            "userType",
            "password",
            "gender",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_username(self, value):
        if len(value) < 3:
            raise serializers.ValidationError(
                "اسم المستخدم يجب أن يكون على الأقل 3 أحرف."
            )
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "اسم المستخدم موجود بالفعل. الرجاء اختيار اسم آخر."
            )
        return value

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError(
                "كلمة المرور يجب أن تكون على الأقل 6 أحرف."
            )
        return value

    def validate_userType(self, value):
        if value not in ["0", "1"]:
            raise serializers.ValidationError("نوع المستخدم غير صالح.")
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    userType = serializers.CharField()
    gender = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "password",
            "gender",
        ]
        read_only_fields = [
            "id",
            "gender",
        ]

    def validate(self, data):
        user = CustomUser.objects.filter(
            username=data["username"], userType=data["userType"]
        ).first()
        if not user:
            raise serializers.ValidationError("اسم المستخدم غير صحيح")

        if not user.check_password(data["password"]):
            raise serializers.ValidationError("كلمة المرور غير صحيحة")
        data["user"] = user

        return data


class NotificationsSerializer(serializers.ModelSerializer):
    child_first_name = serializers.CharField(
        source="ChildUser.ChildUser.first_name", read_only=True
    )
    child_last_name = serializers.CharField(
        source="ChildUser.ChildUser.last_name", read_only=True
    )
    child_gender = serializers.CharField(source="ChildUser.gender", read_only=True)

    class Meta:
        model = Notifications
        fields = [
            "id",
            "ChildUser",
            "dateOfNotification",
            "child_first_name",
            "child_last_name",
            "child_gender",
            "imageOfNotification",
        ]
        read_only_fields = [
            "id",
            "child_first_name",
            "child_last_name",
            "child_gender",
        ]

    # دالة create لتحفظ الكائن
    def create(self, validated_data):
        notification = Notifications.objects.create(**validated_data)
        return notification

    def delete(self, instance):
        instance.delete()
        return {"detail": "تم الحذف بنجاح"}


class MostUseAppsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MostUseApps
        fields = ["ChildUser", "appName", "hour", "imageOfApp"]  # إضافة حقل appIcon

    # دالة create لتحفظ الكائن
    def create(self, validated_data):
        MostUseApp = MostUseApps.objects.create(**validated_data)
        return MostUseApp


class ChildSerializer(serializers.ModelSerializer):
    child_first_name = serializers.CharField(
        source="ChildUser.first_name", read_only=True
    )
    child_last_name = serializers.CharField(
        source="ChildUser.last_name", read_only=True
    )
    father_first_name = serializers.CharField(
        source="FatherUser.first_name", read_only=True
    )
    last_Connect = serializers.CharField(source="ChildUser.last_login", read_only=True)
    child_gender = serializers.CharField(source="ChildUser.gender", read_only=True)

    encryption = EncryptionHandler()

    class Meta:
        model = Child
        fields = [
            "id",
            "ChildUser",
            "child_first_name",
            "child_last_name",
            "last_Connect",
            "FatherUser",
            "father_first_name",
            "child_gender",
            "key",
        ]
        read_only_fields = [
            "id",
            "child_first_name",
            "child_last_name",
            "last_Connect",
            "father_first_name",
            "child_gender",
        ]

    def validate(self, data):
        request_method = self.context.get("request").method
        if request_method == "POST":
            key = data.get("key")
            if not key:
                raise serializers.ValidationError({"key": "المفتاح الخاص بالطفل مطلوب"})
            child = Child.objects.filter(key=key)
            if not child.exists():
                raise serializers.ValidationError(
                    {"key": "المفتاح الذي تم ادخاله غير صحيح"}
                )
            if child.first().FatherUser == data["FatherUser"]:
                raise serializers.ValidationError(
                    {"key": "انت مرتبط بهذا الطفل بالفعل"}
                )
            if child.first().FatherUser:
                raise serializers.ValidationError({"key": "هذا الطفل مرتبط بـ أب اخر"})
            try:
                key = self.encryption.decrypt(key)
                newChild = child.first()
                newChild.FatherUser = data["FatherUser"]
                newChild.save()
                data = newChild
            except Exception as e:
                raise serializers.ValidationError(
                    {"key": f"فشل التحقق من المفتاح: {str(e)}"}
                )

        elif request_method == "DELETE":
            key = data.get("key")
            if not key:
                raise serializers.ValidationError({"key": "الرجاء تحديد طفل اولا"})
            child = Child.objects.filter(key=key, FatherUser=data["FatherUser"])
            if not child.exists():
                raise serializers.ValidationError({"key": "الابن غير موجود"})
            child = child.first()
            child.FatherUser = None
            child.save()
            data = child

        return data


class ProfileImageSerializer(serializers.Serializer):
    Image = serializers.ImageField()
    username = serializers.CharField()

    def validate(self, data):
        user = CustomUser.objects.filter(username=data["username"]).first()
        if not user:
            raise serializers.ValidationError("اسم المستخدم غير صحيح")
        user.profileImage = data["Image"]
        user.save()
        data["user"] = user
        return data


class ImageContentAnalysisSerializer(serializers.Serializer):
    Image = serializers.ImageField()
    username = serializers.CharField()

    def validate(self, data):
        user = CustomUser.objects.filter(username=data["username"]).first()
        if not user:
            raise serializers.ValidationError("اسم المستخدم غير صحيح")

        # تحويل الصورة إلى ملف في الذاكرة
        image_file = data["Image"]
        memory_file = BytesIO(image_file.read())

        # تحديد مسار حفظ الصورة
        save_path = os.path.join(settings.MEDIA_ROOT, "temp_images")
        os.makedirs(save_path, exist_ok=True)  # إنشاء المجلد إذا لم يكن موجودًا

        # إنشاء اسم الملف بناءً على اسم المستخدم
        filename = f"user_{user.id}_screenshot.png"
        file_path = os.path.join(save_path, filename)

        # حفظ الصورة
        with open(file_path, "wb") as f:
            f.write(memory_file.getbuffer())

        # تمرير المسار إلى البيانات
        data["saved_file_path"] = file_path
        data["user"] = user
        result = detect_image(
            weights="best.pt",
            image_path=file_path,
            conf_thres=0.35,
            iou_thres=0.45,
            device="cpu",
        )
        if result[0]:
            notification = Notifications.objects.create(
                ChildUser=Child.objects.filter(ChildUser=user).first(),
                imageOfNotification=image_file,
            )
            notification.save()
        print(result)
        return data


class UpdateUserSerializer(serializers.Serializer):
    action = serializers.CharField(
        required=True, error_messages={"required": "حقل 'action' مطلوب."}
    )
    username = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    currentPassword = serializers.CharField(required=False)
    newPassword = serializers.CharField(required=False)
    rePassword = serializers.CharField(required=False)

    class Meta:
        fields = [
            "username",
            "first_name",
            "last_name",
            "currentPassword",
            "newPassword",
            "rePassword",
            "action",
        ]

    def validate(self, data):
        action = data.get("action")
        if action not in ["updatePersonaInfo", "updatePassword"]:
            raise serializers.ValidationError(
                {"error": f"قيمة 'action' غير صالحة: {action}"}
            )

        if action == "updatePersonaInfo":
            # تحقق من الحقول المطلوبة لتحديث المعلومات الشخصية
            if not data.get("username"):
                raise serializers.ValidationError(
                    {"username": "حقل 'username' مطلوب لتحديث المعلومات الشخصية."}
                )
            if not data.get("first_name"):
                raise serializers.ValidationError(
                    {"first_name": "حقل 'first_name' مطلوب لتحديث المعلومات الشخصية."}
                )
            if not data.get("last_name"):
                raise serializers.ValidationError(
                    {"last_name": "حقل 'last_name' مطلوب لتحديث المعلومات الشخصية."}
                )

        if action == "updatePassword":
            if not data.get("currentPassword"):
                raise serializers.ValidationError(
                    {
                        "currentPassword": "حقل 'currentPassword' مطلوب لتحديث كلمة المرور."
                    }
                )
            if not data.get("newPassword"):
                raise serializers.ValidationError(
                    {"newPassword": "حقل 'newPassword' مطلوب لتحديث كلمة المرور."}
                )
            if not data.get("rePassword"):
                raise serializers.ValidationError(
                    {"rePassword": "حقل 'rePassword' مطلوب لتحديث كلمة المرور."}
                )

        return data

    def update(self, instance, validated_data):
        action = validated_data.get("action")

        if action == "updatePersonaInfo":
            # تحديث معلومات المستخدم الشخصية
            instance.username = validated_data.get("username", instance.username)
            instance.first_name = validated_data.get("first_name", instance.first_name)
            instance.last_name = validated_data.get("last_name", instance.last_name)

        elif action == "updatePassword":
            if not instance.check_password(validated_data.get("currentPassword")):
                raise serializers.ValidationError({"password": "كلمة المرور غير صحيحة"})
            instance.set_password(validated_data["newPassword"])

        instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "user",
            "message",
            "is_read",
            "created_at",
        ]
