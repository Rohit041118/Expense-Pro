from django.apps import AppConfig


class ExpenseappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ExpenseApp'

    def ready(self):
        # Register signal handlers
        import ExpenseApp.signals  # noqa: F401
