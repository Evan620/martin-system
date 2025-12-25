# Deployment Guide

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Domain name with SSL certificate
- Cloud storage (AWS S3, Azure Blob, or equivalent)
- Email service credentials (SMTP or API)
- LLM API key (OpenAI or Anthropic)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd martins-system
```

### 2. Configure Environment Variables

```bash
# Root
cp .env.example .env

# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

Edit each `.env` file with your production values.

**Critical Variables**:
- Database connection strings
- Secret keys (use strong random values)
- API keys for LLM, email, calendar
- CORS origins
- Storage credentials

### 3. Setup SSL Certificates

Place SSL certificates in a secure location:
```bash
/etc/ssl/certs/ecowas-summit.crt
/etc/ssl/private/ecowas-summit.key
```

## Deployment Options

### Option 1: Docker Compose (Recommended for Small/Medium Scale)

#### Production docker-compose.yml

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
      - /etc/ssl/certs:/etc/nginx/certs
    depends_on:
      - backend
      - frontend
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - ./backend/.env
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
      - chromadb
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    restart: always

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    restart: always

  celery_worker:
    build:
      context: ./backend
    command: celery -A app.core.scheduler worker -l info
    env_file:
      - ./backend/.env
    depends_on:
      - redis
      - postgres
    restart: always

  celery_beat:
    build:
      context: ./backend
    command: celery -A app.core.scheduler beat -l info
    env_file:
      - ./backend/.env
    depends_on:
      - redis
    restart: always

volumes:
  postgres_data:
  redis_data:
  chroma_data:
```

#### Deploy

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python scripts/create_admin.py
```

### Option 2: Kubernetes (For Large Scale)

#### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-hosted)
- kubectl configured
- Helm 3+

#### Deploy with Helm

```bash
# Add chart repository
helm repo add ecowas-summit ./helm

# Install
helm install ecowas-summit ecowas-summit/summit-system \
  --namespace ecowas \
  --create-namespace \
  --values values.prod.yaml
```

#### Kubernetes Resources

**Deployments**:
- Backend (API) - 3 replicas
- Frontend (nginx) - 2 replicas
- Celery Workers - 2 replicas
- Celery Beat - 1 replica

**StatefulSets**:
- PostgreSQL - 1 replica (or use managed DB)
- Redis - 1 replica (or use managed cache)
- ChromaDB - 1 replica

**Services**:
- Backend (ClusterIP)
- Frontend (LoadBalancer)
- PostgreSQL (ClusterIP)
- Redis (ClusterIP)

**Ingress**:
```yaml
apiVersion: networking.k8.io/v1
kind: Ingress
metadata:
  name: ecowas-summit
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - summit.ecowas.int
      secretName: ecowas-tls
  rules:
    - host: summit.ecowas.int
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
```

### Option 3: Cloud Platform (AWS Example)

#### Services

- **Compute**: ECS Fargate or EKS
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Storage**: S3
- **CDN**: CloudFront
- **Load Balancer**: ALB
- **Secrets**: Secrets Manager
- **Monitoring**: CloudWatch

#### Architecture

```
CloudFront (CDN)
      │
      ▼
Application Load Balancer
      │
      ├─► ECS Service (Frontend)
      └─► ECS Service (Backend)
              │
              ├─► RDS PostgreSQL
              ├─► ElastiCache Redis
              └─► S3 Bucket
```

#### Infrastructure as Code (Terraform)

```hcl
# See terraform/ directory for full configuration

resource "aws_ecs_cluster" "summit" {
  name = "ecowas-summit"
}

resource "aws_db_instance" "postgres" {
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.medium"
  # ...
}

# ...more resources
```

## Database Setup

### Initial Migration

```bash
# Create database
createdb ecowas_summit_db

# Run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

### Seed Data

```bash
# Seed initial TWGs and roles
python scripts/seed_data.py

# Create admin user
python scripts/create_admin.py \
  --email admin@ecowas.int \
  --password <secure_password>
```

### Backups

```bash
# Backup database
pg_dump ecowas_summit_db > backup_$(date +%Y%m%d).sql

# Restore database
psql ecowas_summit_db < backup_20260115.sql
```

**Automated Backups** (cron):
```bash
0 2 * * * /usr/bin/pg_dump ecowas_summit_db > /backups/backup_$(date +\%Y\%m\%d).sql
```

## Monitoring

### Health Checks

```bash
# Backend health
curl https://summit.ecowas.int/api/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "chromadb": "connected"
}
```

### Logs

**Docker Compose**:
```bash
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

**Kubernetes**:
```bash
kubectl logs -f deployment/backend -n ecowas
kubectl logs -f deployment/celery-worker -n ecowas
```

### Metrics

Integrate with monitoring tools:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Sentry**: Error tracking
- **DataDog**: APM

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] Environment variables secured (not in code)
- [ ] Database encrypted at rest
- [ ] Strong passwords for all services
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Security headers set (CSP, HSTS, etc.)
- [ ] Regular backups configured
- [ ] Monitoring and alerts set up
- [ ] Secrets rotated regularly
- [ ] Dependencies updated
- [ ] Audit logging enabled

## Performance Optimization

### Backend

- Enable Gunicorn with multiple workers
- Use connection pooling for database
- Cache frequently accessed data in Redis
- Compress responses with gzip
- Use async/await for I/O operations

### Frontend

- Enable CDN for static assets
- Compress images and assets
- Code splitting for lazy loading
- Service worker for offline support
- Browser caching headers

### Database

- Index frequently queried fields
- Use materialized views for reports
- Connection pooling
- Query optimization
- Regular VACUUM and ANALYZE

## Scaling

### Horizontal Scaling

**Backend**:
```bash
# Docker Compose
docker-compose up -d --scale backend=3

# Kubernetes
kubectl scale deployment/backend --replicas=5 -n ecowas
```

**Celery Workers**:
```bash
kubectl scale deployment/celery-worker --replicas=4 -n ecowas
```

### Vertical Scaling

Increase resources for containers:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Troubleshooting

### Backend not starting

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database connection failed → Check DATABASE_URL
# - Redis connection failed → Check REDIS_URL
# - Missing environment variables → Check .env
```

### Database connection errors

```bash
# Test connection
psql postgresql://user:pass@host:5432/db

# Check PostgreSQL is running
docker-compose ps postgres
```

### Frontend build fails

```bash
# Clear cache
rm -rf frontend/node_modules frontend/.next

# Reinstall
cd frontend && npm install && npm run build
```

## Rollback

```bash
# Docker Compose - use previous image
docker-compose down
git checkout <previous-tag>
docker-compose up -d

# Kubernetes - rollback deployment
kubectl rollout undo deployment/backend -n ecowas
```

## Maintenance

### Update Dependencies

```bash
# Backend
cd backend
pip install --upgrade -r requirements.txt

# Frontend
cd frontend
npm update
```

### Database Maintenance

```bash
# Vacuum database
psql ecowas_summit_db -c "VACUUM ANALYZE;"

# Reindex
psql ecowas_summit_db -c "REINDEX DATABASE ecowas_summit_db;"
```

## Support

For deployment issues:
- Check logs first
- Review documentation
- Contact DevOps team
- Create issue in repository

## License

Proprietary - ECOWAS Summit 2026
