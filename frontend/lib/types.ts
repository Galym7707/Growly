export type Report = {
  id: number;
  type: string | null;
  title: string | null;
  body: string | null;
  summary: string | null;
  query: string | null;
  sources_count: number;
  evidence: unknown[];
  recommendations: unknown[];
  structure: Record<string, unknown>;
  week_start: string | null;
  week_end: string | null;
  status: string;
  notion_synced: boolean;
  notion_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Draft = {
  id: number;
  content_plan_id: number | null;
  type: string | null;
  channel: string | null;
  title: string | null;
  text: string;
  version: number;
  status: string;
  approved_by: string | null;
  metadata: Record<string, unknown>;
  notion_synced: boolean;
  notion_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Source = {
  id: number;
  name: string;
  type: string | null;
  url: string | null;
  category: string | null;
  priority: string;
  frequency: string;
  status: string;
  notes: string | null;
  last_checked_at: string | null;
  notion_synced: boolean;
  created_at: string;
};

export type ContentPlanItem = {
  id: number;
  publish_date: string | null;
  channel: string | null;
  content_type: string | null;
  topic: string | null;
  goal: string | null;
  target_audience: string | null;
  key_message: string | null;
  cta: string | null;
  source_idea: string | null;
  why_recommended: string | null;
  status: string;
  draft_id?: number | null;
  notion_synced: boolean;
  created_at: string;
  updated_at: string;
};

export type ContentPlanSource = {
  report_id: number;
  report_title: string | null;
  sources_count: number;
  created_at: string | null;
  language: string | null;
  notion_synced: boolean;
  notion_url: string | null;
};

export type ContentPlanResponse = {
  plan_id?: number | string | null;
  content_plan_id?: number | string | null;
  items: ContentPlanItem[];
  source?: ContentPlanSource | null;
};

export type ContentPlanOption = {
  label: string;
  value: string;
};

export type ContentPlanOptions = {
  goals: ContentPlanOption[];
  audiences: ContentPlanOption[];
  offers: ContentPlanOption[];
  channels: ContentPlanOption[];
  content_types: ContentPlanOption[];
  ctas: ContentPlanOption[];
};

export type DashboardData = {
  workspace_mode: "single";
  latest_market_scan: Report | null;
  latest_competitor_report: Report | null;
  latest_content_plan: ContentPlanItem | null;
  drafts_waiting: Draft[];
  counts: {
    pending_drafts: number;
    active_sources: number;
    published: number;
  };
  notion: {
    configured: boolean;
    last_synced_at: string | null;
  };
};
