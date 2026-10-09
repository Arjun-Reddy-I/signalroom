import type { ActionItem, Activity, DashboardData, Decision, Meeting, Milestone, Project, TeamMember } from '@/types/signalroom'

export const projects: Project[] = [
  { id: 'p-01', name: 'Northstar rebrand', client: 'Northstar Health', phase: 'Design', dueDate: '2026-09-04', progress: 72, owner: 'Mara Chen', ownerInitials: 'MC', status: 'in-review', accent: 'blue' },
  { id: 'p-02', name: 'Field notes / Q3', client: 'Common Ground', phase: 'Development', dueDate: '2026-09-09', progress: 48, owner: 'Jules Park', ownerInitials: 'JP', status: 'on-track', accent: 'coral' },
  { id: 'p-03', name: 'Signal system', client: 'Lumen Objects', phase: 'Strategy', dueDate: '2026-08-29', progress: 31, owner: 'Mara Chen', ownerInitials: 'MC', status: 'at-risk', accent: 'amber' },
  { id: 'p-04', name: 'Open studio launch', client: 'Assembly House', phase: 'Launch', dueDate: '2026-09-18', progress: 86, owner: 'Dani Okafor', ownerInitials: 'DO', status: 'on-track', accent: 'green' },
]
export const milestones: Milestone[] = [
  { id: 'm-01', title: 'Homepage review', project: 'Northstar rebrand', date: 'Aug 27', time: '10:00 AM' },
  { id: 'm-02', title: 'Content handoff', project: 'Field notes / Q3', date: 'Aug 28', time: '2:30 PM' },
  { id: 'm-03', title: 'Strategy workshop', project: 'Signal system', date: 'Aug 29', time: '9:00 AM' },
  { id: 'm-04', title: 'Launch checklist', project: 'Open studio launch', date: 'Aug 30', time: '4:00 PM', complete: true },
]
export const activity: Activity[] = [
  { id: 'a-01', person: 'Jules Park', initials: 'JP', action: 'uploaded new files to', target: 'Field notes / Q3', time: '18 min ago', accent: 'coral' },
  { id: 'a-02', person: 'Mara Chen', initials: 'MC', action: 'moved', target: 'Northstar rebrand to review', time: '1 hr ago', accent: 'blue' },
  { id: 'a-03', person: 'Dani Okafor', initials: 'DO', action: 'completed a milestone in', target: 'Open studio launch', time: '3 hrs ago', accent: 'green' },
  { id: 'a-04', person: 'Mara Chen', initials: 'MC', action: 'left a note on', target: 'Signal system', time: 'Yesterday', accent: 'amber' },
]
export const team: TeamMember[] = [
  { id: 't-01', name: 'Mara Chen', initials: 'MC', role: 'Studio lead', allocation: 82, color: 'blue' },
  { id: 't-02', name: 'Jules Park', initials: 'JP', role: 'Design director', allocation: 68, color: 'coral' },
  { id: 't-03', name: 'Dani Okafor', initials: 'DO', role: 'Producer', allocation: 54, color: 'green' },
  { id: 't-04', name: 'Theo Bell', initials: 'TB', role: 'Developer', allocation: 41, color: 'amber' },
]
export const meetings: Meeting[] = [
  { id: 'mt-01', title: 'Product planning sync', project: 'Northstar rebrand', date: '2026-09-02', time: '10:00 AM', status: 'Ready', attendees: ['Mara Chen', 'Jules Park', 'Dani Okafor'], summary: 'The team aligned on the launch narrative and narrowed the homepage direction.', decisions: ['Use the editorial route for the homepage'], actionItems: ['Finalize homepage copy', 'Share the updated launch brief'], confidence: 94, duration: '42 min', transcriptStatus: 'Ready' },
  { id: 'mt-02', title: 'Engineering weekly sync', project: 'Signal system', date: '2026-09-03', time: '2:00 PM', status: 'Processing', attendees: ['Theo Bell', 'Mara Chen'], summary: 'Technical sync is being processed into a searchable meeting record.', decisions: [], actionItems: [], confidence: 0, duration: '31 min', transcriptStatus: 'Processing' },
  { id: 'mt-03', title: 'Client strategy review', project: 'Field notes / Q3', date: '2026-09-05', time: '11:30 AM', status: 'Scheduled', attendees: ['Jules Park', 'Common Ground'], summary: 'Review the campaign direction and confirm the next delivery milestone.', decisions: [], actionItems: [], confidence: 0, duration: '45 min', transcriptStatus: 'Queued' },
]
export const actionItems: ActionItem[] = [
  { id: 'task-01', title: 'Finalize homepage copy', owner: 'Mara Chen', dueDate: '2026-09-04', status: 'In progress', priority: 'High', project: 'Northstar rebrand', source: 'Product planning sync' },
  { id: 'task-02', title: 'Share updated launch brief', owner: 'Jules Park', dueDate: '2026-09-06', status: 'Pending', priority: 'Medium', project: 'Northstar rebrand', source: 'Product planning sync' },
  { id: 'task-03', title: 'Confirm transcript taxonomy', owner: 'Theo Bell', dueDate: '2026-09-08', status: 'Done', priority: 'Low', project: 'Signal system', source: 'Engineering weekly sync' },
]
export const decisions: Decision[] = [
  { id: 'decision-01', text: 'Use the editorial route for the homepage', meeting: 'Product planning sync', date: '2026-09-02', project: 'Northstar rebrand', owner: 'Mara Chen' },
  { id: 'decision-02', text: 'Keep action-item extraction visible in the first release', meeting: 'Engineering weekly sync', date: '2026-08-28', project: 'Signal system', owner: 'Theo Bell' },
]
export const dashboardData: DashboardData = { stats: { activeProjects: 4, deliveryHealth: 91, hoursLogged: 248, teamAvailability: 46 }, projects, meetings, milestones, activity, team, actionItems, decisions }
export default dashboardData
