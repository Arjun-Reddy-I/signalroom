export type ProjectStatus = 'at-risk' | 'in-review' | 'on-track'
export type ProjectPhase = 'Strategy' | 'Design' | 'Development' | 'Launch'

export interface Project {
  id: string
  name: string
  client: string
  phase: ProjectPhase
  dueDate: string
  progress: number
  owner: string
  ownerInitials: string
  status: ProjectStatus
  accent: string
}

export interface Milestone {
  id: string
  title: string
  project: string
  date: string
  time: string
  complete?: boolean
}

export interface Activity {
  id: string
  person: string
  initials: string
  action: string
  target: string
  time: string
  accent: string
}

export interface TeamMember {
  id: string
  name: string
  initials: string
  role: string
  allocation: number
  color: string
}

export interface ActionItem {
  id: string
  title: string
  owner: string
  dueDate: string
  status: 'Pending' | 'In progress' | 'Done'
  priority: 'High' | 'Medium' | 'Low'
  project: string
  source: string
}

export interface Meeting {
  id: string
  title: string
  project: string
  date: string
  time: string
  status: 'Scheduled' | 'Recording' | 'Processing' | 'Ready'
  attendees: string[]
  summary: string
  decisions: string[]
  actionItems: string[]
  confidence: number
  duration: string
  transcriptStatus: 'Ready' | 'Processing' | 'Queued'
}

export interface Decision {
  id: string
  text: string
  meeting: string
  date: string
  project: string
  owner: string
}

export interface DashboardStats {
  activeProjects: number
  deliveryHealth: number
  hoursLogged: number
  teamAvailability: number
}

export interface DashboardData {
  stats: DashboardStats
  projects: Project[]
  meetings: Meeting[]
  milestones: Milestone[]
  activity: Activity[]
  team: TeamMember[]
  actionItems: ActionItem[]
  decisions: Decision[]
}

export type ProjectFilter = 'all' | ProjectStatus
export type ViewName =
  | 'Overview'
  | 'Meetings'
  | 'Action Items'
  | 'Calendar'
  | 'Team'
  | 'Search'
  | 'Analytics'
  | 'Archive'
  | 'Settings'

export interface NewProjectInput {
  name: string
  client: string
}

export const statusLabels: Record<ProjectStatus, string> = {
  'at-risk': 'At risk',
  'in-review': 'In review',
  'on-track': 'On track',
}

export const phaseLabels: Record<ProjectPhase, string> = {
  Strategy: 'Strategy',
  Design: 'Design',
  Development: 'Development',
  Launch: 'Launch',
}

export const NAV_ITEMS: ViewName[] = [
  'Overview',
  'Meetings',
  'Action Items',
  'Calendar',
  'Team',
  'Search',
  'Analytics',
  'Archive',
  'Settings',
]

export const STATUS_FILTERS: { label: string; value: ProjectFilter }[] = [
  { label: 'All work', value: 'all' },
  { label: 'At risk', value: 'at-risk' },
  { label: 'In review', value: 'in-review' },
  { label: 'On track', value: 'on-track' },
]

export const isProjectStatus = (value: string): value is ProjectStatus =>
  value === 'at-risk' || value === 'in-review' || value === 'on-track'

export const isViewName = (value: string): value is ViewName =>
  NAV_ITEMS.includes(value as ViewName)

export const isNewProjectInput = (value: NewProjectInput): boolean =>
  value.name.trim().length > 1 && value.client.trim().length > 1

export const formatShortDate = (date: string) =>
  new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(
    new Date(`${date}T12:00:00`),
  )

export const EMPTY_DASHBOARD: DashboardData = {
  stats: { activeProjects: 0, deliveryHealth: 0, hoursLogged: 0, teamAvailability: 0 },
  projects: [],
  meetings: [],
  milestones: [],
  activity: [],
  team: [],
  actionItems: [],
  decisions: [],
}

export const DEMO_ERROR_MESSAGE = 'Signalroom could not load this view. Try again.'
export const DEMO_LOADING_LABEL = 'Loading workspace'

export const getGreeting = () => {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export const getTodayLabel = () =>
  new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date())

export const getDateRangeLabel = () => {
  const today = new Date()
  const start = new Date(today)
  start.setDate(today.getDate() - ((today.getDay() + 6) % 7))
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' })
  return `${formatter.format(start)}-${formatter.format(end)}, ${end.getFullYear()}`
}
export const getWorkspaceStatus = () => 'Meeting system nominal'
export const getStatusLabel = (status: ProjectStatus) => statusLabels[status]
export const projectStatusTone = (status: ProjectStatus) =>
  status === 'at-risk' ? 'status-risk' : status === 'in-review' ? 'status-review' : 'status-track'
export const initialsTone = (accent: string) =>
  accent === 'blue' ? 'avatar-blue' : accent === 'coral' ? 'avatar-coral' : accent === 'green' ? 'avatar-green' : 'avatar-amber'

export const createProject = (input: NewProjectInput): Project => ({
  id: `new-${Date.now()}`,
  name: input.name.trim(),
  client: input.client.trim(),
  phase: 'Strategy',
  dueDate: '2026-09-30',
  progress: 8,
  owner: 'You',
  ownerInitials: 'YO',
  status: 'on-track',
  accent: 'amber',
})

export const projectMatches = (project: Project, filter: ProjectFilter, query: string) => {
  const haystack = `${project.name} ${project.client} ${project.phase} ${project.owner}`.toLowerCase()
  return (filter === 'all' || project.status === filter) && haystack.includes(query.trim().toLowerCase())
}

export const filterProjects = (projects: Project[], filter: ProjectFilter, query: string) =>
  projects.filter((project) => projectMatches(project, filter, query))

export const getStatusCount = (projects: Project[], status: ProjectFilter) =>
  status === 'all' ? projects.length : projects.filter((project) => project.status === status).length

export const getProjectScore = (project: Project) => {
  const base = project.progress
  const risk = project.status === 'at-risk' ? 10 : project.status === 'in-review' ? 18 : 24
  return Math.max(0, Math.min(100, base + risk))
}

export const defaultProjectInput: NewProjectInput = { name: '', client: '' }
export const APP_NAME = 'Signalroom'
export const APP_DESCRIPTION = 'A calm command center for meeting intelligence.'
export const getWorkspaceLabel = () => 'Northstar Studio'
export const getProjectDueDateLabel = (project: Project) => formatShortDate(project.dueDate)
export const getNotificationCount = () => 3
export const getCurrentUserName = () => 'Mara'
export const getCurrentUserInitials = () => 'MA'
export const getCurrentUserRole = () => 'Studio lead'

export const buildDashboardStats = (projects: Project[], team: TeamMember[]): DashboardStats => ({
  activeProjects: projects.length,
  deliveryHealth: Math.round(
    projects.reduce((sum, project) => {
      const score = project.status === 'at-risk' ? 68 : project.status === 'in-review' ? 82 : 93
      return sum + score
    }, 0) / Math.max(projects.length, 1),
  ),
  hoursLogged: 248,
  teamAvailability: Math.round(team.reduce((sum, member) => sum + (100 - member.allocation), 0) / Math.max(team.length, 1)),
})

export const getTaskPriorityTone = (priority: ActionItem['priority']) =>
  priority === 'High' ? 'priority-high' : priority === 'Medium' ? 'priority-medium' : 'priority-low'

export const getMeetingStatusTone = (status: Meeting['status']) =>
  status === 'Ready' ? 'meeting-ready' : status === 'Processing' ? 'meeting-processing' : status === 'Recording' ? 'meeting-recording' : 'meeting-scheduled'

export const getSearchPlaceholder = () => 'Search meetings, tasks, and people'
export const getDefaultView = (): ViewName => 'Overview'
export const appName = APP_NAME
export const appDescription = APP_DESCRIPTION
export const workspaceName = getWorkspaceLabel
export const currentUserName = getCurrentUserName
export const currentUserInitials = getCurrentUserInitials
export const currentUserRole = getCurrentUserRole
export const statusFilters = STATUS_FILTERS
export const navItems = NAV_ITEMS
export const formatDateLong = (value: string) =>
  value ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : 'No date'
export const getMeetingStatusLabel = (status: Meeting['status']) => status
export const isMeetingReady = (meeting: Meeting) => meeting.status === 'Ready'
export const isActionDone = (item: ActionItem) => item.status === 'Done'
export const isProjectVisible = projectMatches
export const getProjectHealth = (project: Project) =>
  project.status === 'at-risk' ? 'Needs attention' : project.status === 'in-review' ? 'Awaiting review' : 'Healthy'
export const safeParseFilter = (value: string | null): ProjectFilter =>
  value && (value === 'all' || isProjectStatus(value)) ? value : 'all'
export const safeParseView = (value: string | null): ViewName =>
  value && isViewName(value) ? value : getDefaultView()
export const getActionItemProgress = (items: ActionItem[]) => {
  if (items.length === 0) return 0
  const done = items.filter((item) => item.status === 'Done').length
  return Math.round((done / items.length) * 100)
}

export type ToastState = { message: string; type: 'success' | 'info' | 'error' }
