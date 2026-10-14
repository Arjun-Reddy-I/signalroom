'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Archive, BarChart3, Bell, CalendarDays, Check, ChevronRight, FileText, Grid2X2, Menu, Plus, Search, Settings2, Sparkles, UsersRound, X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { ThemeToggle } from '@/components/signalroom/theme-toggle'
import { MeetingDialog } from '@/components/signalroom/dialogs/MeetingDialog'
import { ProjectDialog } from '@/components/signalroom/dialogs/ProjectDialog'
import { SearchOverlay } from '@/components/signalroom/SearchOverlay'
import { AnalyticsView } from '@/components/signalroom/views/AnalyticsView'
import { ArchiveView } from '@/components/signalroom/views/ArchiveView'
import { CalendarView } from '@/components/signalroom/views/CalendarView'
import { SettingsView } from '@/components/signalroom/views/SettingsView'
import { TeamView } from '@/components/signalroom/views/TeamView'
import { createProjectRequest, updateActionItemRequest } from '@/lib/api/workspace'
import { formatDateLong, getDateRangeLabel, getGreeting, getMeetingStatusTone, getStatusLabel, initialsTone, isActionDone, projectStatusTone, type DashboardData, type Meeting, type NewProjectInput, type Project, type ToastState, type ViewName } from '@/types/signalroom'

const navigation: { label: ViewName; icon: typeof Grid2X2 }[] = [
  { label: 'Overview', icon: Grid2X2 }, { label: 'Meetings', icon: CalendarDays }, { label: 'Action Items', icon: Check },
  { label: 'Calendar', icon: CalendarDays }, { label: 'Team', icon: UsersRound }, { label: 'Search', icon: Search },
  { label: 'Analytics', icon: BarChart3 }, { label: 'Archive', icon: Archive }, { label: 'Settings', icon: Settings2 },
]

const viewSlugs: Record<ViewName, string> = {
  Overview: '', Meetings: 'meetings', 'Action Items': 'action-items', Calendar: 'calendar', Team: 'team', Search: 'search', Analytics: 'analytics', Archive: 'archive', Settings: 'settings',
}
const slugViews: Record<string, ViewName> = Object.fromEntries(Object.entries(viewSlugs).map(([view, slug]) => [slug, view])) as Record<string, ViewName>

function Avatar({ initials, tone = 'blue' }: { initials: string; tone?: string }) { return <span className={`avatar ${initialsTone(tone)}`}>{initials}</span> }
function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) { return <section className={`panel ${className}`}>{children}</section> }
function EmptyState({ title, copy }: { title: string; copy: string }) { return <div className="empty-state"><Sparkles /><strong>{title}</strong><span>{copy}</span></div> }

function Sidebar({ active, onChange, open, onClose }: { active: ViewName; onChange: (view: ViewName) => void; open: boolean; onClose: () => void }) {
  return <><aside className={`sidebar ${open ? 'sidebar-open' : ''}`}><div className="brand"><span className="brand-mark">S</span><span>Signalroom</span><button className="icon-button mobile-close" aria-label="Close navigation" onClick={onClose}><X /></button></div><div className="workspace-switcher"><span className="workspace-avatar">NS</span><span><strong>Northstar Studio</strong><small>Meeting intelligence</small></span><ChevronRight /></div><nav aria-label="Primary navigation"><span className="nav-label">Workspace</span>{navigation.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${active === label ? 'nav-active' : ''}`} onClick={() => { onChange(label); onClose() }}><Icon /><span>{label}</span></button>)}</nav><div className="sidebar-version">SIGNALROOM <span>v0.9.0</span></div></aside>{open && <button className="scrim" aria-label="Close navigation" onClick={onClose} />}</>
}

function Topbar({ active, userName, userInitials, onMenu, onSearch, onNotify }: { active: ViewName; userName: string; userInitials: string; onMenu: () => void; onSearch: () => void; onNotify: () => void }) {
  return <header className="topbar"><button className="icon-button menu-button" aria-label="Toggle navigation" onClick={onMenu}><Menu /></button><div className="breadcrumb"><span>Northstar Studio</span><ChevronRight /><strong>{active}</strong></div><div className="top-actions"><ThemeToggle /><button className="top-search-trigger" onClick={onSearch}><Search /><span>Search workspace</span><kbd>Ctrl K</kbd></button><button className="icon-button notification" aria-label="Notifications" onClick={onNotify}><Bell /></button><button className="profile" onClick={onNotify}><Avatar initials={userInitials} /><span>{userName}</span></button></div></header>
}

function ProjectRow({ project, onOpen }: { project: Project; onOpen: () => void }) {
  return <article className="project-row"><div className="project-main"><span className="project-code">{project.id.slice(0, 8).toUpperCase()}</span><h3>{project.name}</h3><p>{project.client}</p></div><div className="project-phase"><span className="eyebrow">Phase</span><strong>{project.phase}</strong></div><div className="project-progress"><div className="progress-meta"><span>Progress</span><strong>{project.progress ? `${project.progress}%` : 'Not tracked'}</strong></div><div className="progress-track"><span style={{ width: `${project.progress}%` }} /></div></div><div className="project-owner"><Avatar initials={project.ownerInitials} tone={project.accent} /><span>{project.owner.split(' ')[0]}</span></div><span className={`status ${projectStatusTone(project.status)}`}><span className="status-dot" />{getStatusLabel(project.status)}</span><button className="row-arrow" aria-label={`Open ${project.name}`} onClick={onOpen}><ChevronRight /></button></article>
}

function StatCard({ label, value, detail, tone = '' }: { label: string; value: string; detail: string; tone?: string }) { return <article className="stat-card"><span className="eyebrow">{label}</span><strong className={`stat-value ${tone}`}>{value}</strong><span className="stat-detail">{detail}</span></article> }

function Overview({ data, projects, userName, onNew, onOpenProject, onOpenMeeting }: { data: DashboardData; projects: Project[]; userName: string; onNew: () => void; onOpenProject: (project: Project) => void; onOpenMeeting: (meeting: Meeting) => void }) {
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const filtered = projects.filter((project) => (filter === 'all' || project.status === filter) && `${project.name} ${project.client} ${project.owner}`.toLowerCase().includes(query.toLowerCase()))
  const openItems = data.actionItems.filter((item) => !isActionDone(item))
  const overdue = openItems.filter((item) => item.dueDate && new Date(item.dueDate) < new Date()).length
  const ready = data.meetings.filter((meeting) => meeting.status === 'Ready').length
  return <motion.div className="view-stack" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}><div className="hero-row"><div><div className="eyebrow hero-eyebrow"><span className="live-dot" /> System nominal <i /> {getDateRangeLabel()}</div><h1>{getGreeting()}, {userName}<span className="title-mark">.</span></h1><p className="hero-copy">Your meeting intelligence, distilled into the next right actions.</p></div><button className="button-primary hero-button" onClick={onNew}><Plus /> New project</button></div><div className="stats-grid"><StatCard label="Meetings indexed" value={`${data.meetings.length}`} detail={`${ready} ready for follow-up`} /><StatCard label="Open action items" value={`${openItems.length}`} detail={`${overdue} overdue`} tone="amber-text" /><StatCard label="Decisions captured" value={`${data.decisions.length}`} detail={data.decisions.length ? 'From connected meetings' : 'No decisions captured'} /><StatCard label="Team availability" value={data.team.length ? `${data.stats.teamAvailability}%` : '—'} detail={data.team.length ? 'Current capacity' : 'No team data'} tone="green-text" /></div><div className="content-grid"><Panel className="pulse-panel"><div className="section-head"><div><span className="eyebrow">Workspace signal</span><h2>Project pulse</h2></div><button className="text-button" onClick={onNew}>New project <Plus /></button></div><div className="pulse-toolbar"><div className="filter-group">{[['all', 'All work'], ['at-risk', 'At risk'], ['in-review', 'In review'], ['on-track', 'On track']].map(([value, label]) => <button key={value} className={filter === value ? 'filter-active' : ''} onClick={() => setFilter(value)}>{label}<span>{value === 'all' ? projects.length : projects.filter((project) => project.status === value).length}</span></button>)}</div><label className="inline-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a project" aria-label="Find a project" /></label></div><div className="project-list"><AnimatePresence>{filtered.map((project) => <ProjectRow key={project.id} project={project} onOpen={() => onOpenProject(project)} />)}</AnimatePresence>{filtered.length === 0 && <EmptyState title="No projects match" copy="Try another search or filter." />}</div></Panel><div className="right-rail"><Panel className="meeting-panel"><div className="section-head"><div><span className="eyebrow">Next up</span><h2>Meeting queue</h2></div><CalendarDays /></div><div className="meeting-mini-list">{data.meetings.slice(0, 4).map((meeting) => <button className="meeting-mini" key={meeting.id} onClick={() => onOpenMeeting(meeting)}><span className={`meeting-dot ${getMeetingStatusTone(meeting.status)}`} /><span><strong>{meeting.title}</strong><small>{meeting.date} / {meeting.time}</small></span><ChevronRight /></button>)}</div></Panel><Panel className="activity-panel"><div className="section-head"><div><span className="eyebrow">Live feed</span><h2>Recent activity</h2></div><Bell /></div><div className="activity-list">{data.activity.slice(0, 4).map((item) => <div className="activity-item" key={item.id}><Avatar initials={item.initials} tone={item.accent} /><p><strong>{item.person}</strong> {item.action} <span>{item.target}</span><small>{item.time}</small></p></div>)}{data.activity.length === 0 && <EmptyState title="No activity yet" copy="Workspace events will appear here." />}</div></Panel></div></div></motion.div>
}

function ViewFrame({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) { return <motion.div className="view-stack" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}><div className="view-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1></div></div>{children}</motion.div> }

function MeetingsView({ data, onSelect }: { data: DashboardData; onSelect: (meeting: Meeting) => void }) { return <ViewFrame eyebrow="Meeting intelligence" title="Meetings"><div className="meeting-grid">{data.meetings.map((meeting) => <button className="meeting-card" key={meeting.id} onClick={() => onSelect(meeting)}><div className="card-top"><span className={`status meeting-status ${getMeetingStatusTone(meeting.status)}`}>{meeting.status}</span><span>{meeting.duration}</span></div><h3>{meeting.title}</h3><p>{meeting.summary}</p><div className="card-foot"><span>{meeting.project}</span><span>{meeting.attendees.length ? `${meeting.attendees.length} participants` : 'Participants unavailable'} <ChevronRight /></span></div></button>)}</div>{data.meetings.length === 0 && <Panel><EmptyState title="No meetings found" copy="Meetings created in the workspace will appear here." /></Panel>}</ViewFrame> }

function ActionItemsView({ data, onToggle }: { data: DashboardData; onToggle: (id: string, status: boolean) => void }) { return <ViewFrame eyebrow="Follow-through" title="Action items"><Panel className="table-panel"><div className="table-head"><span>Task</span><span>Owner</span><span>Due</span><span>Status</span></div>{data.actionItems.map((item) => <div className={`task-row ${isActionDone(item) ? 'task-done' : ''}`} key={item.id}><button className="task-check" aria-label={`Mark ${item.title} complete`} onClick={() => onToggle(item.id, isActionDone(item))}>{isActionDone(item) && <Check />}</button><div><strong>{item.title}</strong><small>{item.source} / {item.project}</small></div><span>{item.owner}</span><span>{item.dueDate ? formatDateLong(item.dueDate) : 'No due date'}</span><span className={`priority ${item.priority.toLowerCase()}`}>{item.status}</span></div>)}{data.actionItems.length === 0 && <EmptyState title="No action items" copy="Follow-up work extracted from meetings will appear here." />}</Panel></ViewFrame> }


export function AppShell({ data }: { data: DashboardData }) {
  const router = useRouter()
  const [active, setActive] = useState<ViewName>('Overview')
  const [drawer, setDrawer] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [projectDialog, setProjectDialog] = useState(false)
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null)
  const [projects, setProjects] = useState(data.projects)
  const [actionItems, setActionItems] = useState(data.actionItems)
  const [toast, setToast] = useState<ToastState | null>(null)
  const [userName, setUserName] = useState('Workspace member')

  useEffect(() => {
    const slug = new URLSearchParams(window.location.search).get('view') ?? ''
    if (slugViews[slug]) setActive(slugViews[slug])
    const saved = window.localStorage.getItem('signalroom-user')
    if (saved) {
      try {
        const user = JSON.parse(saved) as { full_name?: string }
        if (user.full_name) setUserName(user.full_name)
      } catch { /* ignore malformed session metadata */ }
    }
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setProjectDialog(false)
        setSelectedMeeting(null)
        setDrawer(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const projectData = useMemo(() => ({ ...data, actionItems }), [data, actionItems])
  const userInitials = userName.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'WM'
  const notify = (message: string, type: ToastState['type'] = 'info') => {
    setToast({ message, type })
    window.setTimeout(() => setToast(null), 3200)
  }
  const changeView = (view: ViewName) => {
    setActive(view)
    router.push(viewSlugs[view] ? `/?view=${viewSlugs[view]}` : '/')
  }
  const addProject = async (input: NewProjectInput) => {
    try {
      const response = await createProjectRequest(input) as {
        id: string; name: string; client?: string | null
        status: string; owner_id?: string | null; created_at: string
      }
      const project: Project = {
        id: response.id,
        name: response.name,
        client: response.client ?? input.client,
        phase: 'Strategy',
        dueDate: response.created_at.slice(0, 10),
        progress: 0,
        owner: response.owner_id ? `Member ${response.owner_id.slice(0, 8)}` : 'Unassigned',
        ownerInitials: 'NA',
        status: response.status === 'at_risk' ? 'at-risk' : response.status === 'in_review' ? 'in-review' : 'on-track',
        accent: 'amber',
      }
      setProjects((current) => [project, ...current])
      setProjectDialog(false)
      notify(`${project.name} was saved.`, 'success')
    } catch {
      notify('Project could not be saved. Try again.', 'error')
    }
  }
  const toggleAction = async (id: string, wasDone: boolean) => {
    try {
      await updateActionItemRequest(id, { status: wasDone ? 'open' : 'completed' })
      setActionItems((current) =>
        current.map((item) => item.id === id ? { ...item, status: wasDone ? 'Pending' : 'Done' } : item)
      )
      notify('Action item updated.', 'success')
    } catch {
      notify('Action item could not be updated.', 'error')
    }
  }

  function renderView() {
    switch (active) {
      case 'Overview':
        return (
          <Overview
            data={projectData}
            projects={projects}
            userName={userName.split(' ')[0]}
            onNew={() => setProjectDialog(true)}
            onOpenProject={(project) => notify(`${project.name} — open the full detail view to edit.`)}
            onOpenMeeting={setSelectedMeeting}
          />
        )
      case 'Meetings':
        return <MeetingsView data={projectData} onSelect={setSelectedMeeting} />
      case 'Action Items':
        return <ActionItemsView data={projectData} onToggle={toggleAction} />
      case 'Analytics':
        return <AnalyticsView />
      case 'Calendar':
        return <CalendarView />
      case 'Team':
        return <TeamView />
      case 'Archive':
        return <ArchiveView />
      case 'Settings':
        return <SettingsView />
      case 'Search':
        // Trigger the search overlay immediately when navigating to Search
        return (
          <motion.div className="view-stack" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="view-heading">
              <div>
                <span className="eyebrow">Workspace search</span>
                <h1>Search</h1>
              </div>
            </div>
            <section className="panel feature-empty">
              <div className="feature-icon"><Search /></div>
              <h2>Search across all meetings, transcripts, decisions, and tasks.</h2>
              <p>Use the search button in the toolbar or press <kbd>Ctrl+K</kbd> to open the search overlay.</p>
              <button className="button-primary" onClick={() => setSearchOpen(true)}>
                <Search /> Open search
              </button>
            </section>
          </motion.div>
        )
      default:
        return null
    }
  }

  return (
    <div className="app-frame">
      <Sidebar active={active} onChange={changeView} open={drawer} onClose={() => setDrawer(false)} />
      <div className="app-content">
        <Topbar
          active={active}
          userName={userName}
          userInitials={userInitials}
          onMenu={() => setDrawer(true)}
          onSearch={() => setSearchOpen(true)}
          onNotify={() => notify('Notifications are connected to the workspace API.')}
        />
        <main className="main-content">
          {renderView()}
        </main>
      </div>
      <AnimatePresence>
        {projectDialog && (
          <ProjectDialog onClose={() => setProjectDialog(false)} onCreate={(i) => void addProject(i)} />
        )}
        {selectedMeeting && (
          <MeetingDialog meeting={selectedMeeting} onClose={() => setSelectedMeeting(null)} />
        )}
        {searchOpen && (
          <SearchOverlay
            data={projectData}
            onClose={() => setSearchOpen(false)}
            onOpenMeeting={setSelectedMeeting}
          />
        )}
      </AnimatePresence>
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span><Check /></span>
          {toast.message}
          <button aria-label="Dismiss notification" onClick={() => setToast(null)}>
            <X />
          </button>
        </div>
      )}
    </div>
  )
}
