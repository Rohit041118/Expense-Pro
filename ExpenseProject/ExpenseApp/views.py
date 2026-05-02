import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST

from django.contrib.auth.models import User
from .models import Expense, Category, UserProfile, Company, Notification
from .forms import ExpenseForm, ReviewForm, UserProfileForm, CompanySetupForm, AdminUserCreateForm, AdminUserProfileForm, AdminSignupForm
from .utils import get_exchange_rate


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def manager_required(view_func):
    """Decorator: restrict to managers/admins."""
    from functools import wraps

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not (profile and profile.is_manager):
            messages.error(request, 'Access denied. Managers only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper


def paginate(request, queryset, per_page=10):
    """Return a Page object for the given queryset."""
    paginator = Paginator(queryset, per_page)
    page_num  = request.GET.get('page', 1)
    return paginator.get_page(page_num)


# ─────────────────────────────────────────
# ─────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AdminSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name  = form.cleaned_data.get('last_name', '')
            user.email      = form.cleaned_data.get('email', '')
            user.save()
            # Promote to Admin immediately
            profile = user.profile
            profile.role = 'admin'
            profile.save()
            
            login(request, user)
            messages.success(request, 'Account created! Now set up your company.')
            return redirect('onboarding')
    else:
        form = AdminSignupForm()
        
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user:
            login(request, user)
            profile = getattr(user, 'profile', None)
            
            # Multi-tenant onboarding check
            if profile and profile.is_admin and not profile.company:
                return redirect('onboarding')
                
            return redirect(request.POST.get('next') or 'dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html', {'form': {}})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@login_required
def onboarding_view(request):
    """Admin company setup flow."""
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_admin:
        messages.error(request, 'Only administrators can perform initial setup.')
        return redirect('dashboard')
        
    if profile.company:
        messages.info(request, 'Company is already set up.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CompanySetupForm(request.POST)
        if form.is_valid():
            company = form.save()
            profile.company = company
            profile.save()
            messages.success(request, f"Welcome to ExpensePro! {company.name} setup is complete.")
            return redirect('dashboard')
    else:
        form = CompanySetupForm()

    return render(request, 'onboarding.html', {'form': form})

@login_required
def dashboard(request):
    user    = request.user
    profile = getattr(user, 'profile', None)
    is_mgr  = profile and profile.is_manager

    if is_mgr:
        pending_expenses = (
            Expense.objects
            .filter(status=Expense.STATUS_PENDING)
            .select_related('submitted_by', 'category')[:10]
        )
        total_approved  = Expense.objects.filter(status=Expense.STATUS_APPROVED).aggregate(s=Sum('base_amount'))['s'] or 0
        total_pending   = Expense.objects.filter(status=Expense.STATUS_PENDING).count()
        total_rejected  = Expense.objects.filter(status=Expense.STATUS_REJECTED).count()
        total_paid      = Expense.objects.filter(status=Expense.STATUS_PAID).aggregate(s=Sum('base_amount'))['s'] or 0
        recent_expenses = Expense.objects.all().select_related('submitted_by', 'category')[:8]
        context = {
            'is_manager':      True,
            'company':         profile.company if profile else None,
            'pending_expenses': pending_expenses,
            'total_approved':  total_approved,
            'total_pending':   total_pending,
            'total_rejected':  total_rejected,
            'total_paid':      total_paid,
            'recent_expenses': recent_expenses,
        }
    else:
        my_expenses     = Expense.objects.filter(submitted_by=user)
        total_submitted = my_expenses.exclude(status=Expense.STATUS_DRAFT).aggregate(s=Sum('base_amount'))['s'] or 0
        total_approved  = my_expenses.filter(status=Expense.STATUS_APPROVED).aggregate(s=Sum('base_amount'))['s'] or 0
        count_pending   = my_expenses.filter(status=Expense.STATUS_PENDING).count()
        count_rejected  = my_expenses.filter(status=Expense.STATUS_REJECTED).count()
        recent_expenses = my_expenses.select_related('category')[:8]
        context = {
            'is_manager':      False,
            'company':         profile.company if profile else None,
            'total_submitted': total_submitted,
            'total_approved':  total_approved,
            'count_pending':   count_pending,
            'count_rejected':  count_rejected,
            'recent_expenses': recent_expenses,
        }

    return render(request, 'dashboard.html', context)


# ─────────────────────────────────────────
# EMPLOYEE — EXPENSE CRUD
# ─────────────────────────────────────────

@login_required
def expense_list(request):
    """Employee: paginated, filtered list of own expenses."""
    qs     = Expense.objects.filter(submitted_by=request.user).select_related('category')
    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')

    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    page = paginate(request, qs, per_page=10)

    context = {
        'page_obj':      page,
        'expenses':      page.object_list,
        'status_filter': status,
        'query':         q,
        'status_choices': Expense.STATUS_CHOICES,
    }
    return render(request, 'expense_list.html', context)


@login_required
def expense_new(request):
    """Create a new expense — save as draft or submit."""
    # Seed default categories if none exist yet
    if not Category.objects.exists():
        defaults = [
            ('Travel', 'fa-plane'), ('Food and Dining', 'fa-utensils'),
            ('Accommodation', 'fa-hotel'), ('Office Supplies', 'fa-boxes-stacked'),
            ('Training', 'fa-graduation-cap'), ('Communication', 'fa-phone'),
            ('Medical', 'fa-kit-medical'), ('Miscellaneous', 'fa-receipt'),
        ]
        for name, icon in defaults:
            Category.objects.get_or_create(name=name, defaults={'icon': icon})

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            expense              = form.save(commit=False)
            expense.submitted_by = request.user
            
            # Base amount conversion
            profile = getattr(request.user, 'profile', None)
            base_code = profile.company.base_currency_code if profile and profile.company else expense.currency
            rate = get_exchange_rate(expense.currency, base_code)
            expense.base_amount = expense.amount * rate
            
            if 'submit_expense' in request.POST:
                expense.status       = Expense.STATUS_PENDING
                expense.submitted_at = timezone.now()
                msg = 'Expense submitted for approval!'
            else:
                expense.status = Expense.STATUS_DRAFT
                msg = 'Expense saved as draft.'
            expense.save()
            messages.success(request, msg)
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(user=request.user)

    return render(request, 'expense_form.html', {'form': form, 'action': 'new'})


@login_required
def expense_edit(request, pk):
    """Edit a draft expense."""
    expense = get_object_or_404(Expense, pk=pk, submitted_by=request.user)

    if not expense.is_editable:
        messages.error(request, 'This expense cannot be edited.')
        return redirect('expense_detail', pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            if 'submit_expense' in request.POST:
                expense.status = Expense.STATUS_PENDING
                expense.submitted_at = timezone.now()
                msg = 'Expense submitted for approval!'
            else:
                expense.status = Expense.STATUS_DRAFT
                msg = 'Draft updated.'
            expense.save()
            messages.success(request, msg)
            return redirect('expense_detail', pk=pk)
    else:
        form = ExpenseForm(instance=expense, user=request.user)

    return render(request, 'expense_form.html', {'form': form, 'action': 'edit', 'expense': expense})


@login_required
def process_receipt_ocr(request):
    """AJAX endpoint to process an uploaded receipt image and return OCR data."""
    if request.method == 'POST' and request.FILES.get('receipt'):
        receipt_file = request.FILES['receipt']
        try:
            from .ocr_utils import extract_receipt_data
            data = extract_receipt_data(receipt_file)
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'No file uploaded or invalid request method.'})


@login_required
def expense_detail(request, pk):
    """View a single expense — owner or manager only."""
    expense = get_object_or_404(Expense, pk=pk)
    profile = getattr(request.user, 'profile', None)
    if expense.submitted_by != request.user and not (profile and profile.is_manager):
        return HttpResponseForbidden()

    return render(request, 'expense_detail.html', {'expense': expense})


@login_required
@require_POST
def expense_delete(request, pk):
    """Delete a draft expense."""
    expense = get_object_or_404(Expense, pk=pk, submitted_by=request.user)
    if expense.status != Expense.STATUS_DRAFT:
        messages.error(request, 'Only draft expenses can be deleted.')
        return redirect('expense_detail', pk=pk)
    expense.delete()
    messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


# ─────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────

@login_required
def profile_view(request):
    """View and update own profile."""
    user    = request.user
    profile = getattr(user, 'profile', None)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)

        # Update User fields too
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name  = request.POST.get('last_name',  user.last_name)
        user.email      = request.POST.get('email',      user.email)
        user.save()

        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })

    # Expense summary for profile page
    my_expenses    = Expense.objects.filter(submitted_by=user)
    total_expenses = my_expenses.count()
    total_amount   = my_expenses.exclude(status=Expense.STATUS_DRAFT).aggregate(s=Sum('amount'))['s'] or 0

    return render(request, 'profile.html', {
        'form':          form,
        'profile':       profile,
        'total_expenses': total_expenses,
        'total_amount':   total_amount,
    })


# ─────────────────────────────────────────
# MANAGER — APPROVAL VIEWS
# ─────────────────────────────────────────

@manager_required
def manager_pending(request):
    """Manager: paginated list of pending expenses."""
    qs = Expense.objects.filter(
        status=Expense.STATUS_PENDING
    ).select_related('submitted_by', 'category')

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(submitted_by__username__icontains=q)
        )

    page = paginate(request, qs, per_page=10)
    return render(request, 'manager_pending.html', {
        'page_obj': page,
        'expenses': page.object_list,
        'query':    q,
    })


@manager_required
def manager_review(request, pk):
    """Manager: approve or reject a single expense."""
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            action = request.POST.get('action')
            note   = form.cleaned_data.get('manager_note', '')
            reason = form.cleaned_data.get('rejection_reason', '')

            if action == 'approve':
                expense.approve(request.user, note=note)
                messages.success(request, f'Expense #{pk} approved.')
            elif action == 'reject':
                if not reason:
                    messages.error(request, 'Please provide a rejection reason.')
                    return redirect('manager_review', pk=pk)
                expense.reject(request.user, reason=reason)
                messages.warning(request, f'Expense #{pk} rejected.')
            return redirect('manager_pending')
    else:
        form = ReviewForm()

    return render(request, 'manager_review.html', {
        'expense': expense, 'form': form,
    })


@manager_required
def manager_all_expenses(request):
    """Manager: browseable, paginated list of all expenses."""
    qs = Expense.objects.all().select_related(
        'submitted_by', 'category', 'reviewed_by'
    )

    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')

    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(submitted_by__username__icontains=q)
        )

    page = paginate(request, qs, per_page=15)
    return render(request, 'manager_all_expenses.html', {
        'page_obj':      page,
        'expenses':      page.object_list,
        'status_filter': status,
        'query':         q,
        'status_choices': Expense.STATUS_CHOICES,
    })


# ─────────────────────────────────────────
# CSV EXPORT (Manager only)
# ─────────────────────────────────────────

@manager_required
def export_expenses_csv(request):
    """Download all expenses as a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="expenses_{timezone.now().strftime("%Y%m%d")}.csv"'
    )

    qs = Expense.objects.all().select_related(
        'submitted_by', 'category', 'reviewed_by'
    )

    # Apply same filters as the all-expenses view
    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(submitted_by__username__icontains=q)
        )

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Title', 'Employee', 'Category',
        'Amount', 'Currency', 'Date', 'Status',
        'Submitted On', 'Reviewed By', 'Reviewed On',
        'Manager Note', 'Rejection Reason',
    ])

    for exp in qs:
        writer.writerow([
            exp.pk,
            exp.title,
            exp.submitted_by.get_full_name() or exp.submitted_by.username,
            exp.category.name if exp.category else '',
            exp.amount,
            exp.currency,
            exp.date,
            exp.get_status_display(),
            exp.submitted_at.strftime('%Y-%m-%d %H:%M') if exp.submitted_at else '',
            exp.reviewed_by.get_full_name() if exp.reviewed_by else '',
            exp.reviewed_at.strftime('%Y-%m-%d %H:%M') if exp.reviewed_at else '',
            exp.manager_note,
            exp.rejection_reason,
        ])

    return response


# ─────────────────────────────────────────
# USER MANAGEMENT (ADMIN ONLY)
# ─────────────────────────────────────────

def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not (profile and profile.is_admin):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def user_management_list(request):
    """List all users in the admin's company."""
    company = request.user.profile.company
    if not company:
        messages.error(request, 'Complete company setup first.')
        return redirect('onboarding')
        
    users = UserProfile.objects.filter(company=company).select_related('user', 'manager__user').order_by('user__first_name', 'user__username')
    return render(request, 'user_management_list.html', {'users': users})

@admin_required
def user_management_add(request):
    """Add a new employee or manager."""
    company = request.user.profile.company
    if request.method == 'POST':
        user_form = AdminUserCreateForm(request.POST)
        profile_form = AdminUserProfileForm(request.POST, company=company)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(f"{user.username}123") # Default password
            user.save()
            
            # Profile is automatically created by signal, so we fetch and update it
            profile = user.profile
            profile.role = profile_form.cleaned_data.get('role', 'employee')
            profile.manager = profile_form.cleaned_data.get('manager')
            profile.department = profile_form.cleaned_data.get('department', '')
            profile.phone = profile_form.cleaned_data.get('phone', '')
            profile.company = company
            profile.save()
            
            messages.success(request, f'User {user.username} created. Default password: {user.username}123')
            return redirect('user_management_list')
        else:
            # Collect all errors for debugging
            all_errors = []
            for field, errs in user_form.errors.items():
                for e in errs:
                    all_errors.append(f'{field}: {e}')
            for field, errs in profile_form.errors.items():
                for e in errs:
                    all_errors.append(f'{field}: {e}')
            if all_errors:
                messages.error(request, 'Could not save user — ' + ' | '.join(all_errors))
    else:
        user_form = AdminUserCreateForm()
        profile_form = AdminUserProfileForm(company=company)

    return render(request, 'user_management_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'action': 'Add'
    })

@admin_required
def user_management_edit(request, pk):
    """Edit an existing employee or manager."""
    company = request.user.profile.company
    profile = get_object_or_404(UserProfile, pk=pk, company=company)
    user = profile.user
    
    if request.method == 'POST':
        user_form = AdminUserCreateForm(request.POST, instance=user)
        profile_form = AdminUserProfileForm(request.POST, instance=profile, company=company)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            # Explicitly assign fields to avoid signal overwrite race condition
            profile.role = profile_form.cleaned_data.get('role', profile.role)
            profile.manager = profile_form.cleaned_data.get('manager')
            profile.department = profile_form.cleaned_data.get('department', '')
            profile.phone = profile_form.cleaned_data.get('phone', '')
            profile.save()
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('user_management_list')
    else:
        user_form = AdminUserCreateForm(instance=user)
        profile_form = AdminUserProfileForm(instance=profile, company=company)

    return render(request, 'user_management_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'action': 'Edit',
        'target_user': user
    })


@admin_required
@require_POST
def user_management_delete(request, pk):
    """Remove a team member from the company. Admin cannot delete themselves."""
    company = request.user.profile.company
    profile = get_object_or_404(UserProfile, pk=pk, company=company)
    target_user = profile.user

    if target_user == request.user:
        messages.error(request, 'You cannot remove yourself.')
        return redirect('user_management_list')

    username = target_user.username
    target_user.delete()   # cascades to UserProfile
    messages.success(request, f'User "{username}" has been removed from the team.')
    return redirect('user_management_list')


# ─────────────────────────────────────────
# CUSTOM ERROR HANDLERS
# ─────────────────────────────────────────

def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)


# ─────────────────────────────────────────
# NOTIFICATIONS API
# ─────────────────────────────────────────

@login_required
def notifications_list(request):
    """Return the 15 most recent notifications for the logged-in user as JSON."""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:15]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id':         n.pk,
                'kind':       n.kind,
                'message':    n.message,
                'link':       n.link,
                'is_read':    n.is_read,
                'created_at': n.created_at.strftime('%d %b, %H:%M'),
            }
            for n in notifs
        ],
    }
    return JsonResponse(data)


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark a single notification as read."""
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notifications_mark_all_read(request):
    """Mark all notifications for the current user as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})
