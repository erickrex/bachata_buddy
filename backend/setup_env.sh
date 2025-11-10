#!/bin/bash
# =============================================================================
# Environment Setup Script for Bachata Buddy Backend API
# =============================================================================
# This script helps you set up your local development environment.
# Run with: bash setup_env.sh
# =============================================================================

set -e  # Exit on error

echo "=============================================================================="
echo "Bachata Buddy Backend - Environment Setup"
echo "=============================================================================="
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file."
        echo "To manually update, edit .env or see .env.example for reference."
        exit 0
    fi
fi

# Copy .env.example to .env
echo "📝 Creating .env file from .env.example..."
cp .env.example .env
echo "✓ .env file created"
echo ""

# Prompt for Google API key
echo "=============================================================================="
echo "Google API Key Setup"
echo "=============================================================================="
echo ""
echo "The Bachata Buddy API requires a Google Gemini API key for AI features."
echo "Get your API key at: https://makersuite.google.com/app/apikey"
echo ""
read -p "Enter your Google API key (or press Enter to skip): " api_key

if [ -n "$api_key" ]; then
    # Update .env file with the API key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/GOOGLE_API_KEY=your-gemini-api-key-here/GOOGLE_API_KEY=$api_key/" .env
    else
        # Linux
        sed -i "s/GOOGLE_API_KEY=your-gemini-api-key-here/GOOGLE_API_KEY=$api_key/" .env
    fi
    echo "✓ Google API key configured"
else
    echo "⚠️  Skipped Google API key setup"
    echo "   You can add it later by editing .env"
fi
echo ""

# Generate a secure Django secret key
echo "=============================================================================="
echo "Django Secret Key"
echo "=============================================================================="
echo ""
echo "Generating a secure Django secret key..."

# Check if Python is available
if command -v python3 &> /dev/null; then
    secret_key=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' 2>/dev/null || echo "")
    
    if [ -n "$secret_key" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/DJANGO_SECRET_KEY=local-dev-secret-key-change-in-production-use-secrets-manager/DJANGO_SECRET_KEY=$secret_key/" .env
        else
            sed -i "s/DJANGO_SECRET_KEY=local-dev-secret-key-change-in-production-use-secrets-manager/DJANGO_SECRET_KEY=$secret_key/" .env
        fi
        echo "✓ Django secret key generated"
    else
        echo "⚠️  Could not generate secret key (Django not installed)"
        echo "   Using default key for local development"
    fi
else
    echo "⚠️  Python not found, using default secret key"
fi
echo ""

# Test the configuration
echo "=============================================================================="
echo "Testing Configuration"
echo "=============================================================================="
echo ""

if command -v uv &> /dev/null; then
    echo "Running environment validation..."
    if uv run python test_env.py; then
        echo ""
        echo "=============================================================================="
        echo "✓ Environment Setup Complete!"
        echo "=============================================================================="
        echo ""
        echo "Next steps:"
        echo ""
        echo "1. Start the services:"
        echo "   docker-compose --profile microservices up"
        echo ""
        echo "2. Run migrations:"
        echo "   docker-compose exec api python manage.py migrate"
        echo ""
        echo "3. Create a superuser:"
        echo "   docker-compose exec api python manage.py createsuperuser"
        echo ""
        echo "4. Access the API:"
        echo "   http://localhost:8001"
        echo ""
        echo "5. View API documentation:"
        echo "   http://localhost:8001/api/docs"
        echo ""
        echo "For more information, see README.md and ENVIRONMENT_SETUP.md"
        echo "=============================================================================="
    else
        echo ""
        echo "⚠️  Environment validation failed"
        echo "   Please check the error messages above and update your .env file"
        echo "   See .env.example for reference"
    fi
else
    echo "⚠️  UV not found, skipping validation"
    echo "   Install UV: https://docs.astral.sh/uv/getting-started/installation/"
    echo ""
    echo "✓ .env file created successfully"
    echo "   Please verify the configuration manually"
fi
