# Fitbit Integration - Deployment Checklist

## Pre-Deployment Checklist

### Environment Setup
- [ ] Python 3.8+ installed
- [ ] PostgreSQL database created (production)
- [ ] HAPI FHIR server accessible
- [ ] Fitbit Developer account created
- [ ] Fitbit app registered with correct callback URL

### Configuration
- [ ] `.env` file created from `.env.example`
- [ ] `FITBIT_CLIENT_ID` configured
- [ ] `FITBIT_CLIENT_SECRET` configured
- [ ] `FITBIT_REDIRECT_URI` configured (matches Fitbit app settings)
- [ ] `ENCRYPTION_KEY` generated and configured
- [ ] `DATABASE_URL` configured
- [ ] `FHIR_BASE_URL` configured
- [ ] `SECRET_KEY` changed from default

### Dependencies
- [ ] `requirements.txt` installed: `pip install -r requirements.txt`
- [ ] All imports working (run `test_fitbit_setup.py`)
- [ ] Database tables created (Alembic or auto-create)

### Testing
- [ ] Backend server starts successfully
- [ ] Health check endpoint working: `GET /health`
- [ ] API documentation accessible: `/docs`
- [ ] Can create user and login
- [ ] Can select Fitbit vendor
- [ ] OAuth flow completes successfully
- [ ] Can sync Fitbit data
- [ ] FHIR observations created correctly
- [ ] Can retrieve observations via API

## Development Environment

### Local Setup Steps
1. [ ] Clone repository
2. [ ] Create virtual environment: `python -m venv venv`
3. [ ] Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix: `source venv/bin/activate`
4. [ ] Install dependencies: `pip install -r requirements.txt`
5. [ ] Copy `.env.example` to `.env`
6. [ ] Configure environment variables
7. [ ] Generate encryption key
8. [ ] Start FHIR server (Docker)
9. [ ] Run test script: `python test_fitbit_setup.py`
10. [ ] Start backend: `uvicorn app.main:app --reload`

### Development Testing
- [ ] Test vendor selection endpoint
- [ ] Test OAuth flow in browser
- [ ] Test sync with actual Fitbit device
- [ ] Test observation retrieval
- [ ] Test pagination
- [ ] Test filtering
- [ ] Test error handling
- [ ] Test token refresh
- [ ] Test token encryption/decryption

## Production Deployment

### Infrastructure
- [ ] Production server provisioned
- [ ] PostgreSQL database setup
- [ ] HAPI FHIR server deployed
- [ ] Redis server setup (for OAuth state)
- [ ] Celery workers configured
- [ ] SSL/TLS certificate installed
- [ ] Domain name configured
- [ ] Firewall rules configured

### Application Configuration
- [ ] Environment set to `production`
- [ ] Debug mode disabled
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Error tracking setup (Sentry, etc.)
- [ ] Monitoring configured
- [ ] Backup system setup

### Security
- [ ] HTTPS enforced
- [ ] Encryption key securely stored
- [ ] Database credentials secure
- [ ] Fitbit credentials secure
- [ ] JWT secret key rotated
- [ ] API keys not in code
- [ ] `.env` not in version control
- [ ] Security headers configured

### Database
- [ ] Database migrations run
- [ ] Database backups configured
- [ ] Connection pooling configured
- [ ] Database indexes created
- [ ] Database performance tuned

### Fitbit Configuration
- [ ] Production callback URL updated in Fitbit app
- [ ] OAuth scopes verified
- [ ] Rate limits documented
- [ ] Error handling tested

### Performance
- [ ] Load testing completed
- [ ] Response times acceptable
- [ ] Database queries optimized
- [ ] Caching implemented
- [ ] Background tasks working

### Documentation
- [ ] API documentation deployed
- [ ] Admin documentation available
- [ ] Deployment guide created
- [ ] Troubleshooting guide available
- [ ] Architecture diagram updated

## Post-Deployment

### Verification
- [ ] Health check endpoint responding
- [ ] Can register new user
- [ ] Can login
- [ ] Can select Fitbit vendor
- [ ] OAuth flow works in production
- [ ] Can sync data
- [ ] Observations created in FHIR
- [ ] API returns correct data

### Monitoring
- [ ] Application logs being collected
- [ ] Error alerts configured
- [ ] Performance metrics tracked
- [ ] Uptime monitoring active
- [ ] Database metrics monitored

### Documentation
- [ ] Production URL documented
- [ ] API endpoints documented
- [ ] Known issues documented
- [ ] Support contacts updated

## Mobile App Integration

### Flutter Integration Checklist
- [ ] Update API base URL to production
- [ ] Configure OAuth callback handling
- [ ] Test vendor selection from mobile
- [ ] Test OAuth flow in webview
- [ ] Test data sync from mobile
- [ ] Test observation retrieval
- [ ] Handle token expiration
- [ ] Handle network errors
- [ ] Test offline mode
- [ ] Test background sync

## Maintenance

### Regular Tasks
- [ ] Monitor API usage
- [ ] Review error logs
- [ ] Check sync success rates
- [ ] Monitor token refresh failures
- [ ] Review FHIR server status
- [ ] Database backups verified
- [ ] Security updates applied
- [ ] Dependencies updated

### Monthly Tasks
- [ ] Review Fitbit API changes
- [ ] Check for new FHIR resources
- [ ] Performance review
- [ ] Security audit
- [ ] Cost analysis
- [ ] User feedback review

### Quarterly Tasks
- [ ] Rotate encryption keys
- [ ] Update documentation
- [ ] Review architecture
- [ ] Plan new features
- [ ] Compliance review

## Troubleshooting Checklist

### OAuth Issues
- [ ] Check Fitbit credentials are correct
- [ ] Verify callback URL matches exactly
- [ ] Check state token is valid
- [ ] Verify HTTPS in production
- [ ] Check Fitbit app status

### Sync Issues
- [ ] Check user has FHIR patient ID
- [ ] Verify FHIR server is accessible
- [ ] Check OAuth tokens are valid
- [ ] Review API logs for errors
- [ ] Check Fitbit API rate limits

### Token Issues
- [ ] Verify encryption key hasn't changed
- [ ] Check token expiration times
- [ ] Test token refresh
- [ ] Verify refresh token exists

### Database Issues
- [ ] Check connection string
- [ ] Verify migrations are current
- [ ] Check for table locks
- [ ] Review slow queries

### FHIR Issues
- [ ] Verify FHIR server is running
- [ ] Check FHIR base URL
- [ ] Test FHIR connectivity
- [ ] Review FHIR error responses

## Rollback Plan

### If Deployment Fails
1. [ ] Stop new deployments
2. [ ] Identify the issue
3. [ ] Document the error
4. [ ] Revert to previous version
5. [ ] Verify rollback successful
6. [ ] Notify stakeholders
7. [ ] Fix issue in development
8. [ ] Test fix thoroughly
9. [ ] Redeploy with fix

### Database Rollback
1. [ ] Identify migration to revert
2. [ ] Backup current database
3. [ ] Run downgrade: `alembic downgrade -1`
4. [ ] Verify data integrity
5. [ ] Test application
6. [ ] Document rollback reason

## Support

### Contact Information
- [ ] Technical support email configured
- [ ] Emergency contact list created
- [ ] Escalation procedure documented
- [ ] On-call schedule defined

### Resources
- [ ] Documentation links shared
- [ ] API examples available
- [ ] Troubleshooting guide accessible
- [ ] FAQ created

## Completion

### Final Verification
- [ ] All checklist items completed
- [ ] System fully tested
- [ ] Documentation complete
- [ ] Team trained
- [ ] Stakeholders notified
- [ ] Go-live date confirmed

---

## Quick Reference

**Test Setup:**
```bash
python test_fitbit_setup.py
```

**Start Development:**
```bash
uvicorn app.main:app --reload
```

**Run Migration:**
```bash
alembic upgrade head
```

**Generate Encryption Key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Check Health:**
```bash
curl http://localhost:8000/health
```

---

**Last Updated:** December 2024
**Version:** 1.0.0
