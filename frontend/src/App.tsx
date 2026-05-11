import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  CalendarClock,
  Car,
  CheckCircle2,
  ChevronRight,
  Clock,
  Gauge,
  LayoutDashboard,
  MessageSquareText,
  RefreshCw,
  Route,
  Search,
  Send,
  Settings,
  Sparkles,
  UserRoundCheck,
  UsersRound,
  Workflow
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from './api';
import type { Appointment, DashboardOverview, Lead, ScoreBreakdown, Sequence, TimelineItem, WorkerConfig } from './types';

type View = 'dashboard' | 'leads' | 'nurture' | 'appointments' | 'event-simulator' | 'reply-lab' | 'settings';

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard },
  { id: 'leads', label: 'Lead Inbox', icon: UsersRound },
  { id: 'nurture', label: 'Nurture Sequences', icon: Workflow },
  { id: 'appointments', label: 'Appointments', icon: CalendarClock },
  { id: 'event-simulator', label: 'Lead Event Simulator', icon: Activity },
  { id: 'reply-lab', label: 'AI Reply Lab', icon: MessageSquareText },
  { id: 'settings', label: 'Runtime Settings', icon: Settings }
];

const sampleLead = {
  source_channel: 'website_form',
  first_name: 'Anshul',
  last_name: 'Simhadri',
  email: 'anshul.demo@example.com',
  phone: '+919999999999',
  vehicle_interest: 'Hyundai Creta SX',
  message: 'Can I schedule a test drive today and discuss finance options?',
  customer_location: 'Hyderabad',
  intent_signals: {
    page_views: 7,
    vehicle_page_time_seconds: 360,
    chat_interactions: 3,
    financing_inquiries: 1,
    trade_in_requests: 0,
    test_drive_interest: true
  }
};

const sampleEvent = {
  action: 'TRACK_EVENT',
  sessionId: 'demo-session-001',
  eventType: 'INVENTORY_DWELL_TIME',
  data: {
    durationSeconds: 240,
    VehicleName: 'Hyundai Creta SX',
    Message: 'Still available? I want a test drive this week.'
  }
};

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function metricValue(metrics: Record<string, string | number> | undefined, key: string, fallback: string | number = '—') {
  return metrics?.[key] ?? fallback;
}

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [workers, setWorkers] = useState<WorkerConfig[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [scoreBreakdown, setScoreBreakdown] = useState<ScoreBreakdown | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function refreshData() {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, leadsRes, sequencesRes, appointmentsRes, workersRes] = await Promise.all([
        api.overview().catch(() => null),
        api.leads(),
        api.sequences().catch(() => [] as Sequence[]),
        api.appointments().catch(() => [] as Appointment[]),
        api.workers().catch(() => [] as WorkerConfig[])
      ]);
      setOverview(overviewRes);
      setLeads(leadsRes);
      setSequences(sequencesRes);
      setAppointments(appointmentsRes);
      setWorkers(workersRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load backend data.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshData();
  }, []);

  async function openLead(lead: Lead) {
    setSelectedLead(lead);
    setTimeline([]);
    setScoreBreakdown(null);
    try {
      const [timelineRes, scoreRes] = await Promise.all([
        api.timeline(lead.public_id),
        api.scoreBreakdown(lead.public_id)
      ]);
      setTimeline(timelineRes);
      setScoreBreakdown(scoreRes);
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Could not load lead details.');
    }
  }

  const filteredLeads = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return leads;
    return leads.filter((lead) =>
      [lead.first_name, lead.last_name, lead.email, lead.phone, lead.vehicle_interest, lead.temperature, lead.urgency, lead.status, lead.assigned_rep]
        .join(' ')
        .toLowerCase()
        .includes(term)
    );
  }, [leads, query]);

  const hotLeads = leads.filter((lead) => lead.temperature === 'Hot').length;
  const openSla = leads.filter((lead) => !lead.first_response_at && ['Open', 'Working', 'Escalated'].includes(lead.status)).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Bot size={22} /></div>
          <div>
            <strong>[YourBrand] Auto</strong>
            <span>Sales AI Workers</span>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.id} className={classNames('nav-item', view === item.id && 'active')} onClick={() => setView(item.id)}>
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-card">
          <span>Backend</span>
          <strong>{api.meta.API_BASE_URL}</strong>
          <small>Dealership: {api.meta.DEALERSHIP_ID}</small>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Sales Digital Workers</p>
            <h1>{navItems.find((item) => item.id === view)?.label}</h1>
          </div>
          <div className="topbar-actions">
            {loading && <span className="syncing"><RefreshCw size={15} className="spin" /> Syncing</span>}
            <button className="secondary" onClick={refreshData}><RefreshCw size={16} /> Refresh</button>
            <button className="primary" onClick={() => setView('event-simulator')}><Sparkles size={16} /> Simulate Intent</button>
          </div>
        </header>

        {error && <div className="alert"><AlertTriangle size={18} /> {error}</div>}
        {toast && <button className="toast" onClick={() => setToast(null)}>{toast}</button>}

        {view === 'dashboard' && <DashboardView overview={overview} leads={leads} hotLeads={hotLeads} openSla={openSla} sequences={sequences} appointments={appointments} onOpenLead={openLead} />}
        {view === 'leads' && <LeadsView leads={filteredLeads} query={query} onQuery={setQuery} onOpenLead={openLead} onRefresh={refreshData} />}
        {view === 'nurture' && <NurtureView sequences={sequences} />}
        {view === 'appointments' && <AppointmentsView appointments={appointments} onRefresh={refreshData} />}
        {view === 'event-simulator' && <EventSimulator onDone={refreshData} setToast={setToast} />}
        {view === 'reply-lab' && <ReplyLab leads={leads} onDone={refreshData} setToast={setToast} />}
        {view === 'settings' && <SettingsView workers={workers} />}
      </main>

      {selectedLead && (
        <LeadDrawer
          lead={selectedLead}
          timeline={timeline}
          scoreBreakdown={scoreBreakdown}
          onClose={() => setSelectedLead(null)}
          onDone={async () => {
            await refreshData();
            const latest = leads.find((lead) => lead.public_id === selectedLead.public_id) || selectedLead;
            await openLead(latest);
          }}
          setToast={setToast}
        />
      )}
    </div>
  );
}

function DashboardView({ overview, leads, hotLeads, openSla, sequences, appointments, onOpenLead }: {
  overview: DashboardOverview | null;
  leads: Lead[];
  hotLeads: number;
  openSla: number;
  sequences: Sequence[];
  appointments: Appointment[];
  onOpenLead: (lead: Lead) => void;
}) {
  const tempData = overview?.charts?.temperature?.length ? overview.charts.temperature : [
    { name: 'Hot', value: leads.filter((lead) => lead.temperature === 'Hot').length },
    { name: 'Warm', value: leads.filter((lead) => lead.temperature === 'Warm').length },
    { name: 'Cold', value: leads.filter((lead) => lead.temperature === 'Cold').length }
  ];
  const channelData = overview?.charts?.lead_channels || [];
  const topLeads = [...leads].sort((a, b) => b.score - a.score).slice(0, 6);

  return (
    <section className="page-stack">
      <div className="metric-grid">
        <MetricCard icon={UsersRound} label="Leads Processed" value={metricValue(overview?.lead_metrics, 'leads_processed', leads.length)} tone="blue" />
        <MetricCard icon={Gauge} label="Hot Leads" value={hotLeads} tone="orange" />
        <MetricCard icon={Clock} label="Pending Response" value={metricValue(overview?.lead_metrics, 'pending_response', openSla)} tone="red" />
        <MetricCard icon={CalendarClock} label="Appointments" value={appointments.length} tone="green" />
      </div>

      <div className="grid-2">
        <Panel title="Lead Temperature Mix" icon={Gauge}>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={tempData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={92} paddingAngle={5}>
                  {tempData.map((_, index) => <Cell key={index} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Lead Capture Channels" icon={Route}>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={channelData.length ? channelData : [{ name: 'No data', value: 0 }]}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid-2 align-start">
        <Panel title="Top Priority Leads" icon={Sparkles}>
          <div className="lead-list compact">
            {topLeads.map((lead) => <LeadRow key={lead.public_id} lead={lead} onOpen={() => onOpenLead(lead)} />)}
            {!topLeads.length && <EmptyState title="No leads yet" body="Create a lead or send a lead event to populate this board." />}
          </div>
        </Panel>
        <Panel title="QA Progress / Worker Coverage" icon={CheckCircle2}>
          <div className="qa-grid">
            {(overview?.qa_progress || [
              { agent: 'AI Lead Qualification & Routing', status: 'Partial Complete', priority: 'High' },
              { agent: 'Follow-Up & Nurture', status: 'Backend Partial', priority: 'High' },
              { agent: 'Appointment Scheduling', status: 'Backend Partial', priority: 'High' },
              { agent: 'React Frontend', status: 'Added', priority: 'High' }
            ]).map((item) => (
              <div className="qa-card" key={item.agent}>
                <strong>{item.agent}</strong>
                <span>{item.status}</span>
                <small>{item.priority} priority</small>
              </div>
            ))}
          </div>
          <div className="mini-metrics">
            <span>{sequences.length} sequences</span>
            <span>{appointments.filter((a) => a.status === 'Confirmed').length} confirmed appointments</span>
            <span>{metricValue(overview?.lead_metrics, 'conversion_rate', '0%')} conversion</span>
          </div>
        </Panel>
      </div>
    </section>
  );
}

function LeadsView({ leads, query, onQuery, onOpenLead, onRefresh }: {
  leads: Lead[];
  query: string;
  onQuery: (value: string) => void;
  onOpenLead: (lead: Lead) => void;
  onRefresh: () => void;
}) {
  const [form, setForm] = useState(JSON.stringify(sampleLead, null, 2));
  const [busy, setBusy] = useState(false);

  async function createLead() {
    setBusy(true);
    try {
      await api.createLead(JSON.parse(form));
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <div className="toolbar">
        <div className="search-box"><Search size={16} /><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search lead, vehicle, rep, status..." /></div>
        <span className="chip">{leads.length} visible leads</span>
      </div>
      <div className="grid-2 align-start wide-left">
        <Panel title="Live Lead Inbox" icon={UsersRound}>
          <div className="lead-list">
            {leads.map((lead) => <LeadRow key={lead.public_id} lead={lead} onOpen={() => onOpenLead(lead)} />)}
            {!leads.length && <EmptyState title="No matching leads" body="Try a different search or create a test lead." />}
          </div>
        </Panel>
        <Panel title="Create Lead" icon={UserRoundCheck}>
          <p className="muted">Use this to test Agent-1 lead scoring, dedupe, routing and nurture sequence creation.</p>
          <textarea className="json-editor" value={form} onChange={(event) => setForm(event.target.value)} />
          <button className="primary full" disabled={busy} onClick={createLead}><Send size={16} /> {busy ? 'Creating...' : 'Create Lead'}</button>
        </Panel>
      </div>
    </section>
  );
}

function NurtureView({ sequences }: { sequences: Sequence[] }) {
  return (
    <section className="page-stack">
      <Panel title="Follow-Up & Nurture Agent" icon={Workflow}>
        <div className="sequence-grid">
          {sequences.map((sequence) => (
            <div className="sequence-card" key={sequence.public_id}>
              <div className="sequence-head">
                <div>
                  <strong>{sequence.name}</strong>
                  <span>{sequence.lead_name}</span>
                </div>
                <Badge value={sequence.status} />
              </div>
              <div className="progress-bar"><span style={{ width: `${Math.min(100, (sequence.current_step / Math.max(sequence.total_steps, 1)) * 100)}%` }} /></div>
              <div className="sequence-meta">
                <span>Channel: {sequence.channel}</span>
                <span>Step {sequence.current_step}/{sequence.total_steps}</span>
                <span>{sequence.engagement} engagement</span>
              </div>
              <p>{sequence.next_step}</p>
              {sequence.paused_reason && <small className="warning">Paused: {sequence.paused_reason}</small>}
            </div>
          ))}
          {!sequences.length && <EmptyState title="No sequences yet" body="Sequences are created automatically when leads are captured." />}
        </div>
      </Panel>
    </section>
  );
}

function AppointmentsView({ appointments, onRefresh }: { appointments: Appointment[]; onRefresh: () => void }) {
  async function updateAttendance(id: string, status: 'show' | 'no_show') {
    if (status === 'show') await api.markShow(id);
    else await api.markNoShow(id);
    await onRefresh();
  }

  return (
    <section className="page-stack">
      <Panel title="Appointment Scheduling & Test Drive Orchestrator" icon={CalendarClock}>
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Appointment</th>
                <th>Lead</th>
                <th>Vehicle</th>
                <th>When</th>
                <th>Status</th>
                <th>Attendance</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((appointment) => (
                <tr key={appointment.public_id}>
                  <td>{appointment.public_id}</td>
                  <td>{appointment.lead_id}</td>
                  <td>{appointment.vehicle_id}<small>{appointment.vehicle_location}</small></td>
                  <td>{formatDate(appointment.start_time)}</td>
                  <td><Badge value={appointment.status} /></td>
                  <td>{appointment.attendance_status}</td>
                  <td className="table-actions">
                    <button className="ghost" onClick={() => updateAttendance(appointment.public_id, 'show')}>Show</button>
                    <button className="ghost danger" onClick={() => updateAttendance(appointment.public_id, 'no_show')}>No-show</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!appointments.length && <EmptyState title="No appointments" body="Book a test drive through the API or lead workflow." />}
        </div>
      </Panel>
    </section>
  );
}

function EventSimulator({ onDone, setToast }: { onDone: () => Promise<void>; setToast: (value: string | null) => void }) {
  const [payload, setPayload] = useState(JSON.stringify(sampleEvent, null, 2));
  const [result, setResult] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      const response = await api.leadEvent(JSON.parse(payload));
      setResult(JSON.stringify(response, null, 2));
      await onDone();
      setToast('Lead event processed successfully.');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Failed to process event.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <Panel title="Unified Lead Event API" icon={Activity}>
        <p className="muted">Test anonymous event tracking or CREATE_LEAD payloads. Anonymous events now replay into the final lead when contact details are submitted.</p>
        <div className="grid-2 align-start">
          <textarea className="json-editor tall" value={payload} onChange={(event) => setPayload(event.target.value)} />
          <pre className="result-box">{result || 'Response will appear here...'}</pre>
        </div>
        <button className="primary" disabled={busy} onClick={submit}><Send size={16} /> {busy ? 'Processing...' : 'Process Event'}</button>
      </Panel>
    </section>
  );
}

function ReplyLab({ leads, onDone, setToast }: { leads: Lead[]; onDone: () => Promise<void>; setToast: (value: string | null) => void }) {
  const [leadId, setLeadId] = useState(leads[0]?.public_id || '');
  const [message, setMessage] = useState('Can I come tomorrow evening for a test drive?');
  const [reply, setReply] = useState('');

  useEffect(() => {
    if (!leadId && leads[0]?.public_id) setLeadId(leads[0].public_id);
  }, [leads, leadId]);

  async function generate() {
    const response = await api.aiReply({ lead_id: leadId || undefined, message });
    setReply(response.reply);
  }

  async function registerResponse() {
    if (!leadId || !reply) return;
    await api.respondToLead(leadId, { channel: 'email', message: reply });
    await onDone();
    setToast('Agent response registered and response-time SLA updated.');
  }

  return (
    <section className="page-stack">
      <Panel title="AI Response Generation" icon={MessageSquareText}>
        <div className="form-grid">
          <label>Lead Context<select value={leadId} onChange={(event) => setLeadId(event.target.value)}><option value="">Generic / no lead context</option>{leads.map((lead) => <option key={lead.public_id} value={lead.public_id}>{lead.first_name} {lead.last_name} · {lead.vehicle_interest}</option>)}</select></label>
          <label>Customer Message<textarea value={message} onChange={(event) => setMessage(event.target.value)} /></label>
        </div>
        <div className="button-row"><button className="primary" onClick={generate}><Sparkles size={16} /> Generate Reply</button><button className="secondary" disabled={!reply || !leadId} onClick={registerResponse}>Register Response</button></div>
        {reply && <div className="reply-box"><strong>Suggested reply</strong><p>{reply}</p></div>}
      </Panel>
    </section>
  );
}

function SettingsView({ workers }: { workers: WorkerConfig[] }) {
  return (
    <section className="page-stack">
      <Panel title="Worker Configuration" icon={Settings}>
        <div className="worker-grid">
          {workers.map((worker) => (
            <div className="worker-card" key={worker.worker_key}>
              <div className="worker-icon"><Bot size={22} /></div>
              <strong>{worker.name}</strong>
              <Badge value={worker.status} />
              <span>{worker.tagline}</span>
              <p>{worker.description}</p>
            </div>
          ))}
          {!workers.length && <EmptyState title="No workers loaded" body="Start the FastAPI backend and refresh this page." />}
        </div>
      </Panel>
    </section>
  );
}

function LeadDrawer({ lead, timeline, scoreBreakdown, onClose, onDone, setToast }: {
  lead: Lead;
  timeline: TimelineItem[];
  scoreBreakdown: ScoreBreakdown | null;
  onClose: () => void;
  onDone: () => void;
  setToast: (value: string | null) => void;
}) {
  const [repName, setRepName] = useState(lead.assigned_rep || '');
  const [repId, setRepId] = useState('REP-MANUAL');

  async function assign() {
    await api.assignLead(lead.public_id, { rep_id: repId, rep_name: repName });
    setToast('Lead assignment updated.');
    await onDone();
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <button className="drawer-close" onClick={onClose}>×</button>
        <div className="drawer-header">
          <Badge value={lead.temperature} />
          <h2>{lead.first_name} {lead.last_name}</h2>
          <p>{lead.vehicle_interest}</p>
        </div>
        <div className="score-hero">
          <div><span>Lead Score</span><strong>{lead.score}</strong></div>
          <div><span>Urgency</span><strong>{lead.urgency}</strong></div>
          <div><span>Status</span><strong>{lead.status}</strong></div>
        </div>
        <div className="drawer-section">
          <h3>Next best action</h3>
          <p>{lead.next_action}</p>
        </div>
        <div className="drawer-section">
          <h3>Assign / Reassign</h3>
          <div className="inline-fields"><input value={repId} onChange={(event) => setRepId(event.target.value)} /><input value={repName} onChange={(event) => setRepName(event.target.value)} /><button className="secondary" onClick={assign}>Save</button></div>
        </div>
        {scoreBreakdown && (
          <div className="drawer-section">
            <h3>Score breakdown</h3>
            <div className="component-grid">
              {Object.entries(scoreBreakdown.components).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{String(value)}</strong></div>)}
            </div>
            <ul className="reason-list">{scoreBreakdown.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          </div>
        )}
        <div className="drawer-section">
          <h3>Timeline</h3>
          <div className="timeline">
            {timeline.map((item, index) => (
              <div className="timeline-item" key={`${item.type}-${index}`}>
                <span className="dot" />
                <strong>{item.title}</strong>
                <small>{formatDate(item.timestamp)} · {item.channel || 'system'}</small>
                {item.description && <p>{item.description}</p>}
              </div>
            ))}
            {!timeline.length && <EmptyState title="No timeline yet" body="Events and messages will appear here." />}
          </div>
        </div>
      </aside>
    </div>
  );
}

function LeadRow({ lead, onOpen }: { lead: Lead; onOpen: () => void }) {
  return (
    <button className="lead-row" onClick={onOpen}>
      <div className="avatar">{lead.first_name.slice(0, 1)}{lead.last_name.slice(0, 1)}</div>
      <div className="lead-main">
        <strong>{lead.first_name} {lead.last_name}</strong>
        <span>{lead.vehicle_interest}</span>
        <small>{lead.assigned_rep} · {lead.status}</small>
      </div>
      <div className="lead-score"><strong>{lead.score}</strong><Badge value={lead.temperature} /></div>
      <ChevronRight size={18} />
    </button>
  );
}

function MetricCard({ icon: Icon, label, value, tone }: { icon: typeof LayoutDashboard; label: string; value: string | number; tone: string }) {
  return (
    <div className={classNames('metric-card', `tone-${tone}`)}>
      <div className="metric-icon"><Icon size={20} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof LayoutDashboard; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-head"><div><Icon size={18} /><h2>{title}</h2></div></div>
      {children}
    </section>
  );
}

function Badge({ value }: { value: string }) {
  const lowered = value.toLowerCase();
  return <span className={classNames('badge', lowered.includes('hot') && 'hot', lowered.includes('warm') && 'warm', lowered.includes('cold') && 'cold', lowered.includes('escalated') && 'danger')}>{value}</span>;
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return <div className="empty"><Car size={28} /><strong>{title}</strong><span>{body}</span></div>;
}
