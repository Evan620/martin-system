# TWG Facilitator Role - Interface & Access Guide

## Role Overview
**Role Name**: `facilitator` (TWG Facilitator/Secretariat Rapporteur)

**Who**: Secretariat staff assigned to coordinate a specific TWG

**Access Level**: FULL ACCESS to assigned TWG only, NO access to other TWGs

---

## Permissions Matrix

### ✅ What Facilitators CAN Do (Within Their TWG Only)

#### TWG Workspace Access
- [ ] View their assigned TWG workspace
- [ ] Access all meetings for their TWG
- [ ] View all documents in their TWG repository
- [ ] See their TWG's project pipeline
- [ ] View action items and tasks for their TWG

#### Meeting Management
- [ ] Schedule meetings for their TWG
- [ ] Create meeting agendas
- [ ] Review and approve AI-generated invites
- [ ] Edit meeting details (time, venue, participants)
- [ ] Cancel or reschedule their TWG meetings
- [ ] Mark attendance after meetings

#### Document Management
- [ ] Upload documents to their TWG repository
- [ ] Download documents from their TWG
- [ ] Organize documents (folders, tags)
- [ ] Review and approve AI-generated minutes
- [ ] Edit draft documents (agendas, minutes, reports)

#### Communication
- [ ] Send meeting invites to their TWG members
- [ ] Send reminders and follow-ups
- [ ] Approve email content before sending
- [ ] Communicate with their TWG participants

#### Action Items & Tasks
- [ ] Create action items
- [ ] Assign tasks to TWG members
- [ ] Update task status
- [ ] Set deadlines
- [ ] Track completion

#### Project Pipeline (Their TWG)
- [ ] View projects submitted to their TWG
- [ ] Add new project proposals
- [ ] Edit project details
- [ ] Update project status
- [ ] Submit projects for Resource Mobilization review

#### AI Agent Interaction
- [ ] Chat with their assigned TWG agent (e.g., Energy agent)
- [ ] Request document drafts from agent
- [ ] Ask agent to schedule tasks
- [ ] Review and approve agent suggestions

---

### ❌ What Facilitators CANNOT Do

#### Restricted Access
- [ ] ❌ View other TWGs' workspaces
- [ ] ❌ Access other TWGs' meetings or documents
- [ ] ❌ See projects from other TWGs
- [ ] ❌ Chat with other TWG agents
- [ ] ❌ Access Supervisor agent directly

#### System Administration
- [ ] ❌ Create or delete user accounts
- [ ] ❌ Assign roles to users
- [ ] ❌ Modify system settings
- [ ] ❌ Edit email/document templates
- [ ] ❌ Access audit logs
- [ ] ❌ View global analytics

#### Cross-TWG Actions
- [ ] ❌ Schedule meetings for other TWGs
- [ ] ❌ Approve content for other TWGs
- [ ] ❌ Access global deal pipeline
- [ ] ❌ Generate cross-TWG reports

---

## UI Components & Pages

### 1. Dashboard (Landing Page)
**Route**: `/dashboard` or `/twg/my-workspace`

**Components to Show**:
```tsx
<FacilitatorDashboard>
  {/* Single TWG focus */}
  <TWGHeader twg={assignedTWG}>
    <TWGName>{assignedTWG.name}</TWGName>
    <TWGLeads>
      <PoliticalLead />
      <TechnicalLead />
    </TWGLeads>
    <QuickStats>
      <NextMeeting />
      <OpenActionItems />
      <ProjectCount />
    </QuickStats>
  </TWGHeader>
  
  <UpcomingMeetings twgId={assignedTWG.id} />
  <RecentActivity twgId={assignedTWG.id} />
  <PendingApprovals />  {/* AI drafts awaiting review */}
</FacilitatorDashboard>
```

**Data Requirements**:
- Fetch assigned TWG: `GET /api/users/me/twg`
- Fetch TWG meetings: `GET /api/twgs/{twgId}/meetings`
- Fetch action items: `GET /api/twgs/{twgId}/action-items`

---

### 2. Navigation Menu
**Components**:
```tsx
<FacilitatorNavigation>
  <NavItem to="/dashboard">My TWG Dashboard</NavItem>
  
  {/* NO dropdown for other TWGs */}
  <NavSection label={assignedTWG.name}>
    <NavItem to="/meetings">Meetings</NavItem>
    <NavItem to="/action-items">Action Items</NavItem>
    <NavItem to="/documents">Documents</NavItem>
    <NavItem to="/projects">Projects</NavItem>
    <NavItem to="/agent">AI Assistant</NavItem>
  </NavSection>
  
  <NavItem to="/profile">My Profile</NavItem>
  
  {/* NO access to: */}
  {/* - Other TWGs */}
  {/* - User Management */}
  {/* - System Settings */}
  {/* - Global Deal Pipeline */}
</FacilitatorNavigation>
```

---

### 3. Meeting Management
**Route**: `/meetings`

**Components**:
```tsx
<MeetingManagement twgId={assignedTWG.id}>
  <MeetingTimeline>
    <UpcomingMeetings />
    <PastMeetings />
  </MeetingTimeline>
  
  <ScheduleMeetingButton onClick={openScheduleModal} />
  
  <MeetingCard meeting={meeting}>
    <MeetingDetails />
    <AgendaPreview />
    <ParticipantList />
    <Actions>
      <ViewAgenda />
      <ViewMinutes />
      <EditMeeting />
      <CancelMeeting />
    </Actions>
  </MeetingCard>
</MeetingManagement>
```

**Workflow**:
1. Click "Schedule Meeting"
2. AI agent drafts invite with suggested agenda
3. Facilitator reviews and edits
4. Approve → System sends invites to TWG members
5. After meeting → AI drafts minutes
6. Facilitator reviews and approves minutes
7. System sends minutes to participants

---

### 4. Action Items Tracker
**Route**: `/action-items`

**Components**:
```tsx
<ActionItemsTracker twgId={assignedTWG.id}>
  <FilterBar>
    <FilterByStatus />  {/* Open, In Progress, Completed */}
    <FilterByAssignee />
    <FilterByDueDate />
  </FilterBar>
  
  <ActionItemList>
    <ActionItem>
      <Title />
      <AssignedTo />
      <DueDate />
      <Status />
      <Actions>
        <EditButton />
        <MarkCompleteButton />
        <SendReminderButton />
      </Actions>
    </ActionItem>
  </ActionItemList>
  
  <CreateActionItemButton />
</ActionItemsTracker>
```

---

### 5. Document Repository
**Route**: `/documents`

**Components**:
```tsx
<DocumentRepository twgId={assignedTWG.id}>
  <FolderStructure>
    <Folder name="Meeting Agendas" />
    <Folder name="Meeting Minutes" />
    <Folder name="Policy Drafts" />
    <Folder name="Background Materials" />
    <Folder name="Templates" />
  </FolderStructure>
  
  <DocumentList>
    <Document>
      <FileName />
      <FileType />
      <UploadDate />
      <Actions>
        <DownloadButton />
        <PreviewButton />
        <DeleteButton />
      </Actions>
    </Document>
  </DocumentList>
  
  <UploadButton />
  <SearchBar />
</DocumentRepository>
```

**Access Control**:
- Can only see documents tagged for their TWG
- Cannot access documents from other TWGs

---

### 6. Project Pipeline (TWG-Specific)
**Route**: `/projects`

**Components**:
```tsx
<ProjectPipeline twgId={assignedTWG.id}>
  <ProjectList>
    <Project>
      <ProjectName />
      <InvestmentSize />
      <ReadinessScore />
      <Status />
      <Actions>
        <ViewDetailsButton />
        <EditButton />
        <SubmitToResourceMobButton />
      </Actions>
    </Project>
  </ProjectList>
  
  <AddProjectButton />
  <ExportListButton />
</ProjectPipeline>
```

**Note**: Only shows projects for their TWG (e.g., Energy facilitator only sees energy projects)

---

### 7. AI Agent Chat Interface
**Route**: `/agent`

**Components**:
```tsx
<AgentChatInterface agentType={assignedTWG.agentType}>
  <ChatHeader>
    <AgentName>{assignedTWG.name} Assistant</AgentName>
    <AgentStatus>Online</AgentStatus>
  </ChatHeader>
  
  <ChatMessages>
    <Message from="agent">
      How can I help with the {assignedTWG.name} TWG today?
    </Message>
    <Message from="user">
      Draft an agenda for our next meeting
    </Message>
    <Message from="agent">
      I've prepared a draft agenda. Would you like to review it?
      <PreviewButton />
    </Message>
  </ChatMessages>
  
  <ChatInput>
    <TextArea placeholder="Ask your AI assistant..." />
    <SendButton />
  </ChatInput>
  
  <QuickActions>
    <Button>Schedule Meeting</Button>
    <Button>Draft Minutes</Button>
    <Button>Summarize Last Meeting</Button>
  </QuickActions>
</AgentChatInterface>
```

**Agent Scope**: Can ONLY chat with their assigned TWG agent (e.g., Energy facilitator → Energy agent)

---

## Access Control Implementation

### Frontend Guards
```tsx
// Route protection - check TWG assignment
<PrivateRoute 
  path="/meetings" 
  component={MeetingManagement}
  requiredRole="facilitator"
  validateTWGAccess={true}
/>

// Component-level - hide other TWGs
{user.role === 'facilitator' && (
  <MyTWGWorkspace twgId={user.assignedTWGId} />
)}

// Prevent access to other TWGs
{twgId !== user.assignedTWGId && (
  <AccessDenied message="You can only access your assigned TWG" />
)}
```

### API Calls
```tsx
// All API calls filtered by assigned TWG
const fetchMeetings = async () => {
  const response = await fetch(
    `/api/twgs/${user.assignedTWGId}/meetings`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  // Backend validates user is assigned to this TWG
};
```

---

## Data Visibility Rules

### ✅ Facilitator Can See:
- All data for their assigned TWG
- Meetings, agendas, minutes for their TWG
- Documents in their TWG repository
- Projects submitted to their TWG
- Action items for their TWG
- Their TWG agent's chat history

### 🔒 Facilitator Cannot See:
- Other TWGs' workspaces or data
- Global analytics or cross-TWG reports
- User management information
- System settings or templates
- Audit logs
- Other TWG agents' conversations

---

## UI/UX Considerations

### Visual Indicators
- Display TWG name prominently in header (e.g., "Energy TWG Workspace")
- Show "Facilitator" badge in profile
- Use TWG-specific color coding (optional)

### Breadcrumbs
```
Energy TWG > Meetings > Meeting #3
```
(No "Summit Overview" or other TWG links)

### Contextual Help
- Tooltips explaining facilitator permissions
- Guidance on how to interact with AI agent
- Onboarding tour for first-time facilitators

### Pending Approvals Badge
- Show notification badge when AI has drafts ready for review
- Example: "3 pending approvals" (invites, minutes, etc.)

---

## Workflow Examples

### Example 1: Scheduling a Meeting
1. Facilitator clicks "Schedule Meeting"
2. Fills in basic details (date, time, topic)
3. AI agent generates:
   - Draft agenda based on previous meetings
   - Invitation email text
   - Calendar invite (.ics)
4. Facilitator reviews and edits
5. Clicks "Approve & Send"
6. System sends invites to all TWG members
7. Meeting appears on TWG calendar

### Example 2: After a Meeting
1. Facilitator uploads meeting recording/notes (optional)
2. AI agent drafts minutes:
   - Attendance list
   - Discussion summary
   - Decisions made
   - Action items
3. Facilitator reviews draft
4. Edits any inaccuracies
5. Approves minutes
6. System sends minutes to participants
7. Action items auto-populate in tracker

### Example 3: Adding a Project
1. Facilitator clicks "Add Project"
2. Fills in project details:
   - Name, description
   - Investment size
   - Lead country/organization
3. Uploads supporting documents
4. Submits to Resource Mobilization TWG
5. Project appears in their TWG pipeline
6. Resource Mobilization team receives notification

---

## Testing Checklist

### Access Tests
- [ ] Facilitator can access their assigned TWG workspace
- [ ] Facilitator CANNOT access other TWG workspaces
- [ ] Facilitator CANNOT access admin pages (users, settings)
- [ ] Facilitator can chat with their TWG agent only
- [ ] Facilitator CANNOT chat with Supervisor or other agents

### Permission Tests
- [ ] Facilitator can schedule meetings for their TWG
- [ ] Facilitator can upload documents to their TWG
- [ ] Facilitator can create action items
- [ ] Facilitator can add projects to their TWG pipeline
- [ ] Facilitator CANNOT create users or assign roles

### UI Tests
- [ ] Dashboard shows only assigned TWG data
- [ ] Navigation menu does NOT show other TWGs
- [ ] Document repository shows only their TWG files
- [ ] Project pipeline shows only their TWG projects
- [ ] Meeting list shows only their TWG meetings

### Data Isolation Tests
- [ ] API calls for other TWGs return 403 Forbidden
- [ ] Search results only include their TWG documents
- [ ] Agent chat only responds to their TWG queries

---

## Development Notes

### State Management
```tsx
// Store facilitator-specific state
interface FacilitatorState {
  assignedTWG: TWG;
  twgMeetings: Meeting[];
  twgProjects: Project[];
  twgDocuments: Document[];
  actionItems: ActionItem[];
  pendingApprovals: Approval[];
}
```

### API Endpoints (Facilitator-specific)
- `GET /api/users/me/twg` - Get assigned TWG
- `GET /api/twgs/{twgId}/meetings` - TWG meetings (validated)
- `POST /api/twgs/{twgId}/meetings` - Schedule meeting
- `GET /api/twgs/{twgId}/documents` - TWG documents
- `POST /api/twgs/{twgId}/documents` - Upload document
- `GET /api/twgs/{twgId}/projects` - TWG projects
- `POST /api/twgs/{twgId}/action-items` - Create action item

**Backend Validation**: Every request checks `user.assignedTWGId === twgId`

---

## Security Notes

⚠️ **Critical**: Facilitators have TWG-scoped access. Ensure:
1. Backend validates TWG assignment on EVERY request
2. Frontend hides UI elements for inaccessible resources
3. API returns 403 Forbidden for unauthorized TWG access
4. Agent chat is scoped to assigned TWG only
5. Document search is filtered by TWG

---

## Quick Reference

**Role Identifier**: `role: "facilitator"`

**Database Fields**: 
- `users.role = 'facilitator'`
- `users.assigned_twg_id = <TWG_ID>`

**JWT Claim**: 
```json
{
  "role": "facilitator",
  "twg_id": 1,
  "permissions": ["twg:read", "twg:write", "twg:schedule"]
}
```

**Route Pattern**: `/twg/*` or `/dashboard` (scoped to their TWG)

---

## Comparison with Admin

| Feature | Admin | Facilitator |
|---------|-------|-------------|
| View TWGs | All 6 | Only assigned 1 |
| Schedule meetings | Any TWG | Their TWG only |
| User management | ✅ | ❌ |
| System settings | ✅ | ❌ |
| Global pipeline | ✅ | ❌ (TWG-specific) |
| Agent access | All agents | Their TWG agent |
| Dashboard | Summit-wide | TWG-specific |
