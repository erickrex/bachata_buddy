#!/bin/bash
#
# Production Deployment Script
#
# This script deploys the Bachata Buddy system to Google Cloud Platform.
# It handles database migrations, data uploads, and service deployment.
#
# Usage: ./deploy_to_production.sh [step]
#   step: Optional step number (1-5) to run specific step only
#         If omitted, runs all steps interactively
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (update these!)
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-bachata-db}"
DB_NAME="${DB_NAME:-bachata_vibes}"
DB_USER="${DB_USER:-postgres}"
GCS_BUCKET="${GCS_BUCKET_NAME:-bachata-buddy-bucket}"

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

confirm() {
    read -p "$(echo -e ${YELLOW}$1 [y/N]: ${NC})" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Step 1: Database Setup
step1_database() {
    print_header "STEP 1: Database Setup"
    
    print_info "This step will:"
    print_info "  1. Start Cloud SQL Proxy"
    print_info "  2. Run database migrations"
    print_info "  3. Load move embeddings"
    echo
    
    if ! confirm "Proceed with database setup?"; then
        print_warning "Skipping database setup"
        return
    fi
    
    # Start Cloud SQL Proxy
    print_info "Starting Cloud SQL Proxy..."
    cloud_sql_proxy -instances=${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE}=tcp:5432 &
    PROXY_PID=$!
    sleep 3
    
    if ! ps -p $PROXY_PID > /dev/null; then
        print_error "Failed to start Cloud SQL Proxy"
        return 1
    fi
    print_success "Cloud SQL Proxy started (PID: $PROXY_PID)"
    
    # Set database URL
    export DATABASE_URL="postgresql://${DB_USER}@localhost:5432/${DB_NAME}"
    
    # Run migrations
    print_info "Running database migrations..."
    cd backend
    if uv run python manage.py migrate; then
        print_success "Migrations applied successfully"
    else
        print_error "Migration failed"
        kill $PROXY_PID
        return 1
    fi
    
    # Load embeddings
    print_info "Loading move embeddings..."
    if uv run python ../load_embeddings_to_db.py; then
        print_success "Embeddings loaded successfully"
    else
        print_error "Failed to load embeddings"
        kill $PROXY_PID
        return 1
    fi
    
    # Verify
    print_info "Verifying data..."
    EMBEDDING_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM move_embeddings;" | tr -d ' ')
    if [ "$EMBEDDING_COUNT" -eq 38 ]; then
        print_success "Verified: 38 embeddings loaded"
    else
        print_warning "Expected 38 embeddings, found $EMBEDDING_COUNT"
    fi
    
    # Stop proxy
    kill $PROXY_PID
    print_success "Cloud SQL Proxy stopped"
    
    cd ..
    print_success "Step 1 complete!"
}

# Step 2: Upload Media to GCS
step2_upload_media() {
    print_header "STEP 2: Upload Media to GCS"
    
    print_info "This step will:"
    print_info "  1. Upload training videos (38 files, ~500MB)"
    print_info "  2. Upload songs (16 files, ~80MB)"
    echo
    
    if ! confirm "Proceed with media upload?"; then
        print_warning "Skipping media upload"
        return
    fi
    
    # Upload training videos
    print_info "Uploading training videos..."
    if gsutil -m cp -r data/Bachata_steps/* gs://${GCS_BUCKET}/Bachata_steps/; then
        print_success "Training videos uploaded"
    else
        print_error "Failed to upload training videos"
        return 1
    fi
    
    # Upload songs
    print_info "Uploading songs..."
    if gsutil -m cp data/songs/*.mp3 gs://${GCS_BUCKET}/songs/; then
        print_success "Songs uploaded"
    else
        print_error "Failed to upload songs"
        return 1
    fi
    
    # Verify
    print_info "Verifying uploads..."
    VIDEO_COUNT=$(gsutil ls -r gs://${GCS_BUCKET}/Bachata_steps/ | grep -c ".mp4" || true)
    SONG_COUNT=$(gsutil ls gs://${GCS_BUCKET}/songs/ | grep -c ".mp3" || true)
    
    print_info "Uploaded: $VIDEO_COUNT videos, $SONG_COUNT songs"
    
    if [ "$VIDEO_COUNT" -ge 38 ] && [ "$SONG_COUNT" -ge 16 ]; then
        print_success "Media upload verified"
    else
        print_warning "Expected 38+ videos and 16+ songs"
    fi
    
    print_success "Step 2 complete!"
}

# Step 3: Deploy Backend API
step3_deploy_api() {
    print_header "STEP 3: Deploy Backend API"
    
    print_info "This step will:"
    print_info "  1. Build backend Docker image"
    print_info "  2. Deploy to Cloud Run"
    print_info "  3. Configure environment variables"
    echo
    
    if ! confirm "Proceed with API deployment?"; then
        print_warning "Skipping API deployment"
        return
    fi
    
    cd backend
    
    print_info "Deploying backend API..."
    if gcloud run deploy bachata-api \
        --source . \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_BUCKET_NAME=${GCS_BUCKET},DB_NAME=${DB_NAME}"; then
        print_success "Backend API deployed"
    else
        print_error "Failed to deploy backend API"
        cd ..
        return 1
    fi
    
    # Get service URL
    API_URL=$(gcloud run services describe bachata-api --region ${REGION} --format='value(status.url)')
    print_success "API URL: $API_URL"
    
    # Test health endpoint
    print_info "Testing health endpoint..."
    if curl -s "${API_URL}/api/health" | grep -q "healthy"; then
        print_success "Health check passed"
    else
        print_warning "Health check failed - check logs"
    fi
    
    cd ..
    print_success "Step 3 complete!"
}

# Step 4: Deploy Job Container
step4_deploy_job() {
    print_header "STEP 4: Deploy Job Container"
    
    print_info "This step will:"
    print_info "  1. Build job Docker image"
    print_info "  2. Deploy to Cloud Run Jobs"
    print_info "  3. Configure environment variables"
    echo
    
    if ! confirm "Proceed with job deployment?"; then
        print_warning "Skipping job deployment"
        return
    fi
    
    cd job
    
    print_info "Deploying job container..."
    if gcloud run jobs deploy video-processor \
        --source . \
        --region ${REGION} \
        --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_BUCKET_NAME=${GCS_BUCKET},DB_NAME=${DB_NAME}"; then
        print_success "Job container deployed"
    else
        print_error "Failed to deploy job container"
        cd ..
        return 1
    fi
    
    cd ..
    print_success "Step 4 complete!"
}

# Step 5: End-to-End Test
step5_test() {
    print_header "STEP 5: End-to-End Test"
    
    print_info "This step will:"
    print_info "  1. Create test user"
    print_info "  2. Generate choreography (Path 1)"
    print_info "  3. Verify video in GCS"
    echo
    
    if ! confirm "Proceed with end-to-end test?"; then
        print_warning "Skipping test"
        return
    fi
    
    # Get API URL
    API_URL=$(gcloud run services describe bachata-api --region ${REGION} --format='value(status.url)')
    
    print_info "API URL: $API_URL"
    print_info "Creating test choreography..."
    
    # Register test user
    print_info "Registering test user..."
    curl -s -X POST "${API_URL}/api/auth/register/" \
        -H "Content-Type: application/json" \
        -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}' \
        > /dev/null || true
    
    # Login
    print_info "Logging in..."
    TOKEN=$(curl -s -X POST "${API_URL}/api/auth/login/" \
        -H "Content-Type: application/json" \
        -d '{"username":"testuser","password":"testpass123"}' \
        | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")
    
    if [ -z "$TOKEN" ]; then
        print_error "Failed to get auth token"
        return 1
    fi
    print_success "Authenticated"
    
    # Create choreography
    print_info "Creating choreography..."
    RESPONSE=$(curl -s -X POST "${API_URL}/api/choreography/generate-from-song/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"song_id":1,"difficulty":"intermediate","energy_level":"medium","style":"romantic"}')
    
    TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))")
    
    if [ -z "$TASK_ID" ]; then
        print_error "Failed to create choreography"
        echo "Response: $RESPONSE"
        return 1
    fi
    print_success "Task created: $TASK_ID"
    
    # Poll status
    print_info "Waiting for video generation (this may take 2-3 minutes)..."
    for i in {1..60}; do
        sleep 5
        STATUS=$(curl -s "${API_URL}/api/choreography/tasks/${TASK_ID}/" \
            -H "Authorization: Bearer $TOKEN" \
            | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
        
        echo -n "."
        
        if [ "$STATUS" = "completed" ]; then
            echo
            print_success "Video generated successfully!"
            break
        elif [ "$STATUS" = "failed" ]; then
            echo
            print_error "Video generation failed"
            return 1
        fi
    done
    
    # Verify in GCS
    print_info "Verifying video in GCS..."
    if gsutil ls gs://${GCS_BUCKET}/choreographies/choreography_${TASK_ID}.mp4 > /dev/null 2>&1; then
        print_success "Video found in GCS"
        
        # Get file size
        SIZE=$(gsutil du -h gs://${GCS_BUCKET}/choreographies/choreography_${TASK_ID}.mp4 | awk '{print $1}')
        print_info "Video size: $SIZE"
    else
        print_error "Video not found in GCS"
        return 1
    fi
    
    print_success "Step 5 complete!"
    print_success "End-to-end test PASSED!"
}

# Main execution
main() {
    print_header "Bachata Buddy - Production Deployment"
    
    print_info "Configuration:"
    print_info "  Project ID: $PROJECT_ID"
    print_info "  Region: $REGION"
    print_info "  Cloud SQL: $CLOUD_SQL_INSTANCE"
    print_info "  GCS Bucket: $GCS_BUCKET"
    echo
    
    # Check if specific step requested
    if [ $# -eq 1 ]; then
        case $1 in
            1) step1_database ;;
            2) step2_upload_media ;;
            3) step3_deploy_api ;;
            4) step4_deploy_job ;;
            5) step5_test ;;
            *)
                print_error "Invalid step: $1"
                print_info "Usage: $0 [1-5]"
                exit 1
                ;;
        esac
    else
        # Run all steps interactively
        step1_database
        step2_upload_media
        step3_deploy_api
        step4_deploy_job
        step5_test
        
        print_header "DEPLOYMENT COMPLETE!"
        print_success "All steps completed successfully"
        print_info "Your Bachata Buddy system is now live in production!"
    fi
}

# Run main
main "$@"
