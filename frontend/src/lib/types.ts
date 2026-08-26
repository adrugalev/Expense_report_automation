export type Role = "admin" | "employee";
export type ReportType = "business_trip" | "representative_expenses" | "gifts";
export type BuildMode = "single" | "per_receipt" | "per_receipt_different_companies";
export type ReportStatus = "processing" | "completed" | "failed";
export type ExpenseType = "такси" | "ресторан" | "подарки" | "прочее";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  employee_id: string | null;
}

export interface EmployeeAccount {
  employee_id: string;
  full_name: string;
  email: string | null;
  has_account: boolean;
  is_active: boolean;
  role: Role | null;
}

export interface Employee {
  id: string;
  full_name: string;
  short_name: string | null;
  position: string;
  department: string;
  company: string | null;
  phone: string | null;
  email: string | null;
  manager_name: string | null;
  manager_position: string | null;
  default_signatory_name: string | null;
  default_signatory_position: string | null;
}

export interface Receipt {
  file_name: string;
  date: string | null;
  seller: string | null;
  address: string | null;
  inn: string | null;
  amount: string;
  expense_type: ExpenseType;
  comment: string | null;
  route: string | null;
  fiscal_number: string | null;
  check_number: string | null;
  shift_number: string | null;
  kkt_number: string | null;
  fiscal_document_number: string | null;
  fiscal_drive_number: string | null;
  fiscal_sign: string | null;
  payment_type: string | null;
  qr_raw: string | null;
}

export interface ReceiptUpload {
  id: string;
  original_name: string;
  mime_type: string;
  size: number;
  receipt: Receipt;
  created_at: string;
}

export interface ReportFile {
  id: string;
  name: string;
  mime_type: string;
  size: number;
  download_url: string;
}

export interface ReportSummary {
  id: string;
  report_type: ReportType;
  status: ReportStatus;
  employee_id: string | null;
  employee_name: string | null;
  build_mode: BuildMode;
  total_amount: string;
  created_at: string;
  completed_at: string | null;
  files_count: number;
}

export interface ReportDetail extends ReportSummary {
  input: ReportPayload;
  files: ReportFile[];
  warnings: string[];
  error_message: string | null;
}

export interface ReportList { items: ReportSummary[]; total: number }

export interface DashboardData {
  reports_total: number;
  reports_completed: number;
  reports_failed: number;
  employees_total: number;
  recent_reports: ReportSummary[];
}

export interface ReportTypeOption {
  id: ReportType;
  name: string;
  description: string;
  accepted_expense_type: Exclude<ExpenseType, "прочее">;
}

export interface BaseReportPayload {
  report_type: ReportType;
  employee_id: string;
  report_date: string;
  receipts: Receipt[];
  build_mode: BuildMode;
}

export interface BusinessTripPayload extends BaseReportPayload {
  report_type: "business_trip";
  build_mode: "single";
  trip_city: string;
  trip_start_date: string;
  trip_end_date: string;
  purpose: string;
}

export interface RepresentativePayload extends BaseReportPayload {
  report_type: "representative_expenses";
  event_date: string;
  place: string;
  restaurant_name: string;
  counterparty: string;
  meeting_purpose: string;
  participants_company: string[];
  participants_counterparty: string[];
  meeting_result: string;
}

export interface GiftPayload extends BaseReportPayload {
  report_type: "gifts";
  build_mode: "single";
  purchase_date: string;
  gift_name: string;
  gift_quantity: number;
  unit_price: string;
  recipients: string[];
  counterparty: string;
  occasion: string;
  purpose: string;
}

export type ReportPayload = BusinessTripPayload | RepresentativePayload | GiftPayload;

export interface AppMeta {
  version: string;
  version_date: string;
  version_revision: number;
  history: Array<{ revision: number; date: string; changes: string[] }>;
}
