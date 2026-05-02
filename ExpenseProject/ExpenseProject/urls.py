from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ExpenseApp import views as expense_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ExpenseApp.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error pages
handler404 = expense_views.handler404
handler500 = expense_views.handler500
