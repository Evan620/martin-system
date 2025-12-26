# Role-Based Access Control (RBAC) - Implementation Checklist

## Overview
This document provides a comprehensive checklist for implementing role-based access control across the ECOWAS Summit TWG Support System. Use this during frontend development to ensure proper access restrictions.

---

## Three User Roles

| Role | Access Level | Primary Interface |
|------|--------------|-------------------|
| **Admin** | Full system access (all TWGs) | Portal |
| **Facilitator** | Single TWG access (assigned TWG only) | Portal |
| **Member** | Read-only or email-only | Email (Portal optional) |

**Detailed Guides**:
- [Admin Role Guide](./RBAC_ADMIN_ROLE.md)
- [Facilitator Role Guide](./RBAC_FACILITATOR_ROLE.md)
- [Member Role Guide](./RBAC_MEMBER_ROLE.md)

---

## Quick Reference: Permissions Matrix

### Feature Access by Role

| Feature | Admin | Facilitator | Member |
|---------|:-----:|:-----------:|:------:|
| **TWG Access** |
| View all TWGs | ✅ | ❌ | ❌ |
| View assigned TWG | ✅ | ✅ | ✅ (read-only) |
| Switch between TWGs | ✅ | ❌ | ❌ |
| **Meetings** |
| Schedule meetings | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| View meetings | ✅ (all) | ✅ (their TWG) | ✅ (their TWG, read-only) |
| Edit/cancel meetings | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| **Documents** |
| Upload documents | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| Download documents | ✅ | ✅ | ✅ |
| Delete documents | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| **Projects** |
| View all projects | ✅ | ❌ | ❌ |
| View TWG projects | ✅ | ✅ (their TWG) | ❌ |
| Add/edit projects | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| **Action Items** |
| Create action items | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| View action items | ✅ (all) | ✅ (their TWG) | ✅ (assigned to them) |
| Update status | ✅ (any TWG) | ✅ (their TWG) | ❌ |
| **AI Agents** |
| Chat with Supervisor | ✅ | ❌ | ❌ |
| Chat with TWG agents | ✅ (all) | ✅ (their TWG) | ❌ |
| View agent logs | ✅ | ❌ | ❌ |
| **User Management** |
| Create/edit users | ✅ | ❌ | ❌ |
| Assign roles | ✅ | ❌ | ❌ |
| View user list | ✅ | ❌ | ❌ |
| **System** |
| System settings | ✅ | ❌ | ❌ |
| Edit templates | ✅ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ❌ |

---

## Frontend Implementation Checklist

### 1. Authentication & Authorization

#### Login & Session
- [ ] Implement login page with email/password
- [ ] Store JWT token securely (httpOnly cookie or secure localStorage)
- [ ] Decode JWT to extract user role and TWG assignment
- [ ] Implement session timeout (auto-logout after inactivity)
- [ ] Implement logout functionality (clear token)

#### User Context
```tsx
// Create user context to store role info
interface UserContext {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'facilitator' | 'member';
  assignedTWGId?: number;  // For facilitators and members
  token: string;
}
```

- [ ] Create `UserContext` provider
- [ ] Fetch user info on login: `GET /api/users/me`
- [ ] Store user role and TWG assignment in context
- [ ] Make user context available throughout app

---

### 2. Route Protection

#### Private Routes
```tsx
<PrivateRoute 
  path="/dashboard" 
  component={Dashboard}
  requiredRole={['admin', 'facilitator']}
/>
```

- [ ] Create `PrivateRoute` component
- [ ] Check if user is authenticated (has valid token)
- [ ] Redirect to login if not authenticated
- [ ] Check if user has required role
- [ ] Show 403 error if role doesn't match

#### Role-Specific Routes

**Admin-Only Routes**:
- [ ] `/admin/overview` - Summit overview dashboard
- [ ] `/admin/users` - User management
- [ ] `/admin/settings` - System settings
- [ ] `/admin/audit-logs` - Audit logs
- [ ] `/deal-pipeline` - Global deal pipeline

**Facilitator Routes** (with TWG validation):
- [ ] `/dashboard` - TWG-specific dashboard
- [ ] `/meetings` - TWG meetings
- [ ] `/documents` - TWG documents
- [ ] `/projects` - TWG projects
- [ ] `/action-items` - TWG action items
- [ ] `/agent` - TWG AI agent chat

**Member Routes** (read-only):
- [ ] `/member/dashboard` - Read-only dashboard
- [ ] `/member/meetings` - Read-only meetings
- [ ] `/member/documents` - Read-only documents
- [ ] `/member/action-items` - Assigned tasks (read-only)

#### TWG Access Validation (Facilitators & Members)
```tsx
// Validate user has access to specific TWG
const validateTWGAccess = (userTWGId, requestedTWGId) => {
  if (user.role === 'admin') return true;
  return userTWGId === requestedTWGId;
};
```

- [ ] Implement TWG access validation
- [ ] Check on every TWG-specific route
- [ ] Show 403 error if user tries to access another TWG

---

### 3. Navigation Menu (Role-Based)

#### Admin Navigation
- [ ] Show "Summit Overview" link
- [ ] Show dropdown with all 6 TWGs
- [ ] Show "User Management" link
- [ ] Show "System Settings" link
- [ ] Show "Global Deal Pipeline" link
- [ ] Show "Supervisor Agent" link

#### Facilitator Navigation
- [ ] Show "My TWG Dashboard" link
- [ ] Show TWG-specific sections (Meetings, Documents, Projects, etc.)
- [ ] **Hide** other TWGs
- [ ] **Hide** user management
- [ ] **Hide** system settings
- [ ] Show their TWG agent link

#### Member Navigation (if portal access)
- [ ] Show "Dashboard" link
- [ ] Show "Meetings" (read-only)
- [ ] Show "Documents" (read-only)
- [ ] Show "My Tasks" (read-only)
- [ ] **Hide** all editing/management features

#### Implementation
```tsx
const Navigation = () => {
  const { user } = useUser();
  
  return (
    <nav>
      {user.role === 'admin' && <AdminNav />}
      {user.role === 'facilitator' && <FacilitatorNav />}
      {user.role === 'member' && <MemberNav />}
    </nav>
  );
};
```

- [ ] Create role-specific navigation components
- [ ] Conditionally render based on user role
- [ ] Test navigation for each role

---

### 4. Dashboard (Role-Based Views)

#### Admin Dashboard
- [ ] Show status cards for ALL 6 TWGs
- [ ] Show global calendar (all meetings)
- [ ] Show deal pipeline overview (all projects)
- [ ] Show system alerts
- [ ] Allow drilling down into any TWG

#### Facilitator Dashboard
- [ ] Show ONLY assigned TWG information
- [ ] Show TWG header with leads and stats
- [ ] Show upcoming meetings for their TWG
- [ ] Show pending approvals (AI drafts)
- [ ] Show recent activity for their TWG

#### Member Dashboard (if portal access)
- [ ] Show upcoming meetings (read-only)
- [ ] Show recent documents (read-only)
- [ ] Show assigned action items (read-only)
- [ ] **No** editing capabilities

---

### 5. Component-Level Access Control

#### Conditional Rendering
```tsx
// Show edit button only for admin and facilitator
{(user.role === 'admin' || user.role === 'facilitator') && (
  <EditButton onClick={handleEdit} />
)}

// Show delete button only for admin
{user.role === 'admin' && (
  <DeleteButton onClick={handleDelete} />
)}

// Read-only mode for members
{user.role === 'member' && (
  <ReadOnlyView />
)}
```

- [ ] Implement conditional rendering for action buttons
- [ ] Hide edit/delete buttons for members
- [ ] Hide admin-only features from facilitators
- [ ] Show read-only views for members

#### Button States
- [ ] Disable buttons for unauthorized actions
- [ ] Show tooltips explaining why button is disabled
- [ ] Use visual indicators (grayed out, locked icon)

---

### 6. API Call Authorization

#### Include Auth Token
```tsx
const fetchData = async () => {
  const response = await fetch('/api/twgs/1/meetings', {
    headers: {
      'Authorization': `Bearer ${user.token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (response.status === 403) {
    // Handle unauthorized access
    showError('You do not have permission to access this resource');
  }
};
```

- [ ] Include JWT token in all API requests
- [ ] Handle 401 Unauthorized (redirect to login)
- [ ] Handle 403 Forbidden (show error message)
- [ ] Implement error handling for access denied

#### Method Restrictions
- [ ] Members can only use GET requests
- [ ] Block POST/PUT/DELETE for members on frontend
- [ ] Backend will enforce, but frontend should prevent attempts

---

### 7. Data Filtering (Frontend)

#### TWG-Scoped Data
```tsx
// Facilitators: Filter data to their TWG only
const filteredMeetings = meetings.filter(
  meeting => meeting.twg_id === user.assignedTWGId
);

// Admins: Show all data
const displayMeetings = user.role === 'admin' 
  ? allMeetings 
  : filteredMeetings;
```

- [ ] Filter TWG data for facilitators
- [ ] Show all data for admins
- [ ] Show only shared data for members

#### Search & Filters
- [ ] Scope search results by user role
- [ ] Facilitators: Search only their TWG
- [ ] Admins: Search across all TWGs
- [ ] Members: Search only shared documents

---

### 8. Form Validation (Role-Based)

#### Meeting Scheduling
- [ ] Admin: Can select any TWG
- [ ] Facilitator: Auto-fill with their TWG (no selection)
- [ ] Member: No access to form

#### Document Upload
- [ ] Admin: Can select any TWG
- [ ] Facilitator: Auto-tag with their TWG
- [ ] Member: No upload capability

#### User Creation (Admin-Only)
- [ ] Show form only to admins
- [ ] Allow role assignment
- [ ] Allow TWG assignment for facilitators

---

### 9. AI Agent Chat (Role-Based)

#### Agent Access
```tsx
// Determine which agent user can chat with
const getAvailableAgent = (user) => {
  if (user.role === 'admin') {
    return 'supervisor'; // or any TWG agent
  } else if (user.role === 'facilitator') {
    return user.assignedTWG.agentType; // e.g., 'energy'
  } else {
    return null; // Members can't chat
  }
};
```

- [ ] Admin: Can chat with Supervisor + all TWG agents
- [ ] Facilitator: Can chat with their TWG agent only
- [ ] Member: No agent chat access

#### Agent Selection UI
- [ ] Admin: Show dropdown to select agent
- [ ] Facilitator: Auto-connect to their TWG agent
- [ ] Member: Hide agent chat interface

---

### 10. Visual Indicators

#### Role Badges
- [ ] Show "Admin" badge in header for admins
- [ ] Show "Facilitator - [TWG Name]" badge for facilitators
- [ ] Show "Member" badge for members

#### TWG Context
- [ ] Display current TWG name prominently (for facilitators)
- [ ] Use TWG-specific color coding (optional)
- [ ] Show breadcrumbs with TWG context

#### Read-Only Indicators
- [ ] Show "Read-Only" label on member views
- [ ] Gray out non-editable fields
- [ ] Show lock icons on restricted features

---

### 11. Error Handling

#### Access Denied
```tsx
// 403 Forbidden handler
if (response.status === 403) {
  showNotification({
    type: 'error',
    message: 'You do not have permission to perform this action',
    duration: 5000
  });
}
```

- [ ] Show user-friendly error messages
- [ ] Redirect to appropriate page (e.g., dashboard)
- [ ] Log access attempts for security

#### Unauthorized Access
```tsx
// 401 Unauthorized handler
if (response.status === 401) {
  clearUserSession();
  redirectToLogin();
}
```

- [ ] Clear user session on 401
- [ ] Redirect to login page
- [ ] Show "Session expired" message

---

### 12. Testing Checklist

#### Role-Based Access Tests

**Admin Tests**:
- [ ] Admin can access all 6 TWG workspaces
- [ ] Admin can view user management page
- [ ] Admin can access system settings
- [ ] Admin can view global deal pipeline
- [ ] Admin can chat with all agents

**Facilitator Tests**:
- [ ] Facilitator can access their assigned TWG
- [ ] Facilitator CANNOT access other TWGs (403 error)
- [ ] Facilitator CANNOT access user management
- [ ] Facilitator CANNOT access system settings
- [ ] Facilitator can chat with their TWG agent only

**Member Tests**:
- [ ] Member can view meetings (read-only)
- [ ] Member can download documents
- [ ] Member CANNOT schedule meetings (no button)
- [ ] Member CANNOT upload documents (no button)
- [ ] Member CANNOT chat with agents

#### Cross-Role Tests
- [ ] Facilitator trying to access another TWG → 403
- [ ] Member trying to POST data → 403
- [ ] Non-admin trying to access /admin/users → 403
- [ ] Expired token → 401 and redirect to login

---

### 13. Security Best Practices

#### Frontend Security
- [ ] Never trust frontend-only checks (backend must validate)
- [ ] Hide sensitive data from unauthorized roles
- [ ] Don't expose admin features in DOM (even if hidden)
- [ ] Validate user role on every protected action

#### Token Security
- [ ] Store JWT securely (httpOnly cookie preferred)
- [ ] Don't store sensitive data in localStorage
- [ ] Implement token refresh mechanism
- [ ] Clear token on logout

#### API Security
- [ ] Always include Authorization header
- [ ] Handle token expiration gracefully
- [ ] Implement CSRF protection
- [ ] Use HTTPS in production

---

## Implementation Priority

### Phase 1: Core RBAC (Must Have)
1. ✅ User authentication and context
2. ✅ Route protection (PrivateRoute)
3. ✅ Role-based navigation
4. ✅ TWG access validation (facilitators)
5. ✅ API authorization headers

### Phase 2: UI/UX (Should Have)
6. ✅ Role-specific dashboards
7. ✅ Conditional component rendering
8. ✅ Visual role indicators
9. ✅ Error handling (403, 401)

### Phase 3: Advanced Features (Nice to Have)
10. ✅ Member read-only portal
11. ✅ Agent chat access control
12. ✅ Audit logging (frontend events)
13. ✅ Advanced search filtering

---

## Backend API Requirements

### Endpoints Must Return:
- `GET /api/users/me` - Current user info (role, TWG assignment)
- `GET /api/twgs` - All TWGs (admin) or assigned TWG (facilitator)
- `GET /api/twgs/:id/*` - Validate user has access to TWG

### Endpoints Must Validate:
- User role on every request
- TWG assignment for facilitators
- Read-only enforcement for members
- Return 403 for unauthorized access

---

## Quick Decision Tree

### "Should this user see this feature?"

```
Is user Admin?
├─ Yes → Show everything
└─ No → Is user Facilitator?
    ├─ Yes → Is this their TWG?
    │   ├─ Yes → Show (with edit access)
    │   └─ No → Hide/403
    └─ No → Is user Member?
        └─ Yes → Show read-only (if shared)
```

### "Should this button be enabled?"

```
Is action = write (create/edit/delete)?
├─ Yes → Is user Admin or Facilitator (for their TWG)?
│   ├─ Yes → Enable
│   └─ No → Disable/Hide
└─ No (read action) → Enable for all roles
```

---

## Resources

- [Admin Role Guide](./RBAC_ADMIN_ROLE.md)
- [Facilitator Role Guide](./RBAC_FACILITATOR_ROLE.md)
- [Member Role Guide](./RBAC_MEMBER_ROLE.md)
- [API Documentation](./API.md)
- [Architecture Overview](./ARCHITECTURE.md)

---

## Questions During Development?

### "Can a facilitator do X?"
→ Check [Facilitator Role Guide](./RBAC_FACILITATOR_ROLE.md) permissions matrix

### "What should admin see on dashboard?"
→ Check [Admin Role Guide](./RBAC_ADMIN_ROLE.md) UI components section

### "How do I validate TWG access?"
→ See "TWG Access Validation" in this document (Section 2)

### "What API endpoints can members access?"
→ Check [Member Role Guide](./RBAC_MEMBER_ROLE.md) API endpoints section

---

**Last Updated**: 2025-12-27  
**Maintained By**: Development Team
