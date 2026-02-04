# Security Documentation

## Threat Model

### Assets Protected

The following assets require protection:

- **User credentials** - Passwords (Argon2id hashed)
- **JWT tokens** - Access tokens (15-min expiry) and refresh tokens (7-day expiry)
- **Personal data** - Names, emails, phone numbers
- **Vacation request data** - Private employee information
- **Audit logs** - System activity records
- **Company/Team data** - Organizational structure

### Threat Actors

| Actor | Description | Mitigation |
|-------|-------------|------------|
| External attackers | Attempting unauthorized access via network | Rate limiting, HTTPS, firewall |
| Malicious insiders | Users accessing other companies' data | Query-level isolation, RBAC |
| Automated bots | Brute force attacks, credential stuffing | Auth rate limiting (5/min), CAPTCHA |
| Script kiddies | Automated attack tools | Defense in depth |

### Identified Threats

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Password brute force | High | Rate limiting (5 req/min), Argon2id |
| JWT token theft | High | Short-lived tokens (15 min), HTTP-only cookies |
| Company data leakage | High | Query-level isolation, RBAC |
| Privilege escalation | High | Role-based access control, permission checks |
| SQL injection | Critical | ORM with parameterized queries (SQLAlchemy) |
| XSS attacks | Medium | CSP headers, input sanitization |
| CSRF attacks | Medium | Same-site cookie attributes |

## Security Controls

### Authentication

**Password Hashing: Argon2id**

Argon2id is the winner of the Password Hashing Competition and provides excellent resistance against GPU and ASIC attacks.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `time_cost` | 2 | Number of iterations |
| `memory_cost` | 65536 KB (64 MB) | Memory usage |
| `parallelism` | 4 | Parallel threads |

**Token Security**

| Token | Expiry | Storage | Flags |
|-------|--------|---------|-------|
| Access Token | 15 minutes | Memory/JavaScript | None |
| Refresh Token | 7 days | HTTP-only cookie | Secure, SameSite |

### Authorization

**Role-Based Access Control (RBAC)**

| Role | Permissions |
|------|-------------|
| Admin | Full system access, user management, company settings |
| Manager | Team management, approve/reject requests, view team analytics |
| User | View calendar, submit vacation requests, view own data |

**Company Isolation**

All queries include company_id filtering to prevent data leakage between tenants.

### Network Security

| Control | Description |
|---------|-------------|
| HTTPS | Caddy with automatic TLS via Let's Encrypt |
| HSTS | Strict-Transport-Security header (1 year, includeSubDomains) |
| CSP | Content-Security-Policy with self-allowances |
| Rate Limiting | Caddy (10 req/min auth), Backend (5 req/min auth, 100 req/min API) |

### Application Security Headers

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-Robots-Tag` | `noindex, nofollow` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |

## Hardening Checklist

### Pre-Deployment

- [ ] Change all default passwords (admin password, database password)
- [ ] Set strong `JWT_SECRET` (minimum 32 characters, random)
- [ ] Configure proper `CORS_ORIGINS` for your domain
- [ ] Set `ENVIRONMENT=production`
- [ ] Generate strong database credentials
- [ ] Configure admin email address

### Production Deployment

- [ ] Enable HTTPS (set `HTTPS_MODE=public`)
- [ ] Configure valid TLS email for Let's Encrypt
- [ ] Set up regular automated backups
- [ ] Configure log monitoring/aggregation
- [ ] Enable firewall (ufw) - allow only 80, 443
- [ ] Disable SSH password authentication (use keys only)
- [ ] Configure fail2ban for SSH protection
- [ ] Set up log rotation

### Raspberry Pi Specific

- [ ] Enable full-disk encryption (LUKS)
- [ ] Configure secure boot
- [ ] Set up automatic security updates (`unattended-upgrades`)
- [ ] Monitor system resources (CPU, RAM, SD card health)
- [ ] Use industrial-grade SD card (SanDisk Max Endurance)
- [ ] Configure proper cooling (heatsink case)
- [ ] Enable hardware watchdog timer
- [ ] Configure regular SD card health checks

### Monitoring & Alerting

- [ ] Monitor disk usage (alert at 80%)
- [ ] Monitor memory usage (alert at 80%)
- [ ] Monitor API response times
- [ ] Monitor failed authentication attempts
- [ ] Monitor rate limit triggers
- [ ] Set up uptime monitoring

## Incident Response

### Suspected Breach

1. **Immediate Actions**
   - Isolate affected container: `docker-compose stop backend`
   - Preserve logs: `docker-compose logs > incident_$(date +%Y%m%d_%H%M%S).log`
   - Rotate JWT secrets and passwords

2. **Investigation**
   - Review audit logs for suspicious activity
   - Check rate limit logs for attacks
   - Review failed authentication attempts

3. **Recovery**
   - Restore from known-good backup if needed
   - Reset all user passwords
   - Invalidate all active sessions
   - Apply security patches

### Contact

For security issues, contact: `admin@[your-domain]`

## Compliance

This application is designed with privacy-by-design principles:

- **Data minimization**: Only collect necessary data
- **Purpose limitation**: Data used only for vacation management
- **Storage limitation**: Automatic cleanup of old logs
- **Integrity**: Password hashing with salt

## References

- [OWASP Top 10](https://owasp.org/Top10/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
