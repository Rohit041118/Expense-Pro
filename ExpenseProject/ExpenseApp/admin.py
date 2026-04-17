from django.contrib import admin
from .models import UserProfile, Category, Expense


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'department', 'manager')
    list_filter   = ('role', 'department')
    search_fields = ('user__username', 'user__email', 'department')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'icon')
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display   = ('id', 'title', 'submitted_by', 'amount', 'currency', 'status', 'created_at')
    list_filter    = ('status', 'currency', 'category')
    search_fields  = ('title', 'submitted_by__username', 'description')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'reviewed_at')
    actions        = ['mark_approved', 'mark_rejected', 'mark_paid']

    def mark_approved(self, request, queryset):
        for expense in queryset.filter(status='pending'):
            expense.approve(request.user)
    mark_approved.short_description = "Approve selected expenses"

    def mark_rejected(self, request, queryset):
        for expense in queryset.filter(status='pending'):
            expense.reject(request.user, reason='Bulk rejected via admin')
    mark_rejected.short_description = "Reject selected expenses"

    def mark_paid(self, request, queryset):
        for expense in queryset.filter(status='approved'):
            expense.mark_paid()
    mark_paid.short_description = "Mark selected expenses as Paid"
