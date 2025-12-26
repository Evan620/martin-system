# Admin Role - Interface & Access Guide

## Role Overview
**Role Name**: `admin` (Summit Administrator/Secretariat Leadership)

**Who**: Head of Content, Summit Director, Senior Secretariat staff with cross-TWG oversight

**Access Level**: FULL SYSTEM ACCESS - All TWGs, all data, all settings

---

## Permissions Matrix

### ✅ What Admins CAN Do

#### Global Access
- [ ] View ALL 6 TWGs (Energy, Agriculture, Minerals, Digital, Protocol, Resource Mobilization)
- [ ] Switch between any TWG workspace
- [ ] Access Summit Overview Dashboard (aggregated view)
- [ ] View global calendar with all TWG meetings
- [ ] See combined deal pipeline (all projects across TWGs)

#### TWG Management
- [ ] Create, edit, delete TWGs
- [ ] Assign facilitators to TWGs
- [ ] View all TWG meetings, agendas, minutes
- [ ] Access all TWG documents and repositories
- [ ] Override/edit any TWG content

#### User Management
- [ ] Create, edit, delete user accounts
- [ ] Assign roles (admin, facilitator, member)
- [ ] Manage TWG membership
- [ ] View user activity logs
- [ ] Disable/enable user accounts

#### Meeting & Communication
- [ ] Schedule meetings for ANY TWG
- [ ] Approve/edit AI-generated invites, agendas, minutes for any TWG
- [ ] Send communications on behalf of any TWG
- [ ] Cancel or reschedule any meeting

#### Project & Deal Pipeline
- [ ] View all projects across all TWGs
- [ ] Edit project details, scores, status
- [ ] Approve projects for Deal Room
- [ ] Generate cross-TWG project reports

#### AI Agent Interaction
- [ ] Chat with Supervisor Agent (global coordinator)
- [ ] Interact with ANY specialized TWG agent
- [ ] View agent logs and activity
- [ ] Override agent suggestions

#### System Configuration
- [ ] Modify email/document templates
- [ ] Configure system settings
- [ ] Manage knowledge base uploads
- [ ] Set global deadlines and milestones
- [ ] Access audit logs

#### Document Generation
- [ ] Generate cross-TWG synthesis documents
- [ ] Compile Abuja Declaration drafts
- [ ] Create Freetown Communiqué
- [ ] Export summit-wide reports

---

## UI Components & Pages

### 1. Dashboard (Landing Page)
**Route**: `/dashboard` or `/admin/overview`

**Components to Show**:
```tsx
<SummitOverviewDashboard>
  <StatusCards twgs={allTWGs} />           // All 6 TWGs with stats
  <GlobalCalendar events={allMeetings} />  // Combined calendar
  <DealPipelineOverview projects={allProjects} />
  <SystemAlerts />                         // Cross-TWG flags
  <RecentActivity />                       // All TWG activity
</SummitOverviewDashboard>
```

**Data Requirements**:
- Fetch all TWGs: `GET /api/twgs`
- Fetch all meetings: `GET /api/meetings`
- Fetch all projects: `GET /api/projects`
- Fetch system alerts: `GET /api/alerts`

---

### 2. Navigation Menu
**Components**:
```tsx
<AdminNavigation>
  <NavItem to="/dashboard">Summit Overview</NavItem>
  
  <NavDropdown label="TWG Workspaces">
    <NavItem to="/twg/energy">Energy & Infrastructure</NavItem>
    <NavItem to="/twg/agriculture">Agriculture & Food Systems</NavItem>
    <NavItem to="/twg/minerals">Critical Minerals</NavItem>
    <NavItem to="/twg/digital">Digital Economy</NavItem>
    <NavItem to="/twg/protocol">Protocol & Logistics</NavItem>
    <NavItem to="/twg/resource-mobilization">Resource Mobilization</NavItem>
  </NavDropdown>
  
  <NavItem to="/deal-pipeline">Deal Pipeline (All)</NavItem>
  <NavItem to="/documents">All Documents</NavItem>
  <NavItem to="/users">User Management</NavItem>
  <NavItem to="/settings">System Settings</NavItem>
  <NavItem to="/agent-supervisor">Supervisor Agent</NavItem>
</AdminNavigation>
```

---

### 3. TWG Workspace (Admin View)
**Route**: `/twg/:twgId`

**Components** (Same as Facilitator but with additional controls):
```tsx
<TWGWorkspace twgId={twgId} userRole="admin">
  {/* Standard TWG components */}
  <TWGHeader />
  <MeetingTimeline />
  <ActionItemsTracker />
  <DocumentRepository />
  <ProjectPipeline />
  <AgentChatInterface />
  
  {/* Admin-only components */}
  <AdminControls>
    <AssignFacilitatorButton />
    <EditTWGSettingsButton />
    <ViewAuditLogsButton />
  </AdminControls>
</TWGWorkspace>
```

---

### 4. User Management Page
**Route**: `/users`

**Components**:
```tsx
<UserManagement>
  <UserTable>
    <Columns>
      - Name
      - Email
      - Role (admin/facilitator/member)
      - TWG Assignment (if facilitator)
      - Status (active/disabled)
      - Actions (Edit, Delete, Disable)
    </Columns>
  </UserTable>
  
  <CreateUserButton />
  <BulkImportButton />
</UserManagement>
```

**Actions**:
- Create user: `POST /api/users`
- Edit user: `PUT /api/users/:id`
- Delete user: `DELETE /api/users/:id`
- Assign role: `PUT /api/users/:id/role`

---

### 5. Deal Pipeline (Global View)
**Route**: `/deal-pipeline`

**Components**:
```tsx
<GlobalDealPipeline>
  <FilterBar>
    <FilterByTWG />
    <FilterByStatus />
    <FilterByScore />
  </FilterBar>
  
  <ProjectTable>
    <Columns>
      - Project Name
      - TWG/Pillar
      - Investment Size
      - Readiness Score
      - Status
      - Actions (View, Edit, Approve)
    </Columns>
  </ProjectTable>
  
  <ExportReportButton />
  <GenerateDealRoomListButton />
</GlobalDealPipeline>
```

---

### 6. System Settings
**Route**: `/settings`

**Components**:
```tsx
<SystemSettings>
  <TemplateManagement>
    <EmailTemplates />
    <DocumentTemplates />
    <AgendaFormats />
  </TemplateManagement>
  
  <IntegrationSettings>
    <EmailConfig />
    <CalendarConfig />
    <AIModelSettings />
  </IntegrationSettings>
  
  <TimelineSettings>
    <MilestoneEditor />
    <DeadlineManager />
  </TimelineSettings>
</SystemSettings>
```

---

## Access Control Implementation

### Frontend Guards
```tsx
// Route protection
<PrivateRoute 
  path="/users" 
  component={UserManagement}
  requiredRole="admin"
/>

<PrivateRoute 
  path="/settings" 
  component={SystemSettings}
  requiredRole="admin"
/>

// Component-level
{user.role === 'admin' && (
  <AdminControls>
    <EditButton />
    <DeleteButton />
  </AdminControls>
)}
```

### API Calls
```tsx
// All API calls should include auth token
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}

// Backend validates role on every request
// Admin can access any endpoint
```

---

## Data Visibility Rules

### ✅ Admin Can See:
- All TWG data (meetings, documents, projects)
- All user accounts and activity
- System logs and audit trails
- Cross-TWG analytics and reports
- AI agent conversations (all TWGs)

### 🔒 Admin Cannot See:
- N/A (Full access to everything)

---

## UI/UX Considerations

### Visual Indicators
- Display "Admin" badge in header/profile
- Show "All TWGs" label on dashboard
- Use different color scheme for admin views (e.g., gold/purple accent)

### Breadcrumbs
```
Summit Overview > Energy TWG > Meeting #3
```
(Always show path back to overview)

### Contextual Help
- Tooltips explaining admin-only features
- Warning modals for destructive actions (delete user, etc.)

---

## Testing Checklist

### Access Tests
- [ ] Admin can view all 6 TWG workspaces
- [ ] Admin can switch between TWGs without restriction
- [ ] Admin can access user management page
- [ ] Admin can access system settings
- [ ] Admin can view global deal pipeline
- [ ] Admin can interact with Supervisor agent

### Permission Tests
- [ ] Admin can create/edit/delete users
- [ ] Admin can assign facilitators to TWGs
- [ ] Admin can approve content for any TWG
- [ ] Admin can override AI suggestions
- [ ] Admin can modify templates

### UI Tests
- [ ] Dashboard shows all TWG status cards
- [ ] Navigation menu includes all admin options
- [ ] Global calendar displays all meetings
- [ ] Deal pipeline shows projects from all TWGs

---

## Development Notes

### State Management
```tsx
// Store admin-specific state
interface AdminState {
  allTWGs: TWG[];
  allMeetings: Meeting[];
  allProjects: Project[];
  systemAlerts: Alert[];
  users: User[];
}
```

### API Endpoints (Admin-specific)
- `GET /api/admin/overview` - Dashboard data
- `GET /api/admin/users` - All users
- `POST /api/admin/users` - Create user
- `PUT /api/admin/users/:id/role` - Assign role
- `GET /api/admin/audit-logs` - System logs
- `PUT /api/admin/settings` - Update settings

---

## Security Notes

⚠️ **Critical**: Admin role has full system access. Ensure:
1. Strong authentication (2FA recommended)
2. All destructive actions require confirmation
3. Audit logging for all admin actions
4. Session timeout for inactive admins
5. IP whitelisting (optional, for production)

---

## Quick Reference

**Role Identifier**: `role: "admin"`

**Database Field**: `users.role = 'admin'`

**JWT Claim**: `{ role: 'admin', permissions: ['*'] }`

**Route Prefix**: `/admin/*` (optional, for admin-only pages)
