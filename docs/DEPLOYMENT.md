# Deployment Guide

This guide covers deployment procedures for the Concept platform across different environments.

## Pre-Deployment Checklist

Before deploying to any environment, ensure:

- All tests pass: `npm run test:coverage`
- Type checking passes: `npm run type-check`
- Linting passes: `npm run lint`
- Environment variables are configured
- Database migrations are up to date
- All secrets are properly configured

## Frontend Deployment

### Vercel Deployment

1. Connect GitHub repository to Vercel
2. Configure build settings:
   - Build command: `npm run build --workspace=frontend`
   - Output directory: `frontend/dist`

3. Set environment variables in Vercel dashboard:
   ```
   REACT_APP_API_URL=https://api.yourdomain.com
   REACT_APP_ENVIRONMENT=production
   ```

4. Deploy:
   ```bash
   vercel deploy
   ```

### Netlify Deployment

1. Connect GitHub repository
2. Configure build settings:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `dist`

3. Set environment variables
4. Deploy automatically on push to main

## Backend Deployment

### Docker Deployment

1. Build Docker image:
   ```bash
   cd backend
   docker build -t concept-api:1.0.0 .
   ```

2. Push to registry:
   ```bash
   docker push your-registry/concept-api:1.0.0
   ```

3. Deploy container:
   ```bash
   docker run -p 5000:5000 \
     -e DATABASE_URL=postgresql://... \
     -e JWT_SECRET=... \
     concept-api:1.0.0
   ```

### Kubernetes Deployment

1. Create deployment manifest:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: concept-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: concept-api
     template:
       metadata:
         labels:
           app: concept-api
       spec:
         containers:
         - name: api
           image: your-registry/concept-api:1.0.0
           ports:
           - containerPort: 5000
           env:
           - name: DATABASE_URL
             valueFrom:
               secretKeyRef:
                 name: db-secret
                 key: url
   ```

2. Apply deployment:
   ```bash
   kubectl apply -f deployment.yaml
   ```

## Database Deployment

### PostgreSQL Setup

1. Provision managed PostgreSQL (AWS RDS, DigitalOcean, etc.)

2. Initialize database:
   ```bash
   createdb concept
   ```

3. Run migrations:
   ```bash
   cd backend
   npx prisma migrate deploy
   ```

4. Verify connection:
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

### Backup Strategy

- Daily automated backups
- Point-in-time recovery enabled
- Test recovery procedures monthly
- Keep backups for 30 days minimum

## Environment Configuration

### Production Environment Variables

```bash
# Application
NODE_ENV=production
PORT=5000

# Database
DATABASE_URL=postgresql://user:pass@host:5432/concept

# Authentication
JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRY=7d

# AI Services
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4

# Security
CORS_ORIGIN=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com

# Logging
LOG_LEVEL=info
SENTRY_DSN=https://...
```

## SSL/TLS Configuration

1. Obtain SSL certificate (Let's Encrypt recommended)
2. Configure in reverse proxy (Nginx, HAProxy)
3. Set HSTS header:
   ```
   Strict-Transport-Security: max-age=31536000; includeSubDomains
   ```

## Monitoring & Logging

### Application Monitoring

- New Relic / DataDog for performance
- Sentry for error tracking
- CloudWatch for logs
- Prometheus for metrics

### Health Checks

```bash
# Health endpoint
curl https://api.yourdomain.com/health

# Database check
curl https://api.yourdomain.com/health/db
```

## Scaling Strategy

### Horizontal Scaling

- Use load balancer (AWS ELB, Nginx)
- Auto-scaling groups for backend
- CDN for frontend (CloudFront, Cloudflare)
- Database read replicas

### Vertical Scaling

- Increase server resources
- Optimize database queries
- Implement caching
- Use Redis for sessions

## Disaster Recovery

### Backup Procedures

```bash
# Database backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

### Recovery Time Objectives

- RTO (Recovery Time): 1 hour
- RPO (Recovery Point): 1 hour

## Performance Optimization

### Frontend

- Enable code splitting
- Implement lazy loading
- Optimize images
- Use CDN for static assets

### Backend

- Database query optimization
- Redis caching
- Connection pooling
- API response compression

## Rollback Procedures

### Frontend Rollback

1. Revert to previous commit
2. Rebuild and redeploy
3. Purge CDN cache

### Backend Rollback

```bash
# With Docker
docker run -p 5000:5000 concept-api:previous-version

# With Kubernetes
kubectl set image deployment/concept-api \
  api=your-registry/concept-api:previous-version
```

## Post-Deployment Verification

1. Check application health
2. Verify database connectivity
3. Test critical user flows
4. Monitor error rates and logs
5. Check performance metrics

## Staging Environment

Before production deployment, test in staging:

1. Deploy to staging with production config
2. Run full test suite
3. Performance testing
4. Security scanning
5. User acceptance testing

## Deployment Timeline

Typical deployment process:

```
Code Push → CI/CD Pipeline → Tests → Staging → Approval → Production
   5 min         15 min        10 min    5 min     N/A       5 min
```

## Incident Response

If issues occur post-deployment:

1. Monitor error rates and logs
2. Identify root cause
3. Decide: Continue or Rollback
4. If rollback: Execute rollback procedures
5. Document incident and remediation

## Support & References

- [Architecture Documentation](./ARCHITECTURE.md)
- [Development Setup](./DEVELOPMENT_SETUP.md)
- [API Documentation](./API.md)

For deployment issues, check monitoring dashboards and logs first.
