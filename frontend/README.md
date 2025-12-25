# ECOWAS Summit TWG System - Frontend

React + TypeScript frontend for the ECOWAS Summit Technical Working Groups support system.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Redux Toolkit** - State management
- **React Router** - Routing
- **TailwindCSS** - Styling
- **Axios** - HTTP client
- **Socket.io** - WebSocket for real-time features
- **React Hook Form** - Form handling
- **Zod** - Schema validation

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── common/         # Generic components (Button, Card, etc.)
│   ├── layout/         # Layout components (Header, Sidebar)
│   ├── twg/            # TWG-specific components
│   ├── meetings/       # Meeting components
│   ├── documents/      # Document components
│   ├── agents/         # Agent chat components
│   └── projects/       # Project components
├── pages/              # Page components
├── features/           # Feature modules (Redux slices)
├── hooks/              # Custom React hooks
├── services/           # API service layer
├── store/              # Redux store configuration
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
└── styles/             # Global styles
```

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Setup environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:5173

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Lint code
- `npm test` - Run tests
- `npm run test:ui` - Run tests with UI
- `npm run coverage` - Generate coverage report

## Features

### User Roles
- **Admin** - Full system access, manage users and settings
- **TWG Facilitator** - Manage specific TWG, interact with agents
- **Member** - View-only access to assigned TWG

### Pages

1. **Login** - Authentication
2. **Dashboard** - Overview of all TWGs
3. **TWG Workspace** - Dedicated workspace for each TWG
   - Meeting timeline
   - Document repository
   - Agent chat interface
   - Action items tracker
4. **Meetings** - Meeting management
5. **Documents** - Document library
6. **Projects** - Deal pipeline (Resource Mobilization)
7. **Settings** - User preferences

### Key Components

#### Agent Chat
Interactive chat interface to communicate with AI agents:
- Send commands
- Review generated content
- Approve/edit outputs

#### TWG Dashboard
Per-TWG view showing:
- Upcoming meetings
- Recent documents
- Action items
- Project status

#### Meeting Timeline
Calendar and list view of meetings with:
- Agendas
- Minutes
- Attendance
- Action items

#### Document Repository
Organized document storage with:
- Version control
- Search and filtering
- Preview capabilities
- Download/upload

## Development

### Code Style

- Use TypeScript for all files
- Follow functional component pattern with hooks
- Use Redux Toolkit for global state
- Keep components small and focused
- Write tests for complex logic

### State Management

Use Redux Toolkit for:
- Authentication state
- TWG data
- Meetings and documents
- UI state (modals, notifications)

Use local state (useState) for:
- Form inputs
- Component-specific UI state

### API Integration

All API calls go through service layer in `src/services/`:

```typescript
// services/twgService.ts
import api from './api'

export const getTWGs = () => api.get('/twgs')
export const getTWG = (id: string) => api.get(`/twgs/${id}`)
```

The `api` instance handles:
- Base URL configuration
- Auth token injection
- Error handling
- Response transformation

### Routing

Protected routes require authentication:

```typescript
<Route element={<ProtectedRoute />}>
  <Route path="/dashboard" element={<Dashboard />} />
  <Route path="/twg/:id" element={<TWGWorkspace />} />
</Route>
```

### Forms

Use React Hook Form with Zod validation:

```typescript
const schema = z.object({
  title: z.string().min(1),
  date: z.date(),
})

const form = useForm({
  resolver: zodResolver(schema),
})
```

## Testing

Run tests:
```bash
npm test
```

Write tests for:
- Complex components
- Redux slices
- Utility functions
- API services

Example test:
```typescript
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

test('renders button with text', () => {
  render(<Button>Click me</Button>)
  expect(screen.getByText('Click me')).toBeInTheDocument()
})
```

## Building for Production

```bash
npm run build
```

Outputs to `dist/` directory.

Preview production build locally:
```bash
npm run preview
```

## Environment Variables

See `.env.example` for all available variables.

Key variables:
- `VITE_API_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL for real-time features
- `VITE_APP_NAME` - Application name
- Feature flags for optional features

## Styling

Using TailwindCSS utility classes:

```tsx
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
  <h2 className="text-lg font-semibold">Title</h2>
  <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
    Action
  </button>
</div>
```

## Common Tasks

### Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `App.tsx`
3. Add navigation link if needed

### Adding a New Feature

1. Create feature slice in `src/features/`
2. Add to Redux store
3. Create API service if needed
4. Build UI components

### Adding a Component

1. Create component in appropriate directory
2. Export from index file
3. Write tests if complex
4. Use TypeScript for props

## Troubleshooting

### Build Issues
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Type Errors
Check `tsconfig.json` and ensure all types are properly defined.

### API Connection
Verify `VITE_API_URL` in `.env` matches backend URL.

## Contributing

1. Create feature branch
2. Make changes
3. Write/update tests
4. Lint code
5. Submit pull request

## License

Proprietary - ECOWAS Summit 2026
