import { dashboardData } from '@/data/mock/dashboard'
import { apiFetch } from '@/lib/api/client'
import { isDemoModeEnabled } from '@/lib/config'
import type { ActionItem, DashboardData, Meeting, Project } from '@/types/signalroom'

type ProjectApiRow = {
  id: string
  name: string
  client?: string | null
  status: string
  description?: string | null
  owner_id?: string | null
  created_at: string
  updated_at: string
}

type PaginatedProjectResponse = {
  items: ProjectApiRow[]
}

type DecisionApiRow = {
  id: string
  title: string
  description?: string | null
  meeting_id: string
  created_at: string
}

type PaginatedDecisionResponse = {
  items: DecisionApiRow[]
}

type DashboardAggregateResponse = {
  total_meetings?: number
  completed_meetings?: number
  active_projects?: number
  open_action_items?: number
  overdue_action_items?: number
  upcoming_meetings?: Array<{ id: string; project_id?: string | null; title: string; description?: string | null; scheduled_start: string; scheduled_end: string; status: string }>
  recent_meetings?: Array<{ id: string; project_id?: string | null; title: string; description?: string | null; scheduled_start: string; scheduled_end: string; status: string }>
  action_items?: Array<{
    id: string
    meeting_id?: string | null
    title: string
    owner_name?: string | null
    due_date?: string | null
    priority?: string
    status?: string
  }>
  recent_activity?: Array<{ id: string; title: string; description: string; type: string; timestamp: string; link?: string | null }>
}

function mapProjectStatus(value: string): Project['status'] {
  switch (value) {
    case 'completed':
      return 'on-track'
    case 'in_review':
      return 'in-review'
    case 'at_risk':
      return 'at-risk'
    default:
      return 'on-track'
  }
}

function mapMeetingStatus(value: string): Meeting['status'] {
  switch (value) {
    case 'completed':
      return 'Ready'
    case 'in_progress':
      return 'Processing'
    case 'scheduled':
      return 'Scheduled'
    default:
      return 'Scheduled'
  }
}

function mapActionStatus(value?: string): ActionItem['status'] {
  switch (value) {
    case 'completed':
      return 'Done'
    case 'in_progress':
      return 'In progress'
    default:
      return 'Pending'
  }
}

function mapPriority(value?: string): ActionItem['priority'] {
  switch (value) {
    case 'high':
      return 'High'
    case 'low':
      return 'Low'
    default:
      return 'Medium'
  }
}

function buildFromApi(projectRows: ProjectApiRow[], aggregate: DashboardAggregateResponse, decisionRows: DecisionApiRow[]): DashboardData {
  const projectNames = new Map(projectRows.map((project) => [project.id, project.name]))
  const meetingRows = [...(aggregate.upcoming_meetings ?? []), ...(aggregate.recent_meetings ?? [])]
  const meetingNames = new Map(meetingRows.map((meeting) => [meeting.id, meeting.title]))
  const projects: Project[] = projectRows.map((project) => ({
    id: project.id,
    name: project.name,
    client: project.client ?? 'Internal',
    phase: 'Strategy',
    dueDate: project.created_at.slice(0, 10),
    progress: 0,
    owner: project.owner_id ? `Member ${project.owner_id.slice(0, 8)}` : 'Unassigned',
    ownerInitials: project.owner_id ? project.owner_id.slice(0, 2).toUpperCase() : 'NA',
    status: mapProjectStatus(project.status),
    accent: 'blue',
  }))

  const meetings: Meeting[] = meetingRows.map((item) => {
    const start = new Date(item.scheduled_start)
    const end = new Date(item.scheduled_end)
    const minutes = Math.max(30, Math.round((end.getTime() - start.getTime()) / 60000))
    const transcriptStatus: Meeting['transcriptStatus'] = item.status === 'completed' ? 'Ready' : 'Queued'

    return {
      id: item.id,
      title: item.title,
      project: item.project_id ? projectNames.get(item.project_id) ?? 'Unassigned project' : 'Unassigned project',
      date: start.toISOString().slice(0, 10),
      time: start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
      status: mapMeetingStatus(item.status),
      attendees: [],
      summary: item.description ?? 'Meeting summary is available in the backend workspace.',
      decisions: [],
      actionItems: [],
      confidence: item.status === 'completed' ? 94 : 0,
      duration: `${minutes} min`,
      transcriptStatus,
    }
  })

  const actionItems = (aggregate.action_items ?? []).map((item) => ({
    id: item.id,
    title: item.title,
    owner: item.owner_name ?? 'Unassigned',
    dueDate: item.due_date ? new Date(item.due_date).toISOString().slice(0, 10) : '',
    status: mapActionStatus(item.status),
    priority: mapPriority(item.priority),
    project: item.meeting_id ? projectNames.get(meetingRows.find((meeting) => meeting.id === item.meeting_id)?.project_id ?? '') ?? 'Unassigned project' : 'Unassigned project',
    source: item.meeting_id ? meetingNames.get(item.meeting_id) ?? 'Meeting intelligence' : 'Meeting intelligence',
  }))

  const activity = (aggregate.recent_activity ?? []).map((entry) => ({
    id: entry.id,
    person: 'System',
    initials: 'SY',
    action: entry.title,
    target: entry.description,
    time: new Date(entry.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    accent: 'blue',
  }))

  return {
    stats: {
      activeProjects: aggregate.active_projects ?? projects.length,
      deliveryHealth: aggregate.total_meetings ? Math.round(((aggregate.completed_meetings ?? 0) / aggregate.total_meetings) * 100) : 0,
      hoursLogged: 0,
      teamAvailability: 0,
    },
    projects,
    meetings,
    milestones: meetings.slice(0, 3).map((meeting, index) => ({
      id: `milestone-${meeting.id}`,
      title: meeting.title,
      project: meeting.project,
      date: new Date(meeting.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      time: meeting.time,
      complete: index === 0,
    })),
    activity,
    team: [],
    actionItems: actionItems,
    decisions: decisionRows.map((decision) => {
      const meeting = meetingRows.find((item) => item.id === decision.meeting_id)
      return {
        id: decision.id,
        text: decision.title,
        meeting: meeting?.title ?? 'Meeting',
        date: decision.created_at.slice(0, 10),
        project: meeting?.project_id ? projectNames.get(meeting.project_id) ?? 'Unassigned project' : 'Unassigned project',
        owner: 'Workspace',
      }
    }),
  }
}

export async function getDashboardData(): Promise<DashboardData> {
  if (isDemoModeEnabled()) {
    return dashboardData
  }

  const [projectResponse, aggregateResponse, decisionResponse] = await Promise.all([
    apiFetch<PaginatedProjectResponse>('/projects?limit=20'),
    apiFetch<DashboardAggregateResponse>('/dashboard/aggregates'),
    apiFetch<PaginatedDecisionResponse>('/decisions?limit=20'),
  ])

  return buildFromApi(projectResponse.items ?? [], aggregateResponse, decisionResponse.items ?? [])
}

export async function getProjects(): Promise<Project[]> {
  if (isDemoModeEnabled()) {
    return dashboardData.projects
  }

  const response = await apiFetch<PaginatedProjectResponse>('/projects?limit=20')
  return (response.items ?? []).map((project) => ({
    id: project.id,
    name: project.name,
    client: project.client ?? 'Internal',
    phase: 'Strategy',
    dueDate: project.created_at.slice(0, 10),
    progress: 0,
    owner: project.owner_id ? `Member ${project.owner_id.slice(0, 8)}` : 'Unassigned',
    ownerInitials: project.owner_id ? project.owner_id.slice(0, 2).toUpperCase() : 'NA',
    status: mapProjectStatus(project.status),
    accent: 'blue',
  }))
}
