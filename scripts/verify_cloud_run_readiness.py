#!/usr/bin/env python3
"""
Verify Cloud Run deployment readiness for Bachata Buddy.
Checks all required files, configurations, and dependencies.
"""

import os
from pathlib import Path

def main():
    print('🔍 Cloud Run Deployment Readiness Check')
    print('=' * 50)

    # Check files exist
    files_to_check = [
        'Dockerfile',
        '.dockerignore',
        '.gcloudignore',
        'cloudbuild.yaml',
        'DEPLOYMENT.md',
        'CLOUD_RUN_READINESS.md',
        'scripts/test_docker_build.sh',
        '.env.example'
    ]

    print('\n📁 Required Files:')
    all_files_exist = True
    for file in files_to_check:
        exists = Path(file).exists()
        status = '✅' if exists else '❌'
        print(f'  {status} {file}')
        if not exists:
            all_files_exist = False

    # Check pyproject.toml for gunicorn
    print('\n📦 Dependencies:')
    with open('pyproject.toml', 'r') as f:
        content = f.read()
        has_gunicorn = 'gunicorn' in content
        has_whitenoise = 'whitenoise' in content
        print(f'  {"✅" if has_gunicorn else "❌"} gunicorn')
        print(f'  {"✅" if has_whitenoise else "❌"} whitenoise')

    # Check settings.py
    print('\n⚙️  Django Settings:')
    with open('bachata_buddy/settings.py', 'r') as f:
        content = f.read()
        has_secret_key_env = 'DJANGO_SECRET_KEY' in content
        has_debug_env = 'DJANGO_DEBUG' in content
        has_allowed_hosts_env = 'ALLOWED_HOSTS' in content and 'os.environ.get' in content
        has_whitenoise_middleware = 'whitenoise.middleware.WhiteNoiseMiddleware' in content
        
        print(f'  {"✅" if has_secret_key_env else "❌"} SECRET_KEY uses environment variable')
        print(f'  {"✅" if has_debug_env else "❌"} DEBUG uses environment variable')
        print(f'  {"✅" if has_allowed_hosts_env else "❌"} ALLOWED_HOSTS uses environment variable')
        print(f'  {"✅" if has_whitenoise_middleware else "❌"} WhiteNoise middleware configured')

    # Check Dockerfile
    print('\n🐳 Dockerfile:')
    with open('Dockerfile', 'r') as f:
        content = f.read()
        has_port_var = '$PORT' in content
        has_gunicorn = 'gunicorn' in content
        has_healthcheck = 'HEALTHCHECK' in content
        
        print(f'  {"✅" if has_port_var else "❌"} Uses $PORT environment variable')
        print(f'  {"✅" if has_gunicorn else "❌"} Uses gunicorn')
        print(f'  {"✅" if has_healthcheck else "❌"} Has health check')

    print('\n' + '=' * 50)
    
    if all_files_exist and has_gunicorn and has_whitenoise and has_secret_key_env and has_debug_env and has_allowed_hosts_env:
        print('✅ All checks passed! Ready for Cloud Run deployment.')
        print('\nNext steps:')
        print('  1. Test locally: ./scripts/test_docker_build.sh')
        print('  2. Deploy: gcloud run deploy bachata-buddy --source . --region us-central1')
        print('  3. See DEPLOYMENT.md for detailed instructions')
        return 0
    else:
        print('❌ Some checks failed. Please review the issues above.')
        return 1

if __name__ == '__main__':
    exit(main())

