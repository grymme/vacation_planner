# Vacation Planner - Improvement Proposals

This document proposes 25+ improvements for the Vacation Planner application, categorized by priority and perspective. Each improvement includes impact assessment, implementation effort, and rationale.

---

## 🔴 Critical Security Improvements (Must Do)

### 1. Password Complexity Enforcement
**Priority: Critical | Impact: High | Effort: Low**

**Current State:** No password complexity requirements beyond minimum 8 characters.

**Problem:** Weak passwords are susceptible to brute force attacks.

**Implementation:**
```python
# In backend/app/schemas.py - Update password validation
import re

class SetPasswordRequest(BaseModel):
    password: str
    confirm_password: str
    
    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
```

**Files to modify:** `backend/app/schemas.py`

---

### 2. Account Lockout After Failed Attempts
**Priority: Critical | Impact: High | Effort: Medium**

**Current State:** No account lockout mechanism.

**Problem:** Brute force attacks can attempt unlimited passwords.

**Implementation:**
```python
# In backend/app/middleware/rate_limit.py - Add account lockout
class AccountLockoutStore:
    def __init__(self):
        self._attempts = defaultdict(list)
        self._locked = defaultdict(bool)
    
    async def check_login(self, email: str) -> tuple[bool, str]:
        now = time.time()
        window_start = now - 900  # 15 minutes
        
        # Clean old attempts
        self._attempts[email] = [t for t in self._attempts[email] if t > window_start]
        
        if self._locked[email]:
            return False, "Account locked due to too many failed attempts. Try again in 15 minutes."
        
        if len(self._attempts[email]) >= 5:
            self._locked[email] = True
            # Schedule unlock after 15 minutes
            asyncio.get_event_loop().call_later(900, lambda: self._locked.__setitem__(email, False))
            return False, "Account locked due to too many failed attempts."
        
        return True, ""
    
    def record_failure(self, email: str):
        self._attempts[email].append(time.time())
```

**Files to modify:** `backend/app/middleware/rate_limit.py`, `backend/app/routers/auth.py`

---

### 3. Secure Session Management with Token Rotation
**Priority: Critical | Impact: High | Effort: Medium**

**Current State:** Refresh tokens are valid for 7 days without rotation.

**Problem:** Stolen refresh tokens can be used for extended periods.

**Implementation:**
```python
# In backend/app/auth.py - Add token rotation

def create_refresh_token(user_id: UUID) -> str:
    token_id = uuid.uuid4()  # Unique token ID
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "sub": str(user_id),
        "jti": str(token_id),  # Token ID for rotation tracking
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# In database - Add token blacklist table for rotation
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    token_jti: Mapped[str] = Column(String(255), unique=True)
    expires_at: Mapped[datetime] = Column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
```

**Files to modify:** `backend/app/auth.py`, `backend/app/models.py`, `backend/app/routers/auth.py`

---

### 4. CSRF Protection for API Endpoints
**Priority: Critical | Impact: High | Effort: Medium**

**Current State:** No explicit CSRF protection.

**Problem:** Cross-site request forgery attacks possible.

**Implementation:**
```python
# In backend/app/middleware/csrf.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            origin = request.headers.get("origin")
            allowed_origins = settings.CORS_ORIGINS
            
            # Check if origin is allowed
            if origin and origin not in allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"}
                )
            
            # Verify referer for browser requests
            referer = request.headers.get("referer")
            if referer and not any(referer.startswith(o) for o in allowed_origins):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"}
                )
        
        return await call_next(request)
```

**Files to modify:** `backend/app/middleware/csrf.py`, `backend/app/main.py`

---

### 5. Input Validation and Sanitization
**Priority: Critical | Impact: High | Effort: Medium**

**Current State:** Basic Pydantic validation only.

**Problem:** Potential for injection attacks and malicious input.

**Implementation:**
```python
# In backend/app/schemas.py - Add sanitization utilities
import bleach

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS."""
    allowed_tags = []
    allowed_attributes = {}
    strip = True
    
    return bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=strip
    )

# Apply to all text fields in schemas
class VacationRequestCreate(BaseModel):
    start_date: date
    end_date: date
    vacation_type: str = "annual"
    reason: Optional[str] = None
    team_id: Optional[UUID] = None
    
    @validator('reason', 'vacation_type')
    def sanitize_text(cls, v):
        if v:
            return sanitize_input(v)
        return v
```

**Files to modify:** `backend/app/schemas.py`, all input schemas

---

## 🟠 High Priority Improvements

### 6. Two-Factor Authentication (2FA)
**Priority: High | Impact: High | Effort: High**

**Current State:** No 2FA support.

**Problem:** Single factor authentication is vulnerable.

**Implementation:**
- Add TOTP (Time-based One-Time Password) support
- Use `pyotp` library for TOTP generation
- Store hashed secrets in database
- Optional per-user enablement

**New Dependencies:** `pyotp==2.9.0`, `qrcode==7.4.2`

**Files to add:** `backend/app/routers/two_factor.py`, `frontend/src/pages/TwoFactorSetup.tsx`

---

### 7. Audit Log Retention and Search
**Priority: High | Impact: Medium | Effort: Medium**

**Current State:** Audit logs exist but no retention policy or search.

**Problem:** Difficult to investigate security incidents.

**Implementation:**
```python
# In backend/app/routers/admin.py - Add audit log search
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def search_audit_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action: Optional[AuditAction] = None,
    actor_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditLog)
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    if action:
        query = query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()
```

**Files to modify:** `backend/app/routers/admin.py`, create frontend audit log viewer

---

### 8. API Versioning
**Priority: High | Impact: Medium | Effort: Low**

**Current State:** Single API version.

**Problem:** Breaking changes will affect existing clients.

**Implementation:**
```python
# In backend/app/main.py - Add API versioning
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")

# All existing routers registered to v1_router
app.include_router(v1_router, prefix="/api")

# Reserve v2 path for future use
@app.get("/api/v2")
async def api_v2_notice():
    return {"message": "API v2 coming soon"}
```

**Files to modify:** `backend/app/main.py`, update frontend API URLs

---

### 9. Request Validation Logging
**Priority: High | Impact: Medium | Effort: Low**

**Current State:** No logging of validation failures.

**Problem:** Cannot detect attacks or debugging issues.

**Implementation:**
```python
# In backend/app/middleware/validation_logging.py
import logging

logger = logging.getLogger(__name__)

class ValidationLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValidationError as e:
            logger.warning(
                f"Validation error: {e.errors()} - Path: {request.url.path} - IP: {request.client.host}"
            )
            raise
        except Exception as e:
            logger.error(f"Request error: {str(e)} - Path: {request.url.path}")
            raise
```

**Files to add:** `backend/app/middleware/validation_logging.py`

---

### 10. Frontend Performance Optimization
**Priority: High | Impact: Medium | Effort: Medium**

**Current State:** No code splitting or lazy loading.

**Problem:** Initial load time may be slow on Pi 5.

**Implementation:**
```typescript
// In frontend/src/App.tsx - Add lazy loading
import React, { Suspense, lazy } from 'react';

const Login = lazy(() => import('./components/Login'));
const Calendar = lazy(() => import('./components/Calendar'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const TeamsPage = lazy(() => import('./pages/TeamsPage'));

function Loading() {
  return <div className="loading">Loading...</div>;
}

// Update routes to use Suspense
<Suspense fallback={<Loading />}>
  <Routes>...</Routes>
</Suspense>
```

**Files to modify:** `frontend/src/App.tsx`

---

### 11. SQLite Performance Tuning
**Priority: High | Impact: High | Effort: Low**

**Current State:** Default SQLite settings.

**Problem:** SQLite may have performance issues under load.

**Implementation:**
```python
# In backend/app/database.py - Add SQLite optimization
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Enable WAL mode for better concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    # Increase cache size (default is -2000, set to 64MB)
    cursor.execute("PRAGMA cache_size=-64000")
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    # Synchronous mode for durability
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

**Files to modify:** `backend/app/database.py`

---

## 🟡 Medium Priority Improvements

### 12. Email Notifications
**Priority: Medium | Impact: Medium | Effort: Medium**

**Current State:** Dev mailer logs to console only.

**Problem:** Users don't receive notifications.

**Implementation:**
```python
# In backend/app/email.py - Add email service
from fastapi import BackgroundTasks

class EmailService:
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, from_address: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_address = from_address
    
    async def send_email(self, to: str, subject: str, body: str):
        import aiosmtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = to
        
        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_user,
            password=self.smtp_password,
            use_tls=True
        )

# Trigger emails on vacation status changes
async def notify_vacation_status(vacation_request: VacationRequest, status: str):
    email_service = get_email_service()
    subject = f"Vacation Request {status}"
    body = f"Your vacation request for {vacation_request.start_date} to {vacation_request.end_date} has been {status}."
    await email_service.send_email(vacation_request.user.email, subject, body)
```

**New Dependencies:** `aiosmtplib==1.2.0`, `email-validator==2.1.0`

**Files to add:** `backend/app/email.py`

---

### 13. Calendar Recurring Events
**Priority: Medium | Impact: Medium | Effort: High**

**Current State:** Only single-date vacation requests.

**Problem:** Users with regular schedules need recurring entries.

**Implementation:**
- Add recurrence patterns (daily, weekly, monthly, custom)
- Store recurrence rules in separate table
- Expand single requests into recurring instances
- Add recurrence UI to calendar component

**Files to add:** `backend/app/models.py` (RecurringEvent), `backend/app/schemas.py`, update frontend calendar

---

### 14. User Preferences and Settings
**Priority: Medium | Impact: Low | Effort: Medium**

**Current State:** No user preferences.

**Problem:** Cannot customize calendar view, notifications, etc.

**Implementation:**
```python
# In backend/app/models.py - Add user preferences
class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    default_view: Mapped[str] = Column(String(50), default="dayGridMonth")
    timezone: Mapped[str] = Column(String(50), default="UTC")
    email_notifications: Mapped[bool] = Column(Boolean, default=True)
    vacation_reminder_days: Mapped[int] = Column(Integer, default=1)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Files to modify:** `backend/app/models.py`, add preferences API, update frontend

---

### 15. Team Vacation Calendar View
**Priority: Medium | Impact: Medium | Effort: Medium**

**Current State:** Individual calendar views only.

**Problem:** Managers need team-wide vacation overview.

**Implementation:**
```typescript
// In frontend/src/components/Calendar.tsx - Add team view
interface TeamCalendarProps {
  teamId: string;
  showPending: boolean;
}

function TeamCalendar({ teamId, showPending }: TeamCalendarProps) {
  const [events, setEvents] = useState<VacationEvent[]>([]);
  
  useEffect(() => {
    vacationApi.getTeamVacationRequests(teamId, { status: showPending ? undefined : 'approved' })
      .then(response => setEvents(response.data));
  }, [teamId, showPending]);
  
  return <FullCalendar events={events} />;
}
```

**Files to modify:** `frontend/src/components/Calendar.tsx`, `backend/app/routers/teams.py`

---

### 16. API Rate Limiting with Redis
**Priority: Medium | Impact: Medium | Effort: Medium**

**Current State:** In-memory rate limiting.

**Problem:** Rate limits reset on container restart, not scalable.

**Implementation:**
```python
# Replace in-memory store with Redis
import aioredis

class RedisRateLimitStore:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(redis_url)
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        window_start = now - window
        
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        
        return results[2] <= limit
```

**New Dependencies:** `aioredis==2.0.1`

**Files to modify:** `backend/app/middleware/rate_limit.py`

---

### 17. Data Export/Import
**Priority: Medium | Impact: Low | Effort: Medium**

**Current State:** No data portability.

**Problem:** Cannot backup/restore individual users or teams.

**Implementation:**
```python
# In backend/app/routers/admin.py - Add export/import
@router.post("/export-data")
async def export_company_data(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Export all company data as JSON."""
    data = {
        "company": current_user.company.__dict__,
        "functions": [f.__dict__ for f in current_user.company.functions],
        "teams": [t.__dict__ for t in current_user.company.teams],
        "users": [u.__dict__ for u in current_user.company.users],
        "export_date": datetime.now(timezone.utc).isoformat()
    }
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=company_backup_{date.today()}.json"}
    )
```

**Files to modify:** `backend/app/routers/admin.py`

---

### 18. Activity Feed/Dashboard
**Priority: Medium | Impact: Medium | Effort: Medium**

**Current State:** No activity dashboard.

**Problem:** No quick overview of recent activity.

**Implementation:**
```python
# In backend/app/routers/dashboard.py - New router
@router.get("/dashboard")
async def get_dashboard(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics and recent activity."""
    if current_user.role == UserRole.ADMIN:
        return {
            "total_users": await db.scalar(select(func.count(User.id))),
            "total_requests": await db.scalar(select(func.count(VacationRequest.id))),
            "pending_requests": await db.scalar(
                select(func.count(VacationRequest.id)).where(VacationRequest.status == "pending")
            ),
            "recent_activity": await get_recent_activity(db, limit=10)
        }
    # Add similar for MANAGER and USER roles
```

**Files to add:** `backend/app/routers/dashboard.py`, update main.py, create frontend dashboard

---

### 19. Integration API (Webhooks)
**Priority: Medium | Impact: Low | Effort: Medium**

**Current State:** No external integrations.

**Problem:** Cannot integrate with HR systems, Slack, etc.

**Implementation:**
```python
# In backend/app/routers/webhooks.py - New router
@router.post("/webhooks/{webhook_id}")
async def receive_webhook(
    webhook_id: UUID,
    request: WebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    """Receive external webhook and process."""
    webhook = await db.execute(
        select(WebhookConfig).where(
            and_(
                WebhookConfig.id == webhook_id,
                WebhookConfig.is_active == True
            )
        )
    )
    # Process webhook based on event type
    if request.event == "vacation.created":
        pass  # Handle new vacation
    elif request.event == "vacation.approved":
        pass  # Handle approval
    return {"status": "processed"}
```

**Files to add:** `backend/app/routers/webhooks.py`, `backend/app/models.py` (WebhookConfig)

---

### 20. Mobile-Friendly Responsive Design
**Priority: Medium | Impact: Medium | Effort: Medium**

**Current State:** Basic responsive design.

**Problem:** Poor mobile experience on small screens.

**Implementation:**
```css
/* In frontend/src/App.css - Add mobile styles */
@media (max-width: 768px) {
  .calendar-wrapper {
    padding: 10px;
  }
  
  .fc-toolbar {
    flex-direction: column;
    gap: 10px;
  }
  
  .header-content {
    flex-direction: column;
    height: auto;
    padding: 10px;
  }
  
  .main-nav {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .modal {
    margin: 10px;
    max-width: calc(100% - 20px);
  }
}
```

**Files to modify:** `frontend/src/App.css`, `frontend/src/components/*.css`

---

## 🟢 Low Priority Improvements

### 21. Dark Mode Support
**Priority: Low | Impact: Low | Effort: Low**

**Implementation:** Add dark mode toggle using CSS variables and localStorage preference.

**Files to modify:** `frontend/src/App.css`, `frontend/src/components/Header.tsx`

---

### 22. Multi-Language Support (i18n)
**Priority: Low | Impact: Low | Effort: Medium**

**Implementation:** Add internationalization with react-i18next for frontend, i18next for backend messages.

**New Dependencies:** `i18next==23.7.20`, `react-i18next==14.0.0`

**Files to add:** `frontend/src/i18n/`, update all frontend text

---

### 23. Accessibility (WCAG 2.1 AA)
**Priority: Low | Impact: Medium | Effort: Medium**

**Implementation:**
- Add ARIA labels to all interactive elements
- Ensure keyboard navigation works
- Add screen reader support
- Maintain color contrast ratios

**Files to modify:** All frontend components

---

### 24. Performance Monitoring with APM
**Priority: Low | Impact: Medium | Effort: Medium**

**Implementation:** Add Application Performance Monitoring with OpenTelemetry or Prometheus metrics.

**New Dependencies:** `prometheus-client==0.19.0`, `opentelemetry-api==1.21.0`

**Files to modify:** `backend/app/main.py` (add /metrics endpoint)

---

### 25. Database Migration to TiDB or CockroachDB
**Priority: Low | Impact: High | Effort: High**

**Implementation:** For future scaling, consider migrating from SQLite to a distributed SQL database.

**Files to modify:** `backend/app/database.py`, `backend/app/config.py`, requirements.txt

---

## Summary Table

| # | Improvement | Priority | Impact | Effort |
|---|-------------|----------|--------|--------|
| 1 | Password Complexity | Critical | High | Low |
| 2 | Account Lockout | Critical | High | Medium |
| 3 | Token Rotation | Critical | High | Medium |
| 4 | CSRF Protection | Critical | High | Medium |
| 5 | Input Sanitization | Critical | High | Medium |
| 6 | Two-Factor Auth | High | High | High |
| 7 | Audit Log Search | High | Medium | Medium |
| 8 | API Versioning | High | Medium | Low |
| 9 | Validation Logging | High | Medium | Low |
| 10 | Lazy Loading | High | Medium | Medium |
| 11 | SQLite Tuning | High | High | Low |
| 12 | Email Notifications | Medium | Medium | Medium |
| 13 | Recurring Events | Medium | Medium | High |
| 14 | User Preferences | Medium | Low | Medium |
| 15 | Team Calendar | Medium | Medium | Medium |
| 16 | Redis Rate Limit | Medium | Medium | Medium |
| 17 | Data Export/Import | Medium | Low | Medium |
| 18 | Activity Dashboard | Medium | Medium | Medium |
| 19 | Webhooks API | Medium | Low | Medium |
| 20 | Mobile Responsive | Medium | Medium | Medium |
| 21 | Dark Mode | Low | Low | Low |
| 22 | Multi-Language | Low | Low | Medium |
| 23 | Accessibility | Low | Medium | Medium |
| 24 | APM/Monitoring | Low | Medium | Medium |
| 25 | Distributed DB | Low | High | High |

---

## Recommendations

### Immediate Actions (This Week)
1. **Password Complexity** - Prevent weak passwords
2. **Account Lockout** - Stop brute force attacks
3. **CSRF Protection** - Prevent cross-site attacks
4. **SQLite Tuning** - Improve Pi 5 performance

### Short-Term Actions (This Month)
5. **Input Sanitization** - XSS prevention
6. **API Versioning** - Future-proof the API
7. **Validation Logging** - Detect attacks early
8. **Lazy Loading** - Improve frontend performance

### Medium-Term Actions (Quarter)
9-19 above based on business priorities

### Long-Term Actions (Year)
20-25 above based on scaling needs
