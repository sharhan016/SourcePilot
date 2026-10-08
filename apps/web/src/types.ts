export type Workflow = {
  id: string;
  status: "queued" | "running" | "waiting" | "completed" | "failed" | "cancelled";
  current_stage: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
};

export type CompanyContext = {
  company_name: string;
  company_location: string;
  country: string;
  currency: string;
  procurement_region: string;
  sourcing_regions: string[];
};

export type ProcurementRequest = {
  id: string;
  original_request: string;
  normalized_requirements: Record<string, unknown>;
  status: string;
  company_name: string;
  company_location: string;
  created_at: string;
  updated_at: string;
  workflow: Workflow;
};

export type Product = {
  id: string;
  name: string;
  manufacturer: string | null;
  model: string | null;
  specifications: Record<string, unknown>;
  unit_price: string | null;
  currency: string | null;
  available_quantity: number | null;
  availability: string | null;
  warranty: string | null;
  delivery: string | null;
  source_url: string;
  verification_status: string;
};

export type Supplier = {
  id: string;
  name: string;
  website: string;
  location: string | null;
  supplier_type: string | null;
  verification_status: string;
  products: Product[];
};

export type Recommendation = {
  id: string;
  selected_options: Array<Record<string, string | boolean | null>>;
  evaluation_results: Array<Record<string, string | boolean | null>>;
  total_cost: string | null;
  currency: string | null;
  reasoning_summary: string;
  evidence_references: string[];
  status: "ready" | "approved" | "rejected";
  review_note: string | null;
};

export type RequestDetail = ProcurementRequest & {
  suppliers: Supplier[];
  recommendation: Recommendation | null;
};

export type WorkflowTask = {
  id: string;
  agent_type: string;
  task_type: string;
  status: string;
  dependencies: string[];
  retry_count: number;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type ExecutionEvent = {
  id: string;
  task_id: string | null;
  agent: string;
  event_type: string;
  capability: string | null;
  provider: string | null;
  status: string;
  duration_ms: number | null;
  metadata_json: Record<string, unknown>;
  timestamp: string;
};

export type Execution = { workflow: Workflow; tasks: WorkflowTask[]; events: ExecutionEvent[] };
