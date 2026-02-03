# Vacation Planner Application - Architecture Document

## Phase 0: Architecture & Planning Document

**Version:** 1.0  
**Date:** 2026-02-03  
**Platform:** Raspberry Pi 5 (arm64)  
**Database:** SQLite (chosen for resource efficiency on Pi 5)

---

## 1. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                         React SPA Browser App                           │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │     │
│  │  │   Login     │  │  Dashboard  │  │  Calendar   │  │   Reports    │  │     │
│  │  │   Page      │  │             │  │   View      │  │   Export     │  │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │     │
│  │                                                                        │     │
│  │  FullCalendar.js   Axios   React Router   Tailwind CSS   JWT Auth    │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ HTTPS (443)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REVERSE PROXY LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                           Caddy Server                                  │     │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │     │
│  │  │   TLS/HTTPS     │  │  Static Assets  │  │    Reverse Proxy        │ │     │
│  │  │   Termination  │  │     Serving     │  │    (API Routing)        │ │     │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │     │
│  │                                                                        │     │
│  │  Automatic TLS Certificates via Let's Encrypt                           │     │
│  │  Caddyfile: vacation.domain.com -> backend:8000                        │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ HTTP (8000)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND SERVICE LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                        FastAPI Application                               │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │     │
│  │  │                      API Routes                                  │   │     │
│  │  │  /auth/*    │   /users/*   │   /vacations/*   │   /exports/*   │   │     │
│  │  └───────────────────────────────────────────────────────────────────┘   │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │     │
│  │  │                    Middleware Stack                               │   │     │
│  │  │  JWT Auth │ Rate Limiting │ Request Validation │ Logging        │   │     │
│  │  └───────────────────────────────────────────────────────────────────┘   │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │     │
│  │  │                    Business Logic Layer                          │   │     │
│  │  │  Auth Service │ User Service │ Vacation Service │ Export Service │   │     │
│  │  └───────────────────────────────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ SQLAlchemy 2.0 ORM
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │                          SQLite Database                                 │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │     │
│  │  │                    Application.db                                  │   │     │
│  │  │  vacation.db (file-based, located on persistent storage)          │   │     │
│  │  └───────────────────────────────────────────────────────────────────┘   │     │
│  │                                                                        │     │
│  │  Connection pooling via SQLAlchemy 2.0                                 │     │
│  │  WAL mode enabled for concurrent access                                 │     │
│  │  Foreign keys enabled                                                  │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagrams

#### Authentication Flow

```
User Login Flow:
┌────────┐     HTTPS      ┌────────┐    HTTP     ┌────────┐     SQL      ┌────────┐
│ Browser│ ─────────────► │  Caddy │ ──────────► │FastAPI │ ───────────► │ SQLite │
│        │                │ (TLS)  │             │        │              │        │
└────────┘                └────────┘             └────────┘              └────────┘
    │                          │                    │                         │
    │  1. POST /auth/login     │                    │                         │
    │  {email, password}       │                    │                         │
    │◄─────────────────────────│                    │                         │
    │  JWT Access + Refresh    │                    │                         │
    │  Set-Cookie: refresh     │                    │                         │
```

#### Vacation Request Flow

```
Vacation Request Flow:
┌────────┐     HTTPS      ┌────────┐    HTTP     ┌────────┐     SQL      ┌────────┐
│ Browser│ ─────────────► │  Caddy │ ──────────► │FastAPI │ ───────────► │ SQLite │
│        │                │ (TLS)  │             │        │              │        │
└────────┘                └────────┘             └────────┘              └────────┘
    │                          │                    │                         │
    │  POST /vacations/         │                    │                         │
    │  Authorization: Bearer   │                    │                         │
    │  JWT                     │                    │                         │
    │◄─────────────────────────│                    │                         │
    │  201 Created +           │                    │                         │
    │  Vacation Request        │                    │                         │
```

---

## 2. Data Model

### 2.1 Database Design Principles

- **Database Engine:** SQLite 3.40+ with WAL mode for concurrent access
- **ORM:** SQLAlchemy 2.0 with async support
- **Primary Keys:** UUID v4 for all tables (distributed, no single point of failure)
- **Soft Deletes:** Implemented via `deleted_at` timestamp on all transactional tables
- **Timestamps:** UTC-based, stored as ISO8601 strings
- **Indexes:** Strategic indexes on frequently queried foreign keys and date fields

### 2.2 Table Definitions

#### 2.2.1 Company Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Company display name |
| `slug` | VARCHAR(100) | UNIQUE, NOT NULL | URL-friendly identifier |
| `domain` | VARCHAR(255) | UNIQUE | Company domain for auto-grouping |
| `settings` | JSON | DEFAULT '{}' | Company-specific settings (vacation policies, holidays) |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Last update timestamp |

**Indexes:**
- `idx_company_slug` ON `company` (`slug`)
- `idx_company_domain` ON `company` (`domain`)

#### 2.2.2 Function Table (Department/Team Functional Area)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `company_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `company(id)` | Parent company |
| `name` | VARCHAR(255) | NOT NULL | Function/department name |
| `code` | VARCHAR(50) | NOT NULL | Short code (e.g., "ENG", "HR", "SALES") |
| `manager_id` | UUID | NULL, FOREIGN KEY REFERENCES `user(id)` | Default manager (can be overridden by team assignments) |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Last update timestamp |
| `deleted_at` | DATETIME | NULL | Soft delete timestamp |

**Indexes:**
- `idx_function_company` ON `function` (`company_id`)
- `idx_function_code` ON `function` (`company_id`, `code`)

#### 2.2.3 Team Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `company_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `company(id)` | Parent company |
| `function_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `function(id)` | Parent function |
| `name` | VARCHAR(255) | NOT NULL | Team display name |
| `code` | VARCHAR(50) | NOT NULL | Short team code |
| `settings` | JSON | DEFAULT '{}' | Team-specific settings |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Last update timestamp |
| `deleted_at` | DATETIME | NULL | Soft delete timestamp |

**Indexes:**
- `idx_team_company` ON `team` (`company_id`)
- `idx_team_function` ON `team` (`function_id`)
- `idx_team_function_code` ON `team` (`function_id`, `code`)

#### 2.2.4 User Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `company_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `company(id)` | Parent company |
| `function_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `function(id)` | Primary function assignment |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User email (login identifier) |
| `password_hash` | VARCHAR(255) | NOT NULL | Argon2id hashed password |
| `first_name` | VARCHAR(100) | NOT NULL | First name |
| `last_name` | VARCHAR(100) | NOT NULL | Last name |
| `role` | ENUM('admin', 'manager', 'user') | NOT NULL, DEFAULT 'user' | User role |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active status |
| `email_verified` | BOOLEAN | NOT NULL, DEFAULT FALSE | Email verification status |
| `last_login_at` | DATETIME | NULL | Last successful login |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Last update timestamp |
| `deleted_at` | DATETIME | NULL | Soft delete timestamp |

**Indexes:**
- `idx_user_email` ON `user` (`email`)
- `idx_user_company` ON `user` (`company_id`)
- `idx_user_function` ON `user` (`function_id`)
- `idx_user_role` ON `user` (`role`)

#### 2.2.5 Team Membership Table (User to Team Many-to-Many)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `user_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | User identifier |
| `team_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `team(id)` | Team identifier |
| `is_primary` | BOOLEAN | NOT NULL, DEFAULT FALSE | Primary team for user |
| `joined_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Membership start date |
| `left_at` | DATETIME | NULL | Membership end date (for historical tracking) |

**Constraints:**
- Unique constraint on `(user_id, team_id)` for active memberships

**Indexes:**
- `idx_team_membership_user` ON `team_membership` (`user_id`)
- `idx_team_membership_team` ON `team_membership` (`team_id`)
- `idx_team_membership_active` ON `team_membership` (`user_id`, `left_at` IS NULL)

#### 2.2.6 Team Manager Assignment Table (Manager to Team Scope Many-to-Many)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `manager_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Manager user |
| `team_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `team(id)` | Managed team |
| `assigned_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Assignment date |
| `assigned_by` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Who made the assignment |

**Constraints:**
- Unique constraint on `(manager_id, team_id)` to prevent duplicate assignments

**Indexes:**
- `idx_manager_assignment_manager` ON `team_manager_assignment` (`manager_id`)
- `idx_manager_assignment_team` ON `team_manager_assignment` (`team_id`)

#### 2.2.7 Vacation Request Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `user_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Request owner |
| `vacation_type` | ENUM('annual', 'sick', 'personal', 'unpaid', 'other') | NOT NULL | Type of leave |
| `start_date` | DATE | NOT NULL | First day of leave |
| `end_date` | DATE | NOT NULL | Last day of leave |
| `total_days` | DECIMAL(4,2) | NOT NULL | Number of leave days |
| `status` | ENUM('draft', 'pending', 'approved', 'rejected', 'cancelled', 'withdrawn') | NOT NULL, DEFAULT 'draft' | Request status |
| `reason` | TEXT | NULL | Optional reason/notes |
| `approver_id` | UUID | NULL, FOREIGN KEY REFERENCES `user(id))` | Who approved/rejected |
| `approved_at` | DATETIME | NULL | Approval timestamp |
| `rejected_reason` | TEXT | NULL | Rejection reason |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Last update timestamp |
| `deleted_at` | DATETIME | NULL | Soft delete timestamp |

**Indexes:**
- `idx_vacation_user` ON `vacation_request` (`user_id`)
- `idx_vacation_status` ON `vacation_request` (`status`)
- `idx_vacation_dates` ON `vacation_request` (`start_date`, `end_date`)
- `idx_vacation_approver` ON `vacation_request` (`approver_id`)
- `idx_vacation_user_status` ON `vacation_request` (`user_id`, `status`)

#### 2.2.8 Audit Log Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `company_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `company(id)` | Company context |
| `actor_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Who performed the action |
| `action` | VARCHAR(100) | NOT NULL | Action type (e.g., 'vacation.approve', 'user.create') |
| `entity_type` | VARCHAR(50) | NOT NULL | Entity being acted upon |
| `entity_id` | UUID | NOT NULL | Entity identifier |
| `old_values` | JSON | NULL | Previous state (for updates) |
| `new_values` | JSON | NULL | New state (for updates) |
| `ip_address` | VARCHAR(45) | NULL | Client IP address |
| `user_agent` | VARCHAR(500) | NULL | Browser user agent |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |

**Indexes:**
- `idx_audit_company` ON `audit_log` (`company_id`)
- `idx_audit_actor` ON `audit_log` (`actor_id`)
- `idx_audit_action` ON `audit_log` (`action`)
- `idx_audit_entity` ON `audit_log` (`entity_type`, `entity_id`)
- `idx_audit_created` ON `audit_log` (`created_at`)

#### 2.2.9 Invite Token Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `token` | VARCHAR(500) | UNIQUE, NOT NULL | Hashed token (store hash, not plain text) |
| `company_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `company(id)` | Target company |
| `function_id` | UUID | NULL, FOREIGN KEY REFERENCES `function(id)` | Pre-assigned function |
| `team_id` | UUID | NULL, FOREIGN KEY REFERENCES `team(id)` | Pre-assigned team |
| `invited_by` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Who sent the invite |
| `role` | ENUM('user', 'manager', 'admin') | NOT NULL, DEFAULT 'user' | Role to assign |
| `email` | VARCHAR(255) | NOT NULL | Target email address |
| `expires_at` | DATETIME | NOT NULL | Token expiration |
| `used_at` | DATETIME | NULL | Token usage timestamp |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |

**Indexes:**
- `idx_invite_token_token` ON `invite_token` (`token`)
- `idx_invite_token_email` ON `invite_token` (`email`)
- `idx_invite_token_expires` ON `invite_token` (`expires_at`)
- `idx_invite_token_status` ON `invite_token` (`expires_at`, `used_at`)

#### 2.2.10 Password Reset Token Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `token` | VARCHAR(500) | UNIQUE, NOT NULL | Hashed token |
| `user_id` | UUID | NOT NULL, FOREIGN KEY REFERENCES `user(id)` | Target user |
| `expires_at` | DATETIME | NOT NULL | Token expiration |
| `used_at` | DATETIME | NULL | Token usage timestamp |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTCNOW | Record creation timestamp |

**Indexes:**
- `idx_password_reset_token` ON `password_reset_token` (`token`)
- `idx_password_reset_user` ON `password_reset_token` (`user_id`)
- `idx_password_reset_expires` ON `password_reset_token` (`expires_at`)

### 2.3 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   company   │       │   function  │       │    team     │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ id (PK)     │◄──────│ id (PK)     │
│ name        │       │ company_id  │       │ company_id  │
│ slug        │       │ name        │       │ function_id │
│ domain      │       │ code        │       │ name        │
└─────────────┘       │ manager_id  │       │ code        │
                      └─────────────┘       └─────────────┘
                             │                    │
                             │                    │
                             │ 1                  │ N
                             ▼                    ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    user     │       │ team_member │       │ team_manager│
├─────────────┤       │ ship        │       │ assignment  │
│ id (PK)     │◄──────│ id (PK)     │       │ id (PK)     │
│ company_id  │       │ user_id (FK)│       │ manager_id  │
│ function_id │       │ team_id (FK)│       │ team_id (FK)│
│ email       │       │ is_primary  │       │ assigned_at │
│ password    │       │ joined_at    │       │ assigned_by │
│ role        │       └─────────────┘       └─────────────┘
└─────────────┘              │
        │                   │
        │ N                  │ N
        ▼                   ▼
┌─────────────────────────────────────────────────────┐
│              vacation_request                       │
├─────────────────────────────────────────────────────┤
│ id (PK)                                             │
│ user_id (FK)                                        │
│ vacation_type                                       │
│ start_date, end_date                                │
│ status                                              │
│ approver_id (FK)                                    │
│ approved_at                                         │
└─────────────────────────────────────────────────────┘
```

---

## 3. RBAC Matrix

### 3.1 Role Definitions

| Role | Scope | Description |
|------|-------|-------------|
| **Admin** | Global (all companies) | Full system access for platform administrators |
| **Manager** | Company + Assigned Teams | Can manage assigned teams and their members |
| **User** | Own Data | Can manage their own vacation requests |

### 3.2 Permission Matrix

| Resource/Action | Admin | Manager | User |
|----------------|-------|---------|------|
| **Auth Endpoints** | | | |
| Login | ✅ | ✅ | ✅ |
| Logout | ✅ | ✅ | ✅ |
| Refresh Token | ✅ | ✅ | ✅ |
| **Users** | | | |
| List all users (company) | ✅ | ✅ (own team only) | ❌ |
| Get user by ID | ✅ | ✅ (own team members) | ✅ (self) |
| Create user | ✅ (via invite) | ❌ | ❌ |
| Update user | ✅ | ✅ (own team members) | ✅ (self) |
| Delete user (soft) | ✅ | ❌ | ❌ |
| **Companies** | | | |
| List companies | ✅ | ❌ | ❌ |
| Get company | ✅ | ✅ (own company) | ✅ (own company) |
| Create company | ✅ | ❌ | ❌ |
| Update company | ✅ | ❌ | ❌ |
| **Functions** | | | |
| List functions | ✅ | ✅ (own company) | ✅ (own company) |
| Get function | ✅ | ✅ (own company) | ✅ (own company) |
| Create function | ✅ | ❌ | ❌ |
| Update function | ✅ | ❌ | ❌ |
| Delete function | ✅ | ❌ | ❌ |
| **Teams** | | | |
| List teams | ✅ | ✅ (own company) | ✅ (own company) |
| Get team | ✅ | ✅ (own company) | ✅ (own company) |
| Create team | ✅ | ❌ | ❌ |
| Update team | ✅ | ❌ | ❌ |
| Delete team | ✅ | ❌ | ❌ |
| **Team Memberships** | | | |
| List team members | ✅ | ✅ (assigned teams) | ✅ (self) |
| Add team member | ✅ | ✅ (assigned teams) | ❌ |
| Remove team member | ✅ | ✅ (assigned teams) | ❌ |
| **Team Manager Assignments** | | | |
| List manager assignments | ✅ | ✅ (own assignments) | ❌ |
| Assign manager | ✅ | ❌ | ❌ |
| Remove manager | ✅ | ❌ | ❌ |
| **Vacation Requests (Own)** | | | |
| List own requests | ✅ | ✅ | ✅ |
| Get own request | ✅ | ✅ | ✅ |
| Create request | ✅ | ✅ | ✅ |
| Update own request (draft only) | ✅ | ✅ | ✅ |
| Cancel/withdraw request | ✅ | ✅ | ✅ |
| **Vacation Requests (Others)** | | | |
| List team requests | ✅ | ✅ (assigned teams) | ❌ |
| Get team request | ✅ | ✅ (assigned teams) | ❌ |
| Approve team request | ✅ | ✅ (assigned teams) | ❌ |
| Reject team request | ✅ | ✅ (assigned teams) | ❌ |
| **Exports** | | | |
| Export company data | ✅ | ❌ | ❌ |
| Export team data | ✅ | ✅ (assigned teams) | ❌ |
| Export own data | ✅ | ✅ | ✅ |
| **Audit Logs** | | | |
| List audit logs | ✅ | ❌ | ❌ |
| View audit log entry | ✅ | ❌ | ❌ |

### 3.3 RBAC Implementation Strategy

#### 3.3.1 Permission Check Decorator

```python
from functools import wraps
from fastapi import HTTPException, status

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            if not has_permission(current_user, permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: str) -> bool:
    """Check if user has specific permission based on role and scope."""
```

#### 3.3.2 Query Filtering for Company Isolation

```python
def apply_company_filter(query, user):
    """Ensure users can only access their own company's data."""
    if user.role == 'admin':
        return query  # Admin sees all companies
    
    return query.filter(Model.company_id == user.company_id)

def apply_team_scope(query, user, model):
    """Apply team-based scope for managers."""
    if user.role == 'admin':
        return query
    
    if user.role == 'manager':
        # Manager sees data for teams they manage
        managed_teams = get_managed_team_ids(user.id)
        if hasattr(model, 'team_id'):
            return query.filter(model.team_id.in_(managed_teams))
        elif hasattr(model, 'user_id'):
            team_members = get_team_member_user_ids(managed_teams)
            return query.filter(model.user_id.in_(team_members))
    
    # Regular users only see their own data
    return query.filter(model.user_id == user.id)
```

---

## 4. API Surface Proposal

### 4.1 Authentication Endpoints

#### 4.1.1 POST /auth/login

**Purpose:** Authenticate user and return tokens

**Request Schema:**
```python
class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address", example="user@example.com")
    password: str = Field(..., description="User password", example="SecurePassword123!")
```

**Response Schema:**
```python
class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_token: str = Field(..., description="Refresh token for session renewal")
```

**Auth Required:** No (public endpoint)

**Rate Limit:** 5 requests per minute per IP

#### 4.1.2 POST /auth/logout

**Purpose:** Invalidate refresh token and end session

**Request Schema:**
```python
class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to invalidate")
```

**Response Schema:**
```python
class MessageResponse(BaseModel):
    message: str = Field(default="Successfully logged out")
```

**Auth Required:** Yes (valid access token)

#### 4.1.3 POST /auth/refresh

**Purpose:** Refresh access token using refresh token

**Request Schema:**
```python
class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")
```

**Response Schema:**
```python
class RefreshResponse(BaseModel):
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="Access token expiry in seconds")
```

**Auth Required:** No (refresh token validation)

#### 4.1.4 POST /auth/invite/accept

**Purpose:** Accept invitation and set password

**Request Schema:**
```python
class AcceptInviteRequest(BaseModel):
    token: str = Field(..., description="Invite token")
    password: str = Field(..., min_length=12, description="New password")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
```

**Response Schema:**
```python
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: "UserResponse schema"
```

**Auth Required:** No (token validation)

#### 4.1.5 POST /auth/password/reset/request

**Purpose:** Request password reset email

**Request Schema:**
```python
class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="User email address")
```

**Response Schema:**
```python
class MessageResponse(BaseModel):
    message: str = "If an account exists, a password reset email has been sent"
```

**Auth Required:** No

**Rate Limit:** 3 requests per hour per email

#### 4.1.6 POST /auth/password/reset/confirm

**Purpose:** Reset password with valid reset token

**Request Schema:**
```python
class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, description="New password")
```

**Response Schema:**
```python
class MessageResponse(BaseModel):
    message: str = "Password has been reset successfully"
```

**Auth Required:** No (token validation)

#### 4.1.7 POST /auth/password/change

**Purpose:** Change password for authenticated user

**Request Schema:**
```python
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New password")
```

**Response Schema:**
```python
class MessageResponse(BaseModel):
    message: str = "Password has been changed successfully"
```

**Auth Required:** Yes (valid access token)

### 4.2 User Endpoints

#### 4.2.1 GET /users/me

**Purpose:** Get current authenticated user

**Response Schema:**
```python
class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    company_id: UUID
    function_id: UUID
    is_active: bool
    email_verified: bool
    created_at: datetime
```

**Auth Required:** Yes

#### 4.2.2 GET /users

**Purpose:** List users (with filtering)

**Query Parameters:**
- `team_id`: Filter by team
- `function_id`: Filter by function
- `role`: Filter by role
- `is_active`: Filter by active status
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

**Response Schema:**
```python
class PaginatedResponse(BaseModel):
    data: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Auth Required:** Yes (role-dependent visibility)

#### 4.2.3 GET /users/{user_id}

**Purpose:** Get specific user by ID

**Response Schema:** UserResponse

**Auth Required:** Yes (role-dependent visibility)

#### 4.2.4 PUT /users/{user_id}

**Purpose:** Update user profile

**Request Schema:**
```python
class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    function_id: Optional[UUID] = None
```

**Response Schema:** UserResponse

**Auth Required:** Yes (own profile or manager/admin)

### 4.3 Company/Function/Team Endpoints

#### 4.3.1 GET /companies/{company_id}

**Purpose:** Get company details

**Response Schema:**
```python
class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    domain: Optional[str]
    settings: dict
    created_at: datetime
```

**Auth Required:** Yes (own company)

#### 4.3.2 GET /companies/{company_id}/functions

**Purpose:** List functions in company

**Response Schema:** list[FunctionResponse]

**Auth Required:** Yes (own company)

#### 4.3.3 GET /companies/{company_id}/teams

**Purpose:** List teams in company

**Query Parameters:**
- `function_id`: Filter by function
- `include_members`: Include member count (default: false)

**Response Schema:** list[TeamResponse]

**Auth Required:** Yes (own company)

#### 4.3.4 GET /teams/{team_id}

**Purpose:** Get team details with members

**Response Schema:**
```python
class TeamDetailResponse(BaseModel):
    id: UUID
    name: str
    code: str
    function_id: UUID
    members: list[TeamMemberResponse]
    managers: list[ManagerResponse]
```

**Auth Required:** Yes (own company)

### 4.4 Vacation Request Endpoints

#### 4.4.1 GET /vacations

**Purpose:** List vacation requests

**Query Parameters:**
- `status`: Filter by status
- `start_date`: Filter by start date range (from)
- `end_date`: Filter by start date range (to)
- `user_id`: Filter by user (manager/admin only)
- `team_id`: Filter by team (manager only)
- `page`, `page_size`: Pagination

**Response Schema:** PaginatedResponse[VacationRequestResponse]

**Auth Required:** Yes (scoped by role)

#### 4.4.2 POST /vacations

**Purpose:** Create new vacation request

**Request Schema:**
```python
class VacationCreateRequest(BaseModel):
    vacation_type: str = Field(..., example="annual")
    start_date: date = Field(..., example="2024-07-01")
    end_date: date = Field(..., example="2024-07-05")
    reason: Optional[str] = Field(None, max_length=500)
```

**Response Schema:** VacationRequestResponse (status: 'draft' or 'pending')

**Auth Required:** Yes (own data)

#### 4.4.3 GET /vacations/{vacation_id}

**Purpose:** Get vacation request details

**Response Schema:**
```python
class VacationRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    vacation_type: str
    start_date: date
    end_date: date
    total_days: Decimal
    status: str
    reason: Optional[str]
    approver_id: Optional[UUID]
    approved_at: Optional[datetime]
    rejected_reason: Optional[str]
    created_at: datetime
```

**Auth Required:** Yes (scoped)

#### 4.4.4 PUT /vacations/{vacation_id}

**Purpose:** Update vacation request (draft only)

**Request Schema:** VacationCreateRequest

**Auth Required:** Yes (owner, draft status)

#### 4.4.5 POST /vacations/{vacation_id}/submit

**Purpose:** Submit draft request for approval

**Auth Required:** Yes (owner, draft status)

#### 4.4.6 POST /vacations/{vacation_id}/approve

**Purpose:** Approve vacation request

**Request Schema:**
```python
class ApproveRequest(BaseModel):
    comment: Optional[str] = None
```

**Response Schema:** VacationRequestResponse (status: 'approved')

**Auth Required:** Yes (manager of team, pending status)

#### 4.4.7 POST /vacations/{vacation_id}/reject

**Purpose:** Reject vacation request

**Request Schema:**
```python
class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
```

**Response Schema:** VacationRequestResponse (status: 'rejected')

**Auth Required:** Yes (manager of team, pending status)

#### 4.4.8 POST /vacations/{vacation_id}/cancel

**Purpose:** Cancel/withdraw vacation request

**Auth Required:** Yes (owner, or admin/manager)

#### 4.4.9 GET /vacations/balance

**Purpose:** Get user's vacation balance

**Response Schema:**
```python
class VacationBalanceResponse(BaseModel):
    total_annual_days: int
    used_annual_days: int
    remaining_annual_days: int
    carry_over_days: int
    balances_by_type: dict
```

**Auth Required:** Yes (own data)

### 4.5 Export Endpoints

#### 4.5.1 GET /exports/vacations/csv

**Purpose:** Export vacation data as CSV

**Query Parameters:**
- `start_date`: Start of date range
- `end_date`: End of date range
- `team_id`: Filter by team (manager)
- `user_id`: Filter by user (admin)

**Response:** CSV file download

**Content-Type:** text/csv

**Auth Required:** Yes (role-dependent scope)

#### 4.5.2 GET /exports/vacations/xlsx

**Purpose:** Export vacation data as XLSX

**Query Parameters:** Same as CSV

**Response:** XLSX file download

**Content-Type:** application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

**Auth Required:** Yes (role-dependent scope)

### 4.6 Audit Log Endpoints

#### 4.6.1 GET /audit-logs

**Purpose:** List audit logs (admin only)

**Query Parameters:**
- `company_id`: Filter by company
- `actor_id`: Filter by actor
- `action`: Filter by action type
- `entity_type`: Filter by entity type
- `start_date`: Filter by date range
- `end_date`: Filter by date range
- `page`, `page_size`: Pagination

**Response Schema:** PaginatedResponse[AuditLogResponse]

**Auth Required:** Yes (admin only)

#### 4.6.2 GET /audit-logs/{log_id}

**Purpose:** Get audit log entry details

**Response Schema:**
```python
class AuditLogResponse(BaseModel):
    id: UUID
    company_id: UUID
    actor_id: UUID
    actor_email: str
    action: str
    entity_type: str
    entity_id: UUID
    old_values: Optional[dict]
    new_values: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
```

**Auth Required:** Yes (admin only)

### 4.7 Invite Management Endpoints (Admin)

#### 4.7.1 POST /admin/invites

**Purpose:** Create invite token

**Request Schema:**
```python
class CreateInviteRequest(BaseModel):
    email: str = Field(..., description="Email to invite")
    role: str = Field(default="user", description="Role to assign")
    function_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
```

**Response Schema:**
```python
class InviteResponse(BaseModel):
    id: UUID
    token: str = Field(..., description="Shareable invite token")
    email: str
    role: str
    expires_at: datetime
    created_at: datetime
```

**Auth Required:** Yes (admin only)

#### 4.7.2 GET /admin/invites

**Purpose:** List pending invites

**Response Schema:** list[InviteListItem]

**Auth Required:** Yes (admin only)

#### 4.7.3 DELETE /admin/invites/{invite_id}

**Purpose:** Revoke invite token

**Auth Required:** Yes (admin only)

---

## 5. Security Design Decisions

### 5.1 Password Hashing

**Algorithm:** Argon2id (winner of Password Hashing Competition)

**Parameters for Raspberry Pi 5 (arm64):**

```python
# Recommended Argon2id parameters for Pi 5
# Balancing security with reasonable login times on limited hardware

HASH_PARAMS = {
    'time_cost': 2,          # Number of iterations (memory hardness)
    'memory_cost': 65536,    # 64 MB (memory hardness)
    'parallelism': 4,        # Degree of parallelism (match CPU cores)
    'hash_len': 32,          # Length of the hash in bytes
    'salt_len': 16           # Length of the salt in bytes
}
```

**Rationale:**
- `time_cost=2`: Fast enough for responsive login while providing iterations
- `memory_cost=65536`: 64 MB memory requirement makes GPU/ASIC attacks impractical
- `parallelism=4`: Matches Pi 5's 4 cores for optimal performance
- Target hash time: ~200-500ms on Pi 5

**Implementation:**
```python
import argon2

password_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

# Hash password
hash = password_hasher.hash(password)

# Verify password
password_hasher.verify(hash, password)
```

### 5.2 Invite Token Strategy

**Format:** Opaque UUID v4 (not JWT)

**Rationale for Opaque Token vs JWT:**

| Aspect | Opaque Token | JWT |
|--------|-------------|-----|
| One-time use | Easy to enforce (mark as used) | Harder to enforce (need token blocklist) |
| Storage | Database required | Stateless |
| Revocation | Immediate (update DB) | Must wait for expiry or use blocklist |
| DB load | Additional query | None |
| Token size | Compact (UUID) | Larger (claims + signature) |

**Implementation:**
```python
import secrets
import hashlib

def create_invite_token():
    """Generate secure invite token."""
    raw_token = secrets.token_urlsafe(32)  # ~256 bits of entropy
    token_hash = hash_token(raw_token)
    
    # Store hash in database
    invite = InviteToken(
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=7),
        # ... other fields
    )
    
    return raw_token  # Return raw token to share (not stored)

def hash_token(token: str) -> str:
    """Hash token for storage using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()
```

**Expiry:** 7 days (configurable)

**One-time Use:** Token marked as `used_at` after acceptance

### 5.3 Session Strategy

**Approach:** JWT Access Token + Secure HTTP-Only Refresh Token Cookie

**Justification:**

| Factor | JWT (localStorage) | Session Cookies | JWT + Cookie Hybrid |
|--------|-------------------|-----------------|---------------------|
| CSRF Protection | Not needed | Required | Not needed |
| XSS Resilience | Vulnerable | Protected | Protected |
| Mobile/API Friendly | ✅ | ⚠️ Limited | ✅ |
| Token Revocation | Hard (delay) | Immediate | Immediate (refresh) |
| Stateless Scaling | ✅ | ❌ Requires storage | ✅ (mostly) |

**Chosen Hybrid Approach:**
- Access Token: JWT in Authorization header (Bearer scheme)
- Refresh Token: Secure HTTP-Only cookie, stored server-side in SQLite

**Token Lifetimes:**

| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| Access Token | 15 minutes | Memory only | API authentication |
| Refresh Token | 7 days | HTTP-Only Cookie + DB | Session renewal |
| Remember Me Refresh Token | 30 days | HTTP-Only Cookie + DB + fingerprint | Extended session |

**Implementation:**
```python
# Access Token (JWT)
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Refresh Token
REFRESH_TOKEN_EXPIRE_DAYS = 7
REMEMBER_ME_TOKEN_EXPIRE_DAYS = 30

# Token storage in database
class RefreshToken(BaseModel):
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    last_used_at: datetime
    user_agent: Optional[str]
    ip_address: Optional[str]
    is_remember_me: bool = False
```

### 5.4 CSRF Strategy

**Approach:** Not required with JWT Bearer tokens in Authorization header

**Rationale:**
- Access tokens are sent via `Authorization: Bearer <token>` header
- Cookies are only used for refresh tokens (HTTP-Only)
- Refresh tokens are validated against database and bound to user fingerprint

**Additional Cookie Security:**
```python
Set-Cookie: refresh_token=...; 
    HttpOnly;      # JavaScript cannot access
    Secure;        # HTTPS only
    SameSite=Strict;  # CSRF protection
    Path=/auth/refresh  # Limited to refresh endpoint
```

### 5.5 Rate Limiting

**Approach:** Application-level middleware with SQLite-based tracking

**Rationale:**
- Caddy can provide basic limits but lacks granular per-endpoint control
- App-level allows for dynamic limits and user-aware throttling
- SQLite supports efficient counter storage with file-based persistence

**Rate Limits:**

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| /auth/login | 5 | per minute per IP |
| /auth/password/reset/request | 3 | per hour per email |
| /auth/password/reset/confirm | 10 | per hour per IP |
| /auth/refresh | 30 | per minute per user |
| /api/vacations (write) | 60 | per hour per user |
| /api/vacations (read) | 200 | per hour per user |
| /api/exports | 10 | per day per user |
| Default API | 1000 | per hour per user |

**Implementation:**
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Middleware-based rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Check rate limit from SQLite-based storage
    key = get_rate_limit_key(request)
    remaining = await check_rate_limit(key)
    
    request.state.rate_limit_remaining = remaining
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
```

### 5.6 Company Isolation

**Strategy:** Query-level filtering with company context enforcement

**Principles:**
1. Every request is scoped to a company context
2. Company ID is embedded in user session
3. All database queries include company_id filter
4. Cross-company queries raise security exceptions

**Implementation:**
```python
class CompanyIsolationMixin:
    """Mixin to enforce company isolation on all queries."""
    
    @classmethod
    def get_query_with_company_filter(cls, session, company_id: UUID):
        """Ensure all queries are filtered by company."""
        return cls.query.filter(cls.company_id == company_id)
    
    @classmethod
    async def get_by_id_safe(cls, session, id: UUID, user: User):
        """Get by ID with company isolation check."""
        obj = await session.get(cls, id)
        
        if not obj:
            raise NotFoundError()
        
        if obj.company_id != user.company_id:
            raise ForbiddenError("Access to this resource is not allowed")
        
        return obj

# Usage in endpoints
@router.get("/vacations/{vacation_id}")
async def get_vacation(
    vacation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # Company isolation enforced
    vacation = await Vacation.get_by_id_safe(
        session, 
        vacation_id, 
        current_user
    )
    return vacation
```

**Additional Measures:**
- UUIDs prevent ID enumeration attacks
- Audit logging of all access attempts
- Regular security reviews of query patterns

---

## 6. Test Plan

### 6.1 Test Framework

**Recommended:** pytest with async support

**Dependencies:**
```
pytest==8.3.0+
pytest-asyncio==0.23.0+
pytest-cov==4.1.0+
httpx==0.26.0+  # Async HTTP client for testing
factory-boy==3.3.0+  # Test data factories
faker==20.0+  # Fake data generation
```

### 6.2 Unit Tests

#### 6.2.1 Authentication Module Tests

**Test Coverage:**

| Test Case | Description |
|-----------|-------------|
| `test_password_hash_verification` | Hash verification with correct password |
| `test_password_hash_rejection` | Hash verification with wrong password |
| `test_password_hash_algorithmic_properties` | Correct algorithm, salt uniqueness |
| `test_invalid_password_too_short` | Password policy enforcement |
| `test_invalid_password_no_uppercase` | Password policy enforcement |
| `test_invalid_password_no_number` | Password policy enforcement |
| `test_generate_secure_token` | Token generation entropy |
| `test_token_hashing` | Token hashing produces different output |

**Example:**
```python
import pytest
from app.core.security import password_hasher

class TestPasswordHashing:
    def test_password_hash_verification(self):
        password = "SecurePassword123!"
        hash = password_hasher.hash(password)
        
        # Should verify correctly
        assert password_hasher.verify(hash, password) is True
    
    def test_password_hash_rejection(self):
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hash = password_hasher.hash(password)
        
        # Should reject wrong password
        assert password_hasher.verify(hash, wrong_password) is False
```

#### 6.2.2 RBAC Permission Tests

**Test Coverage:**

| Test Case | Description |
|-----------|-------------|
| `test_admin_has_all_permissions` | Admin role has full access |
| `test_manager_team_scope` | Manager can only access assigned teams |
| `test_user_own_data_access` | User can only access own data |
| `test_unauthorized_access_denied` | Access without token is rejected |
| `test_invalid_token_rejected` | Invalid token is rejected |
| `test_expired_token_rejected` | Expired token is rejected |

#### 6.2.3 Vacation Business Logic Tests

**Test Coverage:**

| Test Case | Description |
|-----------|-------------|
| `test_calculate_vacation_days` | Weekend/holiday exclusion |
| `test_partial_day_vacation` | Single day request calculation |
| `test_date_range_validation` | Start date before end date |
| `test_overlapping_requests_prevented` | Cannot double-book dates |
| `test_status_transition_draft_to_pending` | Valid status change |
| `test_status_transition_rejection` | Invalid status change blocked |
| `test_approve_requires_manager_role` | Authorization check |

#### 6.2.4 Company Isolation Tests

**Test Coverage:**

| Test Case | Description |
|-----------|-------------|
| `test_cannot_access_other_company_users` | Cross-company user access blocked |
| `test_cannot_access_other_company_vacations` | Cross-company vacation access blocked |
| `test_cannot_list_other_company_data` | Cross-company listing filtered |
| `test_admin_can_access_all_companies` | Admin bypass works correctly |

### 6.3 Integration Tests

#### 6.3.1 API Flow Tests

**Test Categories:**

| Category | Description |
|----------|-------------|
| **Auth Flows** | Complete login, logout, refresh cycles |
| **User CRUD** | User creation, reading, updating, deletion |
| **Vacation Lifecycle** | Create → Submit → Approve → Cancel |
| **Invite Flow** | Create invite → Accept → Login |
| **Password Reset** | Request → Email → Reset → Login |
| **Export Flow** | Request CSV/XLSX download |

**Example (Vacation Lifecycle):**
```python
@pytest.mark.asyncio
async def test_vacation_lifecycle(client, user_factory, team_factory):
    # Setup
    user = await user_factory.create(role="user")
    team = await team_factory.create()
    await team_factory.add_member(team.id, user.id)
    
    # Create vacation request
    response = await client.post(
        "/api/v1/vacations",
        json={
            "vacation_type": "annual",
            "start_date": "2024-07-01",
            "end_date": "2024-07-05",
            "reason": "Summer vacation"
        },
        headers={"Authorization": f"Bearer {user.access_token}"}
    )
    assert response.status_code == 201
    vacation_id = response.json()["id"]
    
    # Submit for approval
    response = await client.post(
        f"/api/v1/vacations/{vacation_id}/submit",
        headers={"Authorization": f"Bearer {user.access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    
    # Approve as manager
    manager = await user_factory.create(role="manager")
    await team_factory.add_manager(team.id, manager.id)
    
    response = await client.post(
        f"/api/v1/vacations/{vacation_id}/approve",
        json={"comment": "Have a great vacation!"},
        headers={"Authorization": f"Bearer {manager.access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
```

#### 6.3.2 RBAC Enforcement Tests

**Test Scenarios:**

| Scenario | Expected Result |
|----------|----------------|
| User tries to approve vacation | 403 Forbidden |
| Manager tries to approve other team's vacation | 403 Forbidden |
| Admin accesses any company's data | 200 OK |
| User lists other company users | 403 Forbidden |
| Manager lists unassigned team's members | 403 Forbidden |

#### 6.3.3 Export Functionality Tests

**Test Cases:**

| Test Case | Description |
|-----------|-------------|
| `test_export_csv_format` | CSV output has correct headers |
| `test_export_xlsx_format` | XLSX output is valid workbook |
| `test_export_filters_respected` | Date/team filters applied |
| `test_export_scope_enforced` | User can only export scoped data |
| `test_export_large_dataset` | Handles pagination correctly |

### 6.4 Test Data Strategy

#### 6.4.1 Fixtures and Factories

**Factory Structure:**
```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

class CompanyFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Company
    
    name = factory.Faker("company")
    slug = factory.Faker("uuid4")
    domain = factory.Faker("domain_name")

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
    
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password_hash = factory.Lambda(lambda: password_hasher.hash("TestPassword123!"))
    role = "user"
    is_active = True

class VacationRequestFactory(SQLAlchemyModelFactory):
    class Meta:
        model = VacationRequest
    
    vacation_type = "annual"
    start_date = factory.Faker("date_this_year")
    end_date = factory.Lambda(lambda o: o.start_date + timedelta(days=5))
    status = "draft"
```

**pytest Fixtures:**
```python
# tests/conftest.py
import pytest
from app.db.session import get_db, engine
from app.db.base import Base

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a clean database session for each test."""
    # Create all tables
    Base.metadata.create_all(db_engine)
    
    session = get_db()
    yield session
    
    # Rollback and close
    session.rollback()
    session.close()

@pytest.fixture
def client(db_session):
    """Create test client with dependency overrides."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
```

### 6.5 CI/CD Compatibility

#### 6.5.1 Test Execution Strategy

**Pipeline Stages:**

```yaml
# GitHub Actions Example
stages:
  - name: Unit Tests
    run: pytest tests/unit/ -v --cov=app --cov-report=xml
    
  - name: Integration Tests
    run: pytest tests/integration/ -v
    env:
      TEST_DATABASE_URL: "sqlite:///test_vacations.db"
      
  - name: Security Tests
    run: |
      pytest tests/security/ -v
      bandit -r app/
      safety check -r requirements.txt
      
  - name: Linting & Formatting
    run: |
      ruff check app/
      black --check app/
      mypy app/
```

#### 6.5.2 Test Database Management

**SQLite Test Strategy:**
- Each test run creates a fresh test database
- Tests use in-memory or temporary file SQLite databases
- Database is reset between test sessions
- Migrations are applied automatically before tests

```python
# tests/conftest.py - Database setup
@pytest.fixture(scope="session")
def test_db():
    """Create test database and apply migrations."""
    test_db_path = "/tmp/test_vacations.db"
    
    # Remove existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Create database and apply migrations
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    yield test_db_path
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
```

#### 6.5.3 Coverage Requirements

| Metric | Target | Enforcement |
|--------|--------|-------------|
| Unit Test Coverage | 80% | Pipeline fails if below |
| Integration Test Coverage | 60% | Pipeline fails if below |
| Auth Module Coverage | 95% | Critical module requirement |
| RBAC Module Coverage | 90% | Critical module requirement |

---

## Appendix A: Raspberry Pi 5 Considerations

### Resource Constraints

| Resource | Constraint | Mitigation |
|----------|------------|------------|
| CPU | 4 cores, lower single-core performance | Conservative Argon2 parameters, efficient algorithms |
| RAM | 4-8 GB typical | SQLite memory-mapped files, connection pooling |
| Storage | SD card or SSD | WAL mode for performance, regular backups |
| Network | 1 Gbps Ethernet or WiFi | Compression, efficient API responses |

### Recommended Configuration

```python
# Production settings for Raspberry Pi 5

# Database
SQLALCHEMY_DATABASE_URL = "sqlite:///vacations.db"
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "check_same_thread": False,  # Required for SQLite
    },
    "pool_size": 10,  # Conservative for Pi 5 RAM
    "max_overflow": 5,
}

# Redis (optional, for caching/sessions)
# Note: Redis not required, using SQLite for all storage
# If needed, use redis-server with limited maxmemory

# Rate Limiting
RATE_LIMIT_STORAGE_URL = "sqlite:///ratelimits.db"

# Logging
LOG_LEVEL = "INFO"  # Reduce debug overhead
```

---

## Appendix B: Production Readiness Checklist

### Security Checklist

- [ ] TLS certificates from Let's Encrypt via Caddy
- [ ] Strong password policy enforced (12+ chars, complexity)
- [ ] Argon2id password hashing configured
- [ ] JWT tokens with short expiration (15 min)
- [ ] Secure refresh token cookies (HttpOnly, Secure, SameSite)
- [ ] Rate limiting on all auth endpoints
- [ ] Company isolation verified
- [ ] Audit logging enabled
- [ ] Input validation on all endpoints
- [ ] CORS configured appropriately
- [ ] Security headers (HSTS, X-Frame-Options, etc.)

### Operational Checklist

- [ ] Database backups configured (daily)
- [ ] Log rotation configured
- [ ] Health check endpoint (/health)
- [ ] Metrics endpoint (/metrics) for monitoring
- [ ] Error tracking configured (Sentry or similar)
- [ ] Application monitoring (uptime checks)
- [ ] Rollback strategy documented
- [ ] Migration strategy tested
- [ ] Performance testing completed
- [ ] Load testing at expected scale

---

*Document Version: 1.0*  
*Last Updated: 2026-02-03*  
*Status: Phase 0 - Architecture & Planning Complete*
