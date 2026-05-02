from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('signup/', views.signup_view, name='signup'),
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/', views.onboarding_view, name='onboarding'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Employee — Expense CRUD
    path('expenses/',                    views.expense_list,   name='expense_list'),
    path('expenses/new/',                views.expense_new,    name='expense_new'),
    path('expenses/<int:pk>/',           views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/',      views.expense_edit,   name='expense_edit'),
    path('expenses/<int:pk>/delete/',    views.expense_delete, name='expense_delete'),

    # API endpoints
    path('api/ocr-receipt/',             views.process_receipt_ocr, name='ocr_receipt'),

    # Manager
    path('manager/pending/',             views.manager_pending,      name='manager_pending'),
    path('manager/review/<int:pk>/',     views.manager_review,       name='manager_review'),
    path('manager/expenses/',            views.manager_all_expenses,  name='manager_all_expenses'),
    path('manager/expenses/export/',     views.export_expenses_csv,   name='export_expenses_csv'),

    # User Management (Admin)
    path('users/',                       views.user_management_list,   name='user_management_list'),
    path('users/new/',                   views.user_management_add,    name='user_management_add'),
    path('users/<int:pk>/edit/',         views.user_management_edit,   name='user_management_edit'),
    path('users/<int:pk>/delete/',       views.user_management_delete, name='user_management_delete'),

    # Notifications API
    path('api/notifications/',                        views.notifications_list,       name='notifications_list'),
    path('api/notifications/<int:pk>/read/',           views.notification_mark_read,   name='notification_mark_read'),
    path('api/notifications/mark-all-read/',           views.notifications_mark_all_read, name='notifications_mark_all_read'),
]
