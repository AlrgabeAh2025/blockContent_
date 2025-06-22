from django.contrib import admin
from .models import CustomUser , Child , Notifications , MostUseApps ,Notification
from django.contrib.auth.admin import UserAdmin

admin.site.site_header = "ادارة نظام حماية الطفل"

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "first_name", "last_name", "is_staff", "is_superuser" , 'last_login' , 'gender')
    fieldsets = (
        (None, {"fields": ("username", "password" , 'last_login')}),
        ("Personal info", {"fields": ("first_name", "last_name", "userType", 'gender')}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "userType",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    search_fields = ("username", "first_name", "last_name")
    ordering = ("username",)

    def save_model(self, request, obj, form, change):
        if not change and obj.password:  # عند إنشاء مستخدم جديد
            obj.set_password(obj.password)
        elif change and "password" in form.changed_data:  # عند تعديل كلمة المرور
            obj.set_password(obj.password)
        obj.save()


class ChildAdmin(admin.ModelAdmin):
    readonly_fields = ('key',)  # تحديد الحقل كحقل للقراءة فقط
    list_display = ('ChildUser', 'FatherUser', 'key')  # عرض الحقل في قائمة السجلات
    fields = ('ChildUser', 'FatherUser', 'key')


admin.site.register(Child, ChildAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Notifications)
admin.site.register(MostUseApps)
admin.site.register(Notification)