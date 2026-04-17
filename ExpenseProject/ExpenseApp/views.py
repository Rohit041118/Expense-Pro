from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST

from .models import Expense, Category, UserProfile
from .forms import ExpenseForm, ReviewForm, UserProfileForm


# ─────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────

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
            return redirect(request.POST.get('next') or 'dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html', {'form': {}})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@login_required
def dashboard(request):
    user    = request.user
    profile = getattr(user, 'profile', None)
    is_mgr  = profile and profile.is_manager

    if is_mgr:
        # Manager sees team's pending requests & overall stats
        pending_expenses = Expense.objects.filter(status=Expense.STATUS_PENDING).select_related('submitted_by', 'category')[:10]
        total_approved   = Expense.objects.filter(status=Expense.STATUS_APPROVED).aggregate(s=Sum('amount'))['s'] or 0
        total_pending    = Expense.objects.filter(status=Expense.STATUS_PENDING).count()
        total_rejected   = Expense.objects.filter(status=Expense.STATUS_REJECTED).count()
        total_paid       = Expense.objects.filter(status=Expense.STATUS_PAID).aggregate(s=Sum('amount'))['s'] or 0
        recent_expenses  = Expense.objects.all().select_related('submitted_by', 'category')[:8]
        context = {
            'is_manager': True,
            'pending_expenses': pending_expenses,
            'total_approved': total_approved,
            'total_pending': total_pending,
            'total_rejected': total_rejected,
            'total_paid': total_paid,
            'recent_expenses': recent_expenses,
        }
    else:
        # Employee sees their own stats
        my_expenses     = Expense.objects.filter(submitted_by=user)
        total_submitted = my_expenses.exclude(status=Expense.STATUS_DRAFT).aggregate(s=Sum('amount'))['s'] or 0
        total_approved  = my_expenses.filter(status=Expense.STATUS_APPROVED).aggregate(s=Sum('amount'))['s'] or 0
        count_pending   = my_expenses.filter(status=Expense.STATUS_PENDING).count()
        count_rejected  = my_expenses.filter(status=Expense.STATUS_REJECTED).count()
        recent_expenses = my_expenses.select_related('category')[:8]
        context = {
            'is_manager': False,
            'total_submitted': total_submitted,
            'total_approved': total_approved,
            'count_pending': count_pending,
            'count_rejected': count_rejected,
            'recent_expenses': recent_expenses,
        }

    return render(request, 'dashboard.html', context)


# ─────────────────────────────────────────
# EMPLOYEE — EXPENSE CRUD
# ─────────────────────────────────────────

@login_required
def expense_list(request):
    """Employee: view own expenses with filters."""
    qs = Expense.objects.filter(submitted_by=request.user).select_related('category')

    # Filters
    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    context = {
        'expenses': qs,
        'status_filter': status,
        'query': q,
        'status_choices': Expense.STATUS_CHOICES,
    }
    return render(request, 'expense_list.html', context)


@login_required
def expense_new(request):
    """Create a new expense (draft)."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.submitted_by = request.user
            # Check if submit was clicked
            if 'submit_expense' in request.POST:
                expense.status = Expense.STATUS_PENDING
                expense.submitted_at = timezone.now()
                msg = 'Expense submitted successfully!'
            else:
                expense.status = Expense.STATUS_DRAFT
                msg = 'Expense saved as draft.'
            expense.save()
            messages.success(request, msg)
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm()

    return render(request, 'expense_form.html', {'form': form, 'action': 'new'})


@login_required
def expense_edit(request, pk):
    """Edit a draft expense."""
    expense = get_object_or_404(Expense, pk=pk, submitted_by=request.user)

    if not expense.is_editable:
        messages.error(request, 'This expense cannot be edited.')
        return redirect('expense_detail', pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            exp = form.save(commit=False)
            if 'submit_expense' in request.POST:
                exp.status = Expense.STATUS_PENDING
                exp.submitted_at = timezone.now()
                messages.success(request, 'Expense submitted for approval.')
            else:
                messages.success(request, 'Draft saved.')
            exp.save()
            return redirect('expense_detail', pk=pk)
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expense_form.html', {'form': form, 'expense': expense, 'action': 'edit'})


@login_required
def expense_detail(request, pk):
    """View a single expense."""
    expense = get_object_or_404(Expense, pk=pk)
    # Only owner or manager can view
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
# MANAGER — APPROVAL VIEWS
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


@manager_required
def manager_pending(request):
    """Manager: list all pending expenses for review."""
    qs = Expense.objects.filter(status=Expense.STATUS_PENDING).select_related('submitted_by', 'category')

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(submitted_by__username__icontains=q))

    return render(request, 'manager_pending.html', {'expenses': qs, 'query': q})


@manager_required
def manager_review(request, pk):
    """Manager: review a single expense."""
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            action = request.POST.get('action')
            note   = form.cleaned_data.get('manager_note', '')
            reason = form.cleaned_data.get('rejection_reason', '')

            if action == 'approve':
                expense.approve(request.user, note=note)
                messages.success(request, f'Expense #{pk} approved ✓')
            elif action == 'reject':
                if not reason:
                    messages.error(request, 'Please provide a rejection reason.')
                    return redirect('manager_review', pk=pk)
                expense.reject(request.user, reason=reason)
                messages.warning(request, f'Expense #{pk} rejected.')
            return redirect('manager_pending')
    else:
        form = ReviewForm()

    return render(request, 'manager_review.html', {'expense': expense, 'form': form})


@manager_required
def manager_all_expenses(request):
    """Manager: browse all expenses (any status)."""
    qs = Expense.objects.all().select_related('submitted_by', 'category', 'reviewed_by')

    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(submitted_by__username__icontains=q))

    context = {
        'expenses': qs,
        'status_filter': status,
        'query': q,
        'status_choices': Expense.STATUS_CHOICES,
    }
    return render(request, 'manager_all_expenses.html', context)
