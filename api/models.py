# Importing the necessary models for user management and permissions from Django
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.conf import settings
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from django.utils.translation import gettext_lazy as _
from datetime import datetime

currentTime = timezone.now  # Get the current time
currentFilesTime = datetime.now()  # Get the current time


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


# Custom manager for user management
class CustomUserManager(BaseUserManager):

    # Method to create a new user
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError(
                "يجب إدخال اسم المستخدم"
            )  # Ensure the username is provided
        user = self.model(username=username, **extra_fields)  # Create a user instance
        user.set_password(password)  # Set the password
        user.save(using=self._db)  # Save the user to the database
        return user

    # Method to create a superuser (admin)
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)  # Set user as staff
        extra_fields.setdefault("userType", "2")  # Set the user type as "System Admin"
        extra_fields.setdefault("is_superuser", True)  # Set user as superuser

        if not extra_fields.get("is_staff"):
            raise ValueError(
                "المستخدم الإداري يجب أن يحتوي على is_staff"
            )  # Ensure user is staff
        if not extra_fields.get("is_superuser"):
            raise ValueError(
                "المستخدم الإداري يجب أن يحتوي على is_superuser"
            )  # Ensure user is superuser

        return self.create_user(
            username, password, **extra_fields
        )  # Create the superuser using create_user


# Custom user model
class CustomUser(AbstractBaseUser, PermissionsMixin):

    username = models.CharField(
        max_length=150, unique=True, verbose_name="اسم المستخدم"
    )  # Username field

    userType = models.CharField(
        verbose_name="نوع المستخدم",
        blank=False,
        choices=(("0", "أب"), ("1", "ابن"), ("2", "مدير النظام")),
        max_length=10,
    )  # User type field

    gender = models.CharField(
        verbose_name="الجنس",
        blank=False,
        choices=(("1", "ذكر"), ("2", "انثى")),
        default="1",
        max_length=10,
    )  # User gendeer

    first_name = models.CharField(
        max_length=30, verbose_name="الاسم الأول"
    )  # First name field

    last_name = models.CharField(
        max_length=30, verbose_name="الاسم الأخير"
    )  # Last name field

    is_active = models.BooleanField(
        default=True, verbose_name="نشط"
    )  # Active status field

    is_staff = models.BooleanField(
        default=False, verbose_name="موظف"
    )  # Staff status field

    profileImage = models.ImageField(
        verbose_name="صورة الملف الشخصي",
        null=False,
        blank=False,
        max_length=1024,
        upload_to=f"{settings.BASE_DIR}/uploads_images/profileImages/{currentFilesTime.date()}/",
        default=f"{settings.BASE_DIR}/uploads_images/profileImages/guest-user.webp",
    )  # Image associated with the notification

    objects = CustomUserManager()  # Assign custom user manager

    # Set the default username field for login
    USERNAME_FIELD = "username"
    
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
    ]  # Required fields when creating a user

    def __str__(self):
        return self.first_name  # Return the first name of the user

    class Meta:
        verbose_name = "مستخدمين"  # Model name in admin interface
        verbose_name_plural = "المستخدمين"  # Model name in plural form

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if the object is being created
        super().save(*args, **kwargs)

        # Create a Child instance if the userType is "1" and the user is new
        if is_new and self.userType == "1":
            if not Child.objects.filter(ChildUser=self).exists():
                Child.objects.create(ChildUser=self)


# Child model associated with a user
class Child(models.Model):
    ChildUser = models.OneToOneField(
        CustomUser,
        verbose_name="اختر الابن",
        on_delete=models.CASCADE,
        limit_choices_to={"userType": "1"},
        related_name="child_user",
        blank=True,
        null=True,
    )  # Linking child with a user of type "Child"

    FatherUser = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={"userType": "0"},
        related_name="father_user",
        verbose_name="الأب",
        blank=True,
        null=True,
    )  # Linking father with a user of type "Father"

    key = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.ChildUser.first_name}"  # Return the first name of the child

    class Meta:
        verbose_name = "طفل"  # Model name in admin interface
        verbose_name_plural = "الاطفال"  # Model name in plural form

    def clean(self):
        if not self.ChildUser:
            raise ValidationError(
                {"ChildUser": _("يرجى تعبئة الحقل 'ChildUser'. هذا الحقل مطلوب.")}
            )

    def save(self, *args, **kwargs):
        encryption = EncryptionHandler()
        if not self.key and self.ChildUser:
            self.key = encryption.encrypt(
                f"{self.ChildUser.pk}|{self.ChildUser.username}"
            )

        # استدعاء الحفظ الأساسي
        super().save(*args, **kwargs)


# Notifications model
class Notifications(models.Model):
    ChildUser = models.ForeignKey(
        Child, verbose_name="الابن", on_delete=models.CASCADE
    )  # Link notification to a child

    dateOfNotification = models.DateField(
        verbose_name="وقت حدوث البلاغ", blank=False, null=False, default=currentTime
    )  # Date of the notification

    imageOfNotification = models.ImageField(
        verbose_name="صورة البلاغ",
        null=False,
        blank=False,
        max_length=1024,
        upload_to=f"{settings.BASE_DIR}/uploads_images/{currentFilesTime.date()}/",
    )  # Image associated with the notification

    def __str__(self):
        return f"{self.ChildUser.ChildUser.first_name}"  # Return the first name of the child in the notification

    class Meta:
        verbose_name = "بلاغ"  # Model name in admin interface
        verbose_name_plural = "البلاغات"  # Model name in plural form


# Most used apps model for a child
class MostUseApps(models.Model):

    ChildUser = models.ForeignKey(
        Child, verbose_name="الابن", on_delete=models.CASCADE
    )  # Link app usage to a child

    imageOfApp = models.ImageField(
        verbose_name="ايقونة التطبيق",
        null=True,
        blank=True,
        max_length=1024,
        upload_to=f"{settings.BASE_DIR}/uploads_images/appsIcon/{currentFilesTime.date()}/",
    )  # Image associated with the notification

    appName = models.CharField(
        verbose_name="اسم التطبيق", blank=False, null=False, max_length=20
    )  # App name field

    hour = models.TimeField(
        verbose_name="ساعات الاستخدام", null=False, blank=False
    )  # Usage hours field

    def __str__(self):
        return f"{self.ChildUser.ChildUser.first_name} / {self.appName}"  # Return child's name and app name

    class Meta:
        verbose_name = "تطبيق اكثر استخدام"  # Model name in admin interface
        verbose_name_plural = "التطبيقات الاكثر استخدام"  # Model name in plural form


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name

    class Meta:
        verbose_name = "اشعار"
        verbose_name_plural = "اشعارات"
