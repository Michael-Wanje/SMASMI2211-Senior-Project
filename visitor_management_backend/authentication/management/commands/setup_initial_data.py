# authentication/management/commands/setup_initial_data.py
from django.core.management.base import BaseCommand
from notifications.utils import create_default_templates
from authentication.models import User

class Command(BaseCommand):
    help = 'Setup initial data for the application'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create default notification templates
        create_default_templates()
        self.stdout.write('✓ Created default notification templates')
        
        # Create default admin user if it doesn't exist
        if not User.objects.filter(email='admin@example.com').exists():
            User.objects.create_user(
                email='admin@example.com',
                username='admin',
                password='admin123',
                first_name='System',
                last_name='Administrator',
                user_type='admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write('✓ Created default admin user')
        
        # Create default security user
        if not User.objects.filter(email='security@example.com').exists():
            User.objects.create_user(
                email='security@example.com',
                username='security',
                password='security123',
                first_name='Security',
                last_name='Personnel',
                user_type='security'
            )
            self.stdout.write('✓ Created default security user')
        
        self.stdout.write(
            self.style.SUCCESS('Initial data setup completed successfully!')
        )