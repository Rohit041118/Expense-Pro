from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Employee — Expense CRUD
    path('expenses/',           views.expense_list,   name='expense_list'),
    path('expenses/new/',       views.expense_new,    name='expense_new'),
    path('expenses/<int:pk>/',  views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/',   views.expense_edit,   name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Manager
    path('manager/pending/',        views.manager_pending,      name='manager_pending'),
    path('manager/review/<int:pk>/', views.manager_review,      name='manager_review'),
    path('manager/expenses/',        views.manager_all_expenses, name='manager_all_expenses'),
]
