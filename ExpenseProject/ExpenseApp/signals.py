"""
Django signals:
  1. Auto-create UserProfile whenever a new User is created.
  2. Auto-create Notifications when an Expense changes status.
This file is loaded via ExpenseApp/apps.py ready() method.
"""
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.urls import reverse

from .models import UserProfile, Expense, Notification


# ─────────────────────────────────────────
# USER PROFILE — auto-create on User save
# ─────────────────────────────────────────

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile automatically when a new User is registered."""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'employee'}
        )


# NOTE: We intentionally do NOT auto-save the profile when the User is saved.
# Doing so causes a race condition: any role/field just set on the profile
# gets overwritten by a stale in-memory copy triggered by the signal.
# Profiles are saved explicitly in views wherever needed.


# ─────────────────────────────────────────
# NOTIFICATIONS — fire on Expense status changes
# ─────────────────────────────────────────

# Track old status to detect transitions
_EXPENSE_OLD_STATUS = {}


@receiver(post_save, sender=Expense)
def expense_notification(sender, instance, created, **kwargs):
    """
    Create Notification rows when an Expense changes status:
      - draft → pending  : notify all managers in the same company
      - pending → approved: notify the submitter
      - pending → rejected: notify the submitter
    """
    old_status = _EXPENSE_OLD_STATUS.pop(instance.pk, None)
    new_status = instance.status
    expense_link = reverse('expense_detail', args=[instance.pk])

    # ── Submitted (draft/new → pending) ──────────────────────────────────────
    if new_status == Expense.STATUS_PENDING and old_status != Expense.STATUS_PENDING:
        # Notify every manager/admin in the same company
        submitter = instance.submitted_by
        submitter_name = submitter.get_full_name() or submitter.username

        company = getattr(getattr(submitter, 'profile', None), 'company', None)
        if company:
            managers = UserProfile.objects.filter(
                company=company,
                role__in=('manager', 'admin')
            ).select_related('user')

            for mgr_profile in managers:
                if mgr_profile.user != submitter:
                    Notification.objects.create(
                        user=mgr_profile.user,
                        kind=Notification.NOTIF_SUBMITTED,
                        message=f'{submitter_name} submitted "{instance.title}" for ₹{instance.amount}',
                        link=expense_link,
                    )

    # ── Approved (pending → approved) ────────────────────────────────────────
    elif new_status == Expense.STATUS_APPROVED and old_status == Expense.STATUS_PENDING:
        reviewer_name = (
            instance.reviewed_by.get_full_name() or instance.reviewed_by.username
        ) if instance.reviewed_by else 'Your manager'
        Notification.objects.create(
            user=instance.submitted_by,
            kind=Notification.NOTIF_APPROVED,
            message=f'"{instance.title}" was approved by {reviewer_name}',
            link=expense_link,
        )

    # ── Rejected (pending → rejected) ────────────────────────────────────────
    elif new_status == Expense.STATUS_REJECTED and old_status == Expense.STATUS_PENDING:
        reviewer_name = (
            instance.reviewed_by.get_full_name() or instance.reviewed_by.username
        ) if instance.reviewed_by else 'Your manager'
        Notification.objects.create(
            user=instance.submitted_by,
            kind=Notification.NOTIF_REJECTED,
            message=f'"{instance.title}" was rejected by {reviewer_name}',
            link=expense_link,
        )


# Pre-save hook to capture the OLD status before it is overwritten
from django.db.models.signals import pre_save

@receiver(pre_save, sender=Expense)
def capture_old_expense_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Expense.objects.get(pk=instance.pk)
            _EXPENSE_OLD_STATUS[instance.pk] = old.status
        except Expense.DoesNotExist:
            pass
