# System Architecture

This document describes the complete system architecture for Bachata Buddy, including local development and AWS production deployment.

## Table of Contents

- [Overview](#overview)
- [Local Development Architecture](#local-development-architecture)
- [AWS Production Architecture](#aws-production-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Scalability](#scalability)
- [Monitoring](#monitoring)

## Overview

Bachata Buddy is a multi-tier application that generates AI-powered dance choreographies using:
- **Backend**: Django REST API (Python 3.12)
- **Frontend**: React SPA (Vite)
- **Database**: PostgreSQL 15
- **Storage**: Local filesystem (dev) or S3 (production)
- **Jobs**: Background video processing service

## Local Development Architecture

### System Diagram

```mermaid
graph TB
    subgraph "Developer Machine"
        subgraph "Docker Compose Environment"
            FE[Frontend Container<br/>React + Vite<br/>Port 3000]
            BE[Backend Container<br/>Django REST API<br/>Port 8000]
            DB[(PostgreSQL<br/>Port 5432)]
            JOB[Job Container<br/>Video Assembly<br/>FFmpeg]
            FS[Local Filesystem<br/>./data/<br/>./media/]
        end
        
        DEV[Developer<br/>Browser]
    end
    
    DEV -->|HTTP :3000| FE
    FE -->|API Calls :8000| BE
    BE -->|SQL| DB
    BE -->|Trigger| JOB
    BE -->|Read/Write| FS
    JOB -->|Read/Write| FS
    JOB -->|Update Status| DB
    
    style FE fill:#61dafb,color:#000
    style BE fill:#092e20,color:#fff
    style DB fill:#336791,color:#fff
    style JOB fill:#ff6d00,color:#fff
    style FS fill:#ffa000,color:#000
```

### Docker Compose Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| **frontend** | node:18 | 3000 | React development server |
| **backend** | python:3.12 | 8000 | Django API server |
| **postgres** | postgres:15 | 5432 | Database |
| **job** | python:3.12 | - | Video processing (triggered) |

### Local Storage Structure

```
bachata_buddy/
├── data/
│   ├── Bachata_steps/          # 150 video clips (source)
│   ├── songs/                  # Audio files
│   └── output/                 # Generated choreographies
├── media/                      # User uploads
└── backend/
    └── staticfiles/            # Django static files
```

## AWS Production Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Users"
        U[Web Browsers<br/>Mobile Devices]
    end
    
    subgraph "AWS Cloud"
        subgraph "Content Delivery"
            CF[CloudFront CDN<br/>Global Edge Locations]
        end
        
        subgraph "Frontend - us-east-1"
            S3F[S3 Bucket<br/>Static Files<br/>React Build]
        end
        
        subgraph "Backend - us-east-1"
            subgraph "Compute"
                AR1[App Runner<br/>Backend API<br/>Auto-scaling]
                AR2[App Runner<br/>Job Service<br/>Scale to Zero]
            end
            
            subgraph "Storage"
                S3M[S3 Bucket<br/>Media Files<br/>Video Outputs]
            end
            
            subgraph "Database"
                RDS[(RDS Aurora<br/>PostgreSQL<br/>Serverless v2)]
            end
            
            subgraph "Container Registry"
                ECR[ECR<br/>Docker Images]
            end
            
            subgraph "Secrets"
                SM[Secrets Manager<br/>Credentials<br/>API Keys]
            end
            
            subgraph "Networking"
                VPC[VPC<br/>Private Subnets<br/>Security Groups]
            end
        end
        
        subgraph "Monitoring"
            CW[CloudWatch<br/>Logs & Metrics<br/>Alarms]
        end
        
        subgraph "External Services"
            GEMINI[Google Gemini API<br/>Natural Language]
        end
    end
    
    U -->|HTTPS| CF
    CF -->|Origin| S3F
    U -->|API Calls| AR1
    AR1 -->|Query| RDS
    AR1 -->|Trigger| AR2
    AR1 -->|Store/Retrieve| S3M
    AR2 -->|Store/Retrieve| S3M
    AR2 -->|Update Status| RDS
    AR1 -->|Pull Image| ECR
    AR2 -->|Pull Image| ECR
    AR1 -->|Get Secrets| SM
    AR2 -->|Get Secrets| SM
    RDS -.->|Inside| VPC
    AR1 -->|NLP| GEMINI
    AR1 -->|Logs| CW
    AR2 -->|Logs| CW
    RDS -->|Metrics| CW
    
    style CF fill:#ff9900,color:#000
    style S3F fill:#569a31,color:#fff
    style S3M fill:#569a31,color:#fff
    style AR1 fill:#ff9900,color:#000
    style AR2 fill:#ff9900,color:#000
    style RDS fill:#527fff,color:#fff
    style ECR fill:#ff9900,color:#000
    style SM fill:#dd344c,color:#fff
    style VPC fill:#ff9900,color:#000
    style CW fill:#ff9900,color:#000
    style GEMINI fill:#4285f4,color:#fff
```

### Network Architecture

```mermaid
graph TB
    subgraph "AWS Region: us-east-1"
        subgraph "VPC: 10.0.0.0/16"
            subgraph "Public Subnet A: 10.0.1.0/24"
                NAT1[NAT Gateway]
            end
            
            subgraph "Public Subnet B: 10.0.2.0/24"
                NAT2[NAT Gateway]
            end
            
            subgraph "Private Subnet A: 10.0.10.0/24"
                RDS1[(RDS Aurora<br/>Primary)]
            end
            
            subgraph "Private Subnet B: 10.0.11.0/24"
                RDS2[(RDS Aurora<br/>Replica)]
            end
            
            IGW[Internet Gateway]
        end
        
        subgraph "App Runner VPC Connector"
            AR[App Runner<br/>Services]
        end
        
        subgraph "S3 VPC Endpoint"
            S3E[S3 Endpoint]
        end
    end
    
    INTERNET[Internet]
    
    INTERNET -->|HTTPS| IGW
    IGW --> NAT1
    IGW --> NAT2
    NAT1 --> RDS1
    NAT2 --> RDS2
    AR -->|Private| RDS1
    AR -->|Private| RDS2
    AR -->|Private| S3E
    
    style IGW fill:#ff9900,color:#000
    style NAT1 fill:#ff9900,color:#000
    style NAT2 fill:#ff9900,color:#000
    style RDS1 fill:#527fff,color:#fff
    style RDS2 fill:#527fff,color:#fff
    style AR fill:#ff9900,color:#000
    style S3E fill:#569a31,color:#fff
```

### Security Groups

```mermaid
graph LR
    subgraph "Security Groups"
        SG1[App Runner SG<br/>Outbound: All<br/>Inbound: HTTPS]
        SG2[RDS SG<br/>Inbound: 5432<br/>From App Runner SG]
    end
    
    AR[App Runner] -->|Uses| SG1
    RDS[(RDS Aurora)] -->|Uses| SG2
    SG1 -->|Can Access| SG2
    
    style SG1 fill:#dd344c,color:#fff
    style SG2 fill:#dd344c,color:#fff
```

## Component Details

### Frontend (React + Vite)

**Technology Stack:**
- React 18.3.1
- Vite 5.0 (build tool)
- Tailwind CSS 3.3
- React Router 6

**Deployment:**
- **Local**: Vite dev server (port 3000)
- **Production**: S3 + CloudFront
  - Build artifacts uploaded to S3
  - CloudFront serves with global caching
  - Custom domain (optional)

**Key Features:**
- Single Page Application (SPA)
- Client-side routing
- JWT authentication
- API integration via fetch

### Backend (Django REST API)

**Technology Stack:**
- Django 5.2
- Django REST Framework
- Python 3.12
- Gunicorn (production server)

**Deployment:**
- **Local**: Django dev server (port 8000)
- **Production**: App Runner
  - Containerized with Docker
  - Auto-scaling (1-10 instances)
  - Health checks enabled
  - Environment variables from Secrets Manager

**Key Services:**
- User authentication (JWT)
- Choreography generation
- Blueprint creation
- Audio analysis (Librosa)
- Text embeddings (Sentence-Transformers)
- Vector search (FAISS)
- Gemini AI integration

**Resource Configuration:**
- CPU: 2 vCPU
- Memory: 2 GB
- Timeout: 300 seconds
- Concurrency: 100 requests/instance

### Job Service (Video Assembly)

**Technology Stack:**
- Python 3.12
- FFmpeg
- Blueprint-based architecture

**Deployment:**
- **Local**: Docker container (triggered by API)
- **Production**: App Runner
  - Containerized with Docker
  - Scale to zero when idle
  - Triggered by API via HTTP
  - Processes blueprints from database

**Key Functions:**
- Parse blueprint JSON
- Fetch video clips from storage
- Assemble video with FFmpeg
- Upload output to storage
- Update task status in database

**Resource Configuration:**
- CPU: 1 vCPU
- Memory: 512 MB
- Timeout: 300 seconds
- Concurrency: 1 job/instance
- Min instances: 0 (scale to zero)
- Max instances: 5

### Database (PostgreSQL)

**Technology Stack:**
- PostgreSQL 15
- Django ORM

**Deployment:**
- **Local**: Docker container (port 5432)
- **Production**: RDS Aurora Serverless v2
  - Multi-AZ for high availability
  - Automatic backups (7-day retention)
  - Automated patching
  - SSL/TLS connections required

**Schema:**
- Users and authentication
- Choreography tasks and blueprints
- Move embeddings (1792D vectors)
- Collections and favorites
- Instructor data

**Resource Configuration:**
- Min ACU: 0.5
- Max ACU: 2
- Storage: Auto-scaling (10 GB - 64 TB)
- Backup retention: 7 days

### Storage

**Local Development:**
- Filesystem: `./data/` and `./media/`
- Direct file access
- No CDN

**Production (S3):**
- **Media Bucket**: Video clips, audio files, outputs
- **Frontend Bucket**: React build artifacts
- Versioning enabled
- Lifecycle policies for cost optimization
- CloudFront CDN for global delivery

**Storage Structure:**
```
s3://bachata-buddy-media/
├── clips/                  # Source video clips
├── songs/                  # Audio files
├── outputs/                # Generated choreographies
└── uploads/                # User uploads

s3://bachata-buddy-frontend/
├── index.html
├── assets/
│   ├── *.js
│   ├── *.css
│   └── *.png
└── favicon.ico
```

## Data Flow

### Choreography Generation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend API
    participant DB as PostgreSQL
    participant GEMINI as Gemini AI
    participant FAISS as FAISS Search
    participant JOB as Job Service
    participant S3 as S3 Storage
    
    U->>FE: Enter query + select song
    FE->>BE: POST /api/choreography/generate
    BE->>GEMINI: Parse natural language query
    GEMINI-->>BE: Structured parameters
    BE->>BE: Analyze audio (Librosa)
    BE->>DB: Fetch move embeddings
    DB-->>BE: 149 move vectors
    BE->>FAISS: Compute similarities
    FAISS-->>BE: Ranked moves
    BE->>BE: Generate blueprint JSON
    BE->>DB: Save task + blueprint
    DB-->>BE: Task ID
    BE-->>FE: Task ID + status
    FE->>FE: Poll for status
    BE->>JOB: Trigger video assembly
    JOB->>DB: Fetch blueprint
    DB-->>JOB: Blueprint JSON
    JOB->>S3: Fetch video clips
    S3-->>JOB: Video files
    JOB->>JOB: Assemble with FFmpeg
    JOB->>S3: Upload output video
    S3-->>JOB: Video URL
    JOB->>DB: Update task status
    DB-->>JOB: Success
    FE->>BE: Poll status
    BE->>DB: Check status
    DB-->>BE: Complete + URL
    BE-->>FE: Video URL
    FE->>U: Display video
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend API
    participant DB as PostgreSQL
    
    U->>FE: Enter credentials
    FE->>BE: POST /api/auth/login
    BE->>DB: Verify credentials
    DB-->>BE: User data
    BE->>BE: Generate JWT tokens
    BE-->>FE: Access + Refresh tokens
    FE->>FE: Store tokens (localStorage)
    FE->>BE: API request + JWT
    BE->>BE: Verify JWT
    BE->>DB: Fetch data
    DB-->>BE: Data
    BE-->>FE: Response
    FE->>U: Display data
```

## Security Architecture

### Authentication & Authorization

**JWT-Based Authentication:**
- Access tokens (15 min expiry)
- Refresh tokens (7 day expiry)
- Secure HTTP-only cookies (production)
- Token rotation on refresh

**Authorization:**
- Role-based access control (RBAC)
- User, Instructor, Admin roles
- Permission-based API endpoints

### Network Security

**VPC Configuration:**
- Private subnets for RDS
- NAT Gateways for outbound traffic
- Security groups for access control
- VPC endpoints for S3 (private access)

**Security Groups:**
- App Runner: Outbound all, Inbound HTTPS only
- RDS: Inbound 5432 from App Runner SG only
- No public internet access to RDS

### Data Security

**Encryption:**
- **In Transit**: TLS 1.2+ for all connections
- **At Rest**: 
  - RDS: AES-256 encryption
  - S3: Server-side encryption (SSE-S3)
  - Secrets Manager: KMS encryption

**Secrets Management:**
- AWS Secrets Manager for credentials
- No secrets in code or environment files
- Automatic rotation (optional)

### Application Security

**Django Security Settings:**
```python
# Production settings
DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

**CORS Configuration:**
- Specific allowed origins (CloudFront domain)
- No wildcard origins in production
- Credentials allowed for authenticated requests

**Input Validation:**
- Django REST Framework serializers
- SQL injection prevention (ORM)
- XSS prevention (template escaping)
- CSRF protection

## Scalability

### Horizontal Scaling

**App Runner Auto-Scaling:**
- Backend: 1-10 instances
- Job: 0-5 instances (scale to zero)
- Metrics: CPU, Memory, Request count
- Scale-up: 70% CPU or 80% memory
- Scale-down: 30% CPU and 50% memory

**RDS Aurora Scaling:**
- Serverless v2: 0.5-2 ACU
- Automatic scaling based on load
- Read replicas (optional)

### Vertical Scaling

**Resource Limits:**
- Backend: 2 vCPU, 2 GB RAM
- Job: 1 vCPU, 512 MB RAM
- Can be increased via CDK configuration

### Caching Strategy

**CloudFront Caching:**
- Static assets: 1 year TTL
- HTML: 5 minutes TTL
- API responses: No caching

**Application Caching:**
- FAISS index: In-memory (rebuilt on startup)
- Move embeddings: Database query caching
- Django query caching (optional)

## Monitoring

### CloudWatch Metrics

**App Runner Metrics:**
- Request count
- Response time (p50, p90, p99)
- Error rate (4xx, 5xx)
- CPU utilization
- Memory utilization
- Active instances

**RDS Metrics:**
- Database connections
- CPU utilization
- Storage usage
- Read/Write IOPS
- Query performance

**S3 Metrics:**
- Request count
- Data transfer
- Error rate

### CloudWatch Logs

**Log Groups:**
- `/aws/apprunner/backend` - Backend API logs
- `/aws/apprunner/job` - Job service logs
- `/aws/rds/cluster/<cluster-id>` - Database logs

**Log Retention:**
- 30 days (configurable)
- Export to S3 for long-term storage

### CloudWatch Alarms

**Critical Alarms:**
- App Runner error rate > 5%
- RDS CPU > 80%
- RDS storage > 85%
- App Runner response time > 5s

**Warning Alarms:**
- App Runner error rate > 1%
- RDS CPU > 60%
- Job processing time > 10 minutes

### Distributed Tracing

**AWS X-Ray (Optional):**
- Request tracing across services
- Performance bottleneck identification
- Error analysis

## Performance Optimization

### Backend Optimization

- Database connection pooling
- Query optimization (indexes, select_related)
- Lazy loading of embeddings
- Async task processing

### Frontend Optimization

- Code splitting (React.lazy)
- Asset compression (gzip, brotli)
- Image optimization
- CDN caching

### Database Optimization

- Indexes on frequently queried fields
- Query result caching
- Connection pooling
- Read replicas for read-heavy workloads

## Disaster Recovery

### Backup Strategy

**RDS Backups:**
- Automated daily backups (7-day retention)
- Manual snapshots before major changes
- Point-in-time recovery (PITR)

**S3 Versioning:**
- Enabled on media bucket
- Lifecycle policies for old versions

### Recovery Procedures

**Database Recovery:**
1. Restore from automated backup
2. Or restore from manual snapshot
3. Update App Runner environment variables
4. Verify data integrity

**Application Recovery:**
1. Rollback to previous Docker image
2. Or redeploy from Git tag
3. Verify functionality

**Infrastructure Recovery:**
1. CDK destroy and redeploy
2. Or restore from CloudFormation snapshot
3. Restore database from backup
4. Redeploy applications

## Cost Optimization

### Strategies

1. **App Runner**: Scale to zero for job service
2. **RDS**: Serverless v2 with low min ACU
3. **S3**: Lifecycle policies to Glacier
4. **CloudFront**: Optimize cache hit ratio
5. **Monitoring**: Set appropriate log retention

### Cost Breakdown

| Service | Monthly Cost | Optimization |
|---------|-------------|--------------|
| App Runner (Backend) | $50-100 | Right-size instances |
| App Runner (Job) | $20-50 | Scale to zero |
| RDS Aurora | $50-150 | Serverless v2, low min ACU |
| S3 | $10-30 | Lifecycle policies |
| CloudFront | $20-50 | Cache optimization |
| **Total** | **$150-380** | |

## Future Enhancements

- Multi-region deployment for global users
- ElastiCache for application caching
- SQS for job queue management
- Lambda for serverless functions
- API Gateway for advanced routing
- WAF for DDoS protection
- Route 53 for DNS management
- Certificate Manager for SSL/TLS
