from django.apps import AppConfig


class VisitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.visitors'
    verbose_name = 'Visitor Management'
    
    def ready(self):
        import apps.visitors.signals