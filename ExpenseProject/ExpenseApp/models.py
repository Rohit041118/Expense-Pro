from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Extended user profile with role info."""

    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('manager',  'Manager'),
        ('admin',    'Admin'),
    ]

    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    manager    = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='subordinates',
        limit_choices_to={'role': 'manager'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"

    @property
    def is_manager(self):
        return self.role in ('manager', 'admin')

    @property
    def is_admin(self):
        return self.role == 'admin'


class Category(models.Model):
    """Expense categories."""
    name       = models.CharField(max_length=80, unique=True)
    icon       = models.CharField(max_length=60, default='fa-receipt')   # FontAwesome class
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Core expense/reimbursement request."""

    STATUS_DRAFT    = 'draft'
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_PAID     = 'paid'

    STATUS_CHOICES = [
        (STATUS_DRAFT,    'Draft'),
        (STATUS_PENDING,  'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_PAID,     'Paid'),
    ]

    CURRENCY_CHOICES = [
        ('INR', '₹ INR'),
        ('USD', '$ USD'),
        ('EUR', '€ EUR'),
        ('GBP', '£ GBP'),
    ]

    # Core fields
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    currency    = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='INR')
    date        = models.DateField(default=timezone.now)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    # People
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    reviewed_by  = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_expenses',
    )

    # Status
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    rejection_reason = models.TextField(blank=True)
    manager_note     = models.TextField(blank=True)

    # Receipt
    receipt = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True)

    # Timestamps
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.pk} {self.title} — {self.submitted_by.username} ({self.status})"

    @property
    def is_editable(self):
        """Only draft expenses can be edited by the employee."""
        return self.status == self.STATUS_DRAFT

    @property
    def is_pending_review(self):
        return self.status == self.STATUS_PENDING

    def submit(self):
        self.status = self.STATUS_PENDING
        self.submitted_at = timezone.now()
        self.save()

    def approve(self, reviewer, note=''):
        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewer
        self.manager_note = note
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, reviewer, reason=''):
        self.status = self.STATUS_REJECTED
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.reviewed_at = timezone.now()
        self.save()

    def mark_paid(self):
        if self.status == self.STATUS_APPROVED:
            self.status = self.STATUS_PAID
            self.save()
