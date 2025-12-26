# TWG Member Role - Interface & Access Guide

## Role Overview
**Role Name**: `member` (TWG Member/External Participant)

**Who**: Ministry representatives, external experts, country officials invited to participate in TWGs

**Access Level**: READ-ONLY or EMAIL-ONLY (minimal portal access)

---

## Permissions Matrix

### ✅ What Members CAN Do

#### Email Interaction (Primary)
- [ ] Receive meeting invitations via email
- [ ] Get calendar invites (.ics files)
- [ ] Receive meeting agendas and documents as attachments
- [ ] Receive meeting minutes after meetings
- [ ] Receive reminders and follow-ups
- [ ] Reply to emails (to facilitator/secretariat)

#### Portal Access (Optional/Read-Only)
- [ ] View their TWG's meeting schedule
- [ ] Download documents shared with them
- [ ] View meeting minutes (read-only)
- [ ] See upcoming meeting agendas
- [ ] View their assigned action items (if any)

---

### ❌ What Members CANNOT Do

#### No Editing/Management
- [ ] ❌ Schedule or cancel meetings
- [ ] ❌ Edit agendas or minutes
- [ ] ❌ Upload documents
- [ ] ❌ Create action items
- [ ] ❌ Approve AI-generated content
- [ ] ❌ Assign tasks to others

#### No System Access
- [ ] ❌ Access other TWGs (even read-only)
- [ ] ❌ Chat with AI agents
- [ ] ❌ View project pipeline
- [ ] ❌ Access user management
- [ ] ❌ View system settings
- [ ] ❌ See analytics or reports

#### No Cross-TWG Access
- [ ] ❌ View other TWGs' meetings
- [ ] ❌ Access documents from other TWGs
- [ ] ❌ See global calendar

---

## Primary Interaction: Email-Based

### Members Primarily Use EMAIL, Not Portal

**Why**: Most TWG members are busy officials who don't need another login. Email is their primary interface.

### Email Communications Members Receive:

#### 1. Meeting Invitations
```
Subject: Invitation – Energy TWG Meeting (Feb 10, 2026)

Dear Energy TWG Members,

You are invited to the next Energy & Infrastructure TWG meeting.

Date: Feb 10, 2026 (Wednesday)
Time: 14:00–16:00 GMT
Venue: Virtual (Zoom link below)

Agenda:
1. Review of action items from last meeting
2. Discussion on regional power pool expansion
3. Draft policy proposal review

Attached:
- Meeting Agenda (PDF)
- Background Brief on WAPP Integration

Please confirm your availability.

Zoom Link: https://zoom.us/j/123456789

Best regards,
ECOWAS Summit Secretariat (Energy TWG)
```

**Includes**:
- Calendar invite (.ics file) → Auto-adds to their calendar
- Agenda PDF
- Background documents
- Video call link

---

#### 2. Meeting Reminders
```
Subject: Reminder – Energy TWG Meeting Tomorrow (Feb 10)

Dear Colleagues,

This is a reminder that the Energy TWG meeting is tomorrow:

Date: Feb 10, 2026
Time: 14:00 GMT
Zoom: https://zoom.us/j/123456789

Please review the attached agenda.

See you tomorrow!
```

---

#### 3. Meeting Minutes
```
Subject: Minutes – Energy TWG Meeting (Feb 10, 2026)

Dear Energy TWG Members,

Thank you for attending today's meeting. Please find attached:
- Meeting Minutes (PDF)
- Action Items Summary

Key Decisions:
- Approved regional power pool expansion proposal
- Ghana to lead policy draft (due March 1)

Action Items:
- Dr. Smith: Share draft Green Hydrogen study (Feb 20)
- AfCEN: Provide energy access data (Feb 25)

Best regards,
ECOWAS Summit Secretariat
```

**Includes**:
- Full minutes (PDF)
- Action items list
- Any presentations shared during meeting

---

## Optional Portal Access (Read-Only)

### If Member Chooses to Log In

**Route**: `/member/dashboard` or `/member/my-twg`

**Components**:
```tsx
<MemberPortal>
  <WelcomeBanner>
    Welcome, {memberName}
    <TWGBadge>{assignedTWG.name} Member</TWGBadge>
  </WelcomeBanner>
  
  {/* Read-only views */}
  <UpcomingMeetings readOnly />
  <DocumentLibrary readOnly downloadEnabled />
  <MyActionItems readOnly />
  
  {/* NO editing tools */}
  {/* NO schedule button */}
  {/* NO upload button */}
  {/* NO agent chat */}
</MemberPortal>
```

---

### 1. Meeting Schedule (Read-Only)
**Route**: `/member/meetings`

**Components**:
```tsx
<MeetingSchedule readOnly>
  <MeetingList>
    <MeetingCard>
      <MeetingDate />
      <MeetingTime />
      <MeetingTopic />
      <AgendaDownloadButton />  {/* Can download */}
      <AddToCalendarButton />   {/* Can add to calendar */}
      
      {/* NO edit button */}
      {/* NO cancel button */}
    </MeetingCard>
  </MeetingList>
</MeetingSchedule>
```

---

### 2. Document Library (Read-Only)
**Route**: `/member/documents`

**Components**:
```tsx
<DocumentLibrary readOnly>
  <DocumentList>
    <Document>
      <FileName />
      <FileType />
      <UploadDate />
      <DownloadButton />  {/* Can download */}
      <PreviewButton />   {/* Can preview */}
      
      {/* NO delete button */}
      {/* NO edit button */}
    </Document>
  </DocumentList>
  
  {/* NO upload button */}
  {/* NO organize/folder tools */}
</DocumentLibrary>
```

**Access**: Only sees documents explicitly shared with TWG members

---

### 3. My Action Items (Read-Only)
**Route**: `/member/action-items`

**Components**:
```tsx
<MyActionItems readOnly>
  <ActionItemList>
    {/* Only shows items assigned to THIS member */}
    <ActionItem>
      <Title />
      <Description />
      <DueDate />
      <Status />
      
      {/* Member can see but not edit */}
      {/* Facilitator updates status */}
    </ActionItem>
  </ActionItemList>
  
  {/* NO create button */}
  {/* NO assign to others */}
</MyActionItems>
```

**Note**: Members can see action items assigned to them, but cannot mark as complete (they inform facilitator via email)

---

## Navigation Menu (If Portal Access)

**Components**:
```tsx
<MemberNavigation>
  <NavItem to="/member/dashboard">Dashboard</NavItem>
  <NavItem to="/member/meetings">Meetings</NavItem>
  <NavItem to="/member/documents">Documents</NavItem>
  <NavItem to="/member/action-items">My Tasks</NavItem>
  <NavItem to="/member/profile">My Profile</NavItem>
  
  {/* NO access to: */}
  {/* - Other TWGs */}
  {/* - Project pipeline */}
  {/* - AI agent */}
  {/* - User management */}
  {/* - System settings */}
</MemberNavigation>
```

---

## Access Control Implementation

### Frontend Guards
```tsx
// Route protection - read-only access
<PrivateRoute 
  path="/member/meetings" 
  component={MeetingSchedule}
  requiredRole="member"
  readOnly={true}
/>

// Component-level - hide edit buttons
{user.role !== 'member' && (
  <EditButton />  // Members don't see this
)}

// Show download-only actions
{user.role === 'member' && (
  <DownloadButton />  // Members can download
)}
```

### API Calls
```tsx
// Members can only GET (read), not POST/PUT/DELETE
const fetchMeetings = async () => {
  const response = await fetch(
    `/api/twgs/${user.assignedTWGId}/meetings`,
    {
      method: 'GET',  // Only GET allowed
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
};

// POST/PUT/DELETE will return 403 Forbidden
```

---

## Data Visibility Rules

### ✅ Member Can See:
- Meetings for their assigned TWG (read-only)
- Documents explicitly shared with TWG members
- Meeting agendas and minutes
- Action items assigned to them
- Their own profile information

### 🔒 Member Cannot See:
- Other TWGs' data
- Project pipeline
- Internal facilitator notes
- System settings
- User lists
- Analytics or reports
- AI agent conversations
- Draft documents (only final approved versions)

---

## UI/UX Considerations

### Visual Indicators
- Display "Member" badge in profile
- Show TWG name (e.g., "Energy TWG Member")
- Use read-only styling (grayed-out fields, no edit icons)

### Simplified Interface
- Minimal navigation (only essential pages)
- Focus on information consumption, not creation
- Large download buttons for easy access
- Clear "Read-Only" labels where appropriate

### Mobile-Friendly
- Since members may check on phones, ensure responsive design
- Easy-to-tap download buttons
- Calendar integration works on mobile

---

## Workflow Examples

### Example 1: Receiving Meeting Invite
1. Member receives email invitation
2. Clicks .ics attachment → Meeting added to calendar
3. Downloads agenda PDF from email
4. (Optional) Logs into portal to preview documents
5. Attends meeting at scheduled time
6. Receives minutes via email after meeting

### Example 2: Accessing Documents
1. Member receives email with document link
2. Clicks link → Redirects to portal login (if not logged in)
3. Logs in → Sees document library
4. Downloads needed documents
5. Logs out

### Example 3: Checking Action Items
1. Member receives email: "You have been assigned an action item"
2. (Optional) Logs into portal
3. Views "My Action Items"
4. Sees task: "Submit country energy data by Feb 20"
5. Completes task offline
6. Emails facilitator: "Task completed, data attached"
7. Facilitator updates status in system

---

## Testing Checklist

### Access Tests
- [ ] Member can log into portal (if credentials provided)
- [ ] Member can view their TWG meetings (read-only)
- [ ] Member can download documents
- [ ] Member CANNOT access other TWGs
- [ ] Member CANNOT access admin pages

### Permission Tests
- [ ] Member CANNOT schedule meetings (no button shown)
- [ ] Member CANNOT upload documents (no button shown)
- [ ] Member CANNOT edit agendas or minutes
- [ ] Member CANNOT create action items
- [ ] Member CANNOT chat with AI agents

### Email Tests
- [ ] Member receives meeting invitations
- [ ] Calendar invite (.ics) works correctly
- [ ] Member receives meeting reminders
- [ ] Member receives minutes after meetings
- [ ] Member receives action item notifications

### UI Tests
- [ ] Portal shows read-only views
- [ ] No edit/delete buttons visible
- [ ] Download buttons work correctly
- [ ] Navigation menu shows only allowed pages

---

## Development Notes

### State Management
```tsx
// Store member-specific state (minimal)
interface MemberState {
  assignedTWG: TWG;
  upcomingMeetings: Meeting[];
  sharedDocuments: Document[];
  myActionItems: ActionItem[];
}
```

### API Endpoints (Member-specific)
- `GET /api/member/meetings` - Upcoming meetings (read-only)
- `GET /api/member/documents` - Shared documents (read-only)
- `GET /api/member/action-items` - Assigned tasks (read-only)
- `GET /api/member/profile` - Own profile

**Backend Validation**: 
- Only GET requests allowed
- POST/PUT/DELETE return 403 Forbidden
- Data filtered to show only public/shared content

---

## Security Notes

⚠️ **Critical**: Members have minimal access. Ensure:
1. All write operations (POST/PUT/DELETE) are blocked
2. Only approved/final documents are visible (no drafts)
3. Email addresses are not exposed to other members
4. Portal login is optional (email is primary interface)
5. Session timeout for inactive members

---

## Quick Reference

**Role Identifier**: `role: "member"`

**Database Fields**: 
- `users.role = 'member'`
- `users.assigned_twg_id = <TWG_ID>`

**JWT Claim**: 
```json
{
  "role": "member",
  "twg_id": 1,
  "permissions": ["twg:read"]
}
```

**Route Pattern**: `/member/*` (read-only pages)

---

## Comparison with Other Roles

| Feature | Admin | Facilitator | Member |
|---------|-------|-------------|--------|
| View TWGs | All 6 | Assigned 1 | Assigned 1 (read-only) |
| Schedule meetings | ✅ | ✅ (their TWG) | ❌ |
| Upload documents | ✅ | ✅ (their TWG) | ❌ |
| Download documents | ✅ | ✅ | ✅ |
| Edit content | ✅ | ✅ (their TWG) | ❌ |
| Agent access | All agents | Their TWG agent | ❌ |
| Primary interface | Portal | Portal | Email |
| Portal access | Full | TWG-scoped | Read-only |

---

## Important Notes

### Portal Access is OPTIONAL
- Most members will NEVER log into the portal
- Email is the primary communication channel
- Portal is for members who want to:
  - Download documents on-demand
  - Check meeting schedule
  - View their action items

### Email-First Design
- All critical information sent via email
- Portal is supplementary, not required
- Members can fully participate via email only

### No Training Required
- Email interface is familiar to everyone
- Portal (if used) is simple and read-only
- No complex workflows for members
