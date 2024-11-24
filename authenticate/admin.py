from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Request, Course, ManagerRequest

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profiles'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role')
    
    def get_role(self, obj):
        return obj.userprofile.role
    get_role.short_description = 'Role'

class ManagerRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'manager', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'manager__username')

class RequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'submitted_by__username')

# Unregister and register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(ManagerRequest, ManagerRequestAdmin)
admin.site.register(Request, RequestAdmin)
admin.site.register(Course)
