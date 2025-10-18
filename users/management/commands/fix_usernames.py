"""
Management command to fix usernames for email-based login.
Sets username = email for all users where they don't match.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import models


class Command(BaseCommand):
    help = 'Fix usernames to match emails for email-based login'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        
        # Find users where username != email
        users_to_fix = User.objects.exclude(username=models.F('email'))
        count = users_to_fix.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No users need fixing. All usernames match emails.'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {count} user(s) to fix:'))
        self.stdout.write('')
        
        for user in users_to_fix:
            self.stdout.write(f'  User ID: {user.id}')
            self.stdout.write(f'    Current username: {user.username}')
            self.stdout.write(f'    Email: {user.email}')
            self.stdout.write(f'    Will change to: {user.email}')
            self.stdout.write('')
            
            if not dry_run:
                user.username = user.email
                user.save()
                self.stdout.write(self.style.SUCCESS(f'    ✅ Fixed user {user.id}'))
                self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(''))
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes were made'))
            self.stdout.write(self.style.WARNING(f'Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS(''))
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully fixed {count} user(s)'))
            self.stdout.write(self.style.SUCCESS('Users can now log in with their email addresses'))
