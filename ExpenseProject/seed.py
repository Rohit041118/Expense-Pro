"""
Seed script -- creates demo users, categories, and sample expenses.
Run with:  python seed.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ExpenseProject.settings')
django.setup()

from django.contrib.auth.models import User
from ExpenseApp.models import UserProfile, Category, Expense
from django.utils import timezone

# -- Categories -----------------------------------------------
cat_data = [
    ('Travel',          'fa-plane'),
    ('Food and Dining', 'fa-utensils'),
    ('Accommodation',   'fa-hotel'),
    ('Office Supplies', 'fa-boxes-stacked'),
    ('Training',        'fa-graduation-cap'),
    ('Communication',   'fa-phone'),
    ('Medical',         'fa-kit-medical'),
    ('Miscellaneous',   'fa-receipt'),
]
categories = {}
for name, icon in cat_data:
    c, _ = Category.objects.get_or_create(name=name, defaults={'icon': icon})
    categories[name] = c

print(f"[OK] {len(categories)} categories ready")

# -- Users ----------------------------------------------------
def make_user(username, password, fname, lname, role, dept='Engineering'):
    u, created = User.objects.get_or_create(username=username)
    if created:
        u.set_password(password)
        u.first_name = fname
        u.last_name  = lname
        u.email      = f"{username}@expensepro.com"
        u.save()
    UserProfile.objects.get_or_create(user=u, defaults={'role': role, 'department': dept})
    return u

admin_user   = make_user('admin',   'admin123',   'Admin',  'User',   'admin')
manager_user = make_user('manager', 'manager123', 'Priya',  'Sharma', 'manager')
emp1         = make_user('rohit',   'rohit123',   'Rohit',  'Kumar',  'employee')
emp2         = make_user('divya',   'divya123',   'Divya',  'Patel',  'employee')

print("[OK] Users: admin / manager / rohit / divya")

# -- Sample Expenses ------------------------------------------
sample_expenses = [
    dict(title='Flight to Mumbai Q1 Review', amount=12500, status='approved',
         category=categories['Travel'], submitted_by=emp1, currency='INR',
         description='Round trip flight for quarterly review meeting.',
         submitted_at=timezone.now(), reviewed_by=manager_user,
         manager_note='Approved. Please submit boarding pass.'),
    dict(title='Team Lunch Onboarding', amount=2800, status='pending',
         category=categories['Food and Dining'], submitted_by=emp1, currency='INR',
         description='Team lunch for new joiner onboarding.',
         submitted_at=timezone.now()),
    dict(title='MacBook Pro Sleeve', amount=1299, status='draft',
         category=categories['Office Supplies'], submitted_by=emp1, currency='INR'),
    dict(title='AWS Training Course', amount=8999, status='rejected',
         category=categories['Training'], submitted_by=emp2, currency='INR',
         description='Online AWS Solutions Architect Course.',
         submitted_at=timezone.now(), reviewed_by=manager_user,
         rejection_reason='Budget exhausted for this quarter.'),
    dict(title='Hotel Stay Pune Visit', amount=4500, status='pending',
         category=categories['Accommodation'], submitted_by=emp2, currency='INR',
         submitted_at=timezone.now()),
    dict(title='Internet Bill Reimbursement', amount=999, status='approved',
         category=categories['Communication'], submitted_by=emp2, currency='INR',
         submitted_at=timezone.now(), reviewed_by=manager_user),
]

created = 0
for data in sample_expenses:
    if not Expense.objects.filter(title=data['title']).exists():
        Expense.objects.create(**data)
        created += 1

print(f"[OK] {created} new expenses created ({len(sample_expenses)} total in dataset)")
print("")
print("Seed complete! Login credentials:")
print("   admin   / admin123   (Admin role)")
print("   manager / manager123 (Manager role)")
print("   rohit   / rohit123   (Employee role)")
print("   divya   / divya123   (Employee role)")
