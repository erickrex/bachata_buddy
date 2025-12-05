# Microservices Migration Specification

**Project:** Bachata Buddy - Microservices Architecture Migration  
**Date:** October 26, 2025  
**Status:** ✅ **READY FOR IMPLEMENTATION**

---

## 📚 Documentation Overview

This directory contains complete specifications for migrating Bachata Buddy from a monolithic Django application to a modern microservices architecture.

### Documents

1. **[requirements.md](requirements.md)** - Complete requirements specification
2. **[design.md](design.md)** - Detailed architecture and design
3. **[tasks.md](tasks.md)** - Phase-by-phase task breakdown

---

## 🎯 Migration Goals

### From (Current)
```
Monolithic Django App
├── Django Templates (HTMX + Alpine.js)
├── Django Views (Business Logic)
├── Background Threads (Video Processing)
└── Deployed on Compute Engine (Single VM)
```

### To (Target)
```
Microservices Architecture
├── React Frontend (SPA on Cloud Run)
├── Django REST API (Cloud Run)
├── Python Worker (Cloud Run Jobs)
└── Cloud Pub/Sub (Message Broker)
```

---

## 🏗️ Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  React Frontend  │────▶│  Django REST API │────▶│  Python Worker   │
│  (Cloud Run)     │     │  (Cloud Run)     │     │  (Cloud Run Jobs)│
│                  │     │                  │     │                  │
│  • SPA           │     │  • JWT Auth      │     │  • FFmpeg        │
│  • React Router  │     │  • CRUD APIs     │     │  • Video Gen     │
│  • Axios         │     │  • Pub/Sub Pub   │     │  • Pub/Sub Sub   │
│  • Tailwind CSS  │     │  • OpenAPI Docs  │     │  • Progress      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                        │                         │
         └────────────────────────┴─────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │   Shared Services         │
                    │  • Cloud SQL (PostgreSQL) │
                    │  • Elasticsearch          │
                    │  • Cloud Storage (GCS)    │
                    │  • Cloud Pub/Sub          │
                    │  • Secret Manager         │
                    └───────────────────────────┘
```

---

## ✨ Key Benefits

### Technical Benefits
- ✅ **Independent Scaling:** Scale frontend, backend, and worker separately
- ✅ **Reliable Async Processing:** Pub/Sub guarantees message delivery
- ✅ **Modern Stack:** React + DRF + Cloud Run
- ✅ **Better Separation:** Clear boundaries between services
- ✅ **Easier Testing:** Each service can be tested independently

### Business Benefits
- ✅ **Better UX:** Modern SPA with real-time updates
- ✅ **Mobile Ready:** API-first design enables mobile apps
- ✅ **Faster Development:** Teams can work on services independently
- ✅ **Lower Costs:** Pay only for what you use (serverless)
- ✅ **Higher Reliability:** 99.9% uptime with Cloud Run

---

## 📋 Implementation Plan

### Phase 1: Backend API (Week 1-2)
**Effort:** 34 hours

**Deliverables:**
- Django REST Framework API
- JWT authentication
- CRUD endpoints for tasks and collections
- Pub/Sub publisher
- OpenAPI documentation
- Deployed to Cloud Run

**Key Tasks:**
- Set up Django REST Framework project
- Implement JWT authentication
- Create API endpoints
- Integrate Pub/Sub
- Deploy to Cloud Run

---

### Phase 2: Worker Service (Week 2-3)
**Effort:** 32 hours

**Deliverables:**
- Pure Python worker
- Pub/Sub subscriber
- Video processing pipeline
- Progress tracking
- Deployed to Cloud Run Jobs

**Key Tasks:**
- Extract video processing logic
- Implement Pub/Sub subscriber
- Create choreography pipeline
- Deploy to Cloud Run Jobs
- Test end-to-end

---

### Phase 3: React Frontend (Week 3-4)
**Effort:** 33 hours

**Deliverables:**
- React SPA
- Authentication UI
- Choreography generation UI
- Collections UI
- Deployed to Cloud Run

**Key Tasks:**
- Create React app with Vite
- Build authentication flow
- Build choreography generation UI
- Build collections UI
- Deploy to Cloud Run

---

### Phase 4: Migration & Cutover (Week 4-5)
**Effort:** 22 hours

**Deliverables:**
- Migrated user data
- Parallel deployment
- Full system testing
- Production cutover
- Old system decommissioned

**Key Tasks:**
- Migrate data
- Deploy in parallel
- Test thoroughly
- Cutover to new system
- Monitor and fix issues

---

## 🔧 Technology Stack

### Frontend
- **Framework:** React 18
- **Routing:** React Router 6
- **HTTP Client:** Axios
- **State Management:** Zustand / React Context
- **Data Fetching:** TanStack Query (React Query)
- **Styling:** Tailwind CSS
- **Build Tool:** Vite
- **Deployment:** Cloud Run

### Backend API
- **Framework:** Django 5.2 + Django REST Framework 3.14
- **Authentication:** djangorestframework-simplejwt
- **Documentation:** drf-spectacular (OpenAPI)
- **Database:** PostgreSQL (Cloud SQL)
- **Message Queue:** Google Cloud Pub/Sub
- **Storage:** Google Cloud Storage
- **Deployment:** Cloud Run

### Worker
- **Language:** Python 3.12
- **Video Processing:** FFmpeg
- **Audio Analysis:** Librosa
- **Pose Detection:** YOLOv8
- **Message Queue:** Google Cloud Pub/Sub
- **Database:** PostgreSQL (Cloud SQL)
- **Storage:** Google Cloud Storage
- **Deployment:** Cloud Run Jobs

### Infrastructure
- **Cloud Platform:** Google Cloud Platform
- **Compute:** Cloud Run + Cloud Run Jobs
- **Database:** Cloud SQL (PostgreSQL)
- **Storage:** Cloud Storage
- **Message Broker:** Cloud Pub/Sub
- **Secrets:** Secret Manager
- **Search:** Elasticsearch Serverless
- **Monitoring:** Cloud Monitoring + Cloud Logging

---

## 📊 Estimated Costs

### Monthly Costs (Production)

| Service | Current | New | Change |
|---------|---------|-----|--------|
| Compute | $120 (Compute Engine) | $145 (Cloud Run) | +$25 |
| Worker | Included | $0.64 (Cloud Run Jobs) | +$0.64 |
| Frontend | Included | $5-10 (Cloud Run) | +$10 |
| Pub/Sub | N/A | $0.01 | +$0.01 |
| Cloud SQL | $15 | $15 | $0 |
| Elasticsearch | $95-200 | $95-200 | $0 |
| Cloud Storage | $2 | $2 | $0 |
| **Total** | **$232-337** | **$263-373** | **+$36** |

**Cost Increase:** ~10-15% for significantly better architecture

**Cost Optimization:**
- Scale frontend to zero when idle (-$5/month)
- Use Cloud CDN for static assets
- Compress videos before upload
- Clean up old tasks and videos

---

## 🎯 Success Criteria

### Technical Metrics
- ✅ API response time <200ms (p95)
- ✅ Video generation time <2 minutes
- ✅ Frontend load time <2 seconds
- ✅ 99.9% uptime for API
- ✅ Zero message loss in Pub/Sub
- ✅ Test coverage >80%

### Business Metrics
- ✅ Zero data loss during migration
- ✅ All existing features working
- ✅ Mobile responsive (Lighthouse >90)
- ✅ User satisfaction maintained
- ✅ No increase in support tickets

### Migration Metrics
- ✅ 100% users migrated
- ✅ 100% choreographies migrated
- ✅ <1 hour downtime during cutover
- ✅ Rollback plan tested and ready

---

## ⚠️ Risks & Mitigation

### High-Risk Items

**1. Data Migration**
- **Risk:** Data loss or corruption during migration
- **Impact:** High
- **Mitigation:** 
  - Thorough testing with production data copy
  - Reversible migration scripts
  - Keep old system running during migration
  - Verify data integrity after migration

**2. Pub/Sub Integration**
- **Risk:** Message loss or processing failures
- **Impact:** High
- **Mitigation:**
  - Dead letter queue for failed messages
  - Retry logic with exponential backoff
  - Monitoring and alerting
  - Manual retry mechanism

**3. Performance Degradation**
- **Risk:** New system slower than old system
- **Impact:** Medium
- **Mitigation:**
  - Load testing before cutover
  - Performance monitoring
  - Optimization based on metrics
  - Rollback plan ready

**4. User Disruption**
- **Risk:** Users unable to access system during migration
- **Impact:** High
- **Mitigation:**
  - Parallel deployment (both systems running)
  - Gradual traffic shift (10% → 50% → 100%)
  - Clear communication to users
  - Rollback plan ready

---

## 🚀 Getting Started

### Prerequisites

1. **GCP Project** with billing enabled
2. **APIs Enabled:**
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Pub/Sub API
   - Cloud Storage API
   - Secret Manager API
3. **Tools Installed:**
   - gcloud CLI
   - Docker
   - Node.js 18+
   - Python 3.12+
4. **Permissions:**
   - Cloud Run Admin
   - Cloud SQL Admin
   - Pub/Sub Admin
   - Storage Admin
   - Secret Manager Admin

### Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd bachata_buddy

# 2. Review specifications
cd .kiro/specs/microservices-migration
cat requirements.md
cat design.md
cat tasks.md

# 3. Set up GCP infrastructure
gcloud config set project YOUR_PROJECT_ID

# Create Pub/Sub topic
gcloud pubsub topics create choreography-generation-requests

# Create Pub/Sub subscription
gcloud pubsub subscriptions create choreography-generation-requests-sub \
  --topic choreography-generation-requests \
  --ack-deadline 600

# 4. Start Phase 1 (Backend API)
# See tasks.md for detailed steps
```

---

## 📖 Additional Resources

### Related Documentation
- [CLOUD_RUN_JOBS_FEASIBILITY.md](../../CLOUD_RUN_JOBS_FEASIBILITY.md) - Cloud Run feasibility analysis
- [ARCHITECTURE_DIAGRAMS.md](../../ARCHITECTURE_DIAGRAMS.md) - Architecture diagrams
- [DEPLOYMENT_COMPARISON.md](../../DEPLOYMENT_COMPARISON.md) - Deployment comparison

### External Resources
- [Django REST Framework](https://www.django-rest-framework.org/)
- [React Documentation](https://react.dev/)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [JWT Authentication](https://jwt.io/)

---

## 📞 Support

### Questions?
- Review the specifications in this directory
- Check the related documentation
- Consult Google Cloud documentation

### Issues?
- Check Cloud Run logs
- Check Pub/Sub metrics
- Review error messages
- Test with Postman/curl

---

## ✅ Next Steps

1. **Review Specifications**
   - Read requirements.md
   - Read design.md
   - Read tasks.md

2. **Get Approval**
   - Review with team
   - Get stakeholder buy-in
   - Confirm timeline and budget

3. **Set Up Infrastructure**
   - Create GCP project
   - Enable APIs
   - Create Pub/Sub topic
   - Set up Cloud SQL

4. **Start Phase 1**
   - Create Django REST Framework project
   - Implement authentication
   - Create API endpoints
   - Deploy to Cloud Run

5. **Continue with Phases 2-4**
   - Follow tasks.md
   - Test thoroughly
   - Deploy incrementally
   - Monitor closely

---

**Status:** ✅ **READY FOR IMPLEMENTATION**

**Estimated Timeline:** 4-5 weeks  
**Estimated Cost:** $263-373/month (10-15% increase)  
**Risk Level:** Medium (mitigated with thorough testing and rollback plan)

**Recommendation:** Proceed with implementation following the phased approach outlined in tasks.md.
