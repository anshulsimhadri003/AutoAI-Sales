export type Temperature = 'Hot' | 'Warm' | 'Cold' | string;

export interface LeadIntentSignals {
  page_views: number;
  vehicle_page_time_seconds: number;
  chat_interactions: number;
  financing_inquiries: number;
  trade_in_requests: number;
  test_drive_interest: boolean;
}

export interface Lead {
  public_id: string;
  dealership_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  source_channel: string;
  vehicle_interest: string;
  message: string;
  customer_location: string;
  budget_indicator: string;
  intent_signals: LeadIntentSignals;
  semantic_intent: string;
  semantic_intent_similarity: number;
  score: number;
  temperature: Temperature;
  urgency: string;
  assigned_rep: string;
  next_action: string;
  status: string;
  dedup_status: string;
  merged_count: number;
  first_response_at?: string | null;
  sla_due_at: string;
  escalated_at?: string | null;
  created_at: string;
}

export interface Sequence {
  public_id: string;
  dealership_id: string;
  name: string;
  lead_name: string;
  lead_public_id?: string | null;
  channel: string;
  engagement: string;
  status: string;
  next_step: string;
  current_step: number;
  total_steps: number;
  cadence_minutes: number;
  paused_reason?: string | null;
  escalated: boolean;
  conversion_outcome?: string | null;
  next_run_at?: string | null;
}

export interface Appointment {
  public_id: string;
  dealership_id: string;
  lead_id: string;
  vehicle_id: string;
  rep_id: string;
  start_time: string;
  end_time: string;
  channel: string;
  status: string;
  vehicle_location: string;
  vehicle_status: string;
  attendance_status: string;
  created_at: string;
}

export interface WorkerConfig {
  dealership_id: string;
  worker_key: string;
  name: string;
  status: string;
  tagline: string;
  description: string;
}

export interface DashboardOverview {
  lead_metrics: Record<string, string | number>;
  sequence_metrics: Record<string, string | number>;
  appointment_metrics: Record<string, string | number>;
  charts: {
    temperature: Array<{ name: string; value: number }>;
    lead_status: Array<{ name: string; value: number }>;
    lead_channels: Array<{ name: string; value: number }>;
  };
  top_leads: Array<Record<string, string | number>>;
  qa_progress: Array<{ agent: string; status: string; priority: string }>;
}

export interface TimelineItem {
  timestamp?: string | null;
  type: string;
  channel?: string | null;
  title: string;
  description?: string | null;
  metadata: Record<string, unknown>;
}

export interface ScoreBreakdown {
  lead_id: string;
  score: number;
  temperature: string;
  urgency: string;
  semantic_intent: string;
  components: Record<string, number | string | boolean>;
  reasons: string[];
}
