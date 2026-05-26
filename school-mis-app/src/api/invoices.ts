import api from "./client";

export type InvoiceStatus = "draft" | "approved" | "partially_paid" | "paid" | "cancelled" | "voided";

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  bill_id: number | null;
  fee_type_id: number | null;
  fee_type_name: string | null;
  description: string;
  amount: number;
  discount_amount: number;
  quantity: number;
  line_total: number;
}

export interface Invoice {
  id: number;
  invoice_no: string;
  student_id: number;
  student_name: string;
  admission_no: string;
  class_name: string | null;
  academic_year_id: number | null;
  term: number | null;
  status: InvoiceStatus;
  total_amount: number;
  paid_amount: number;
  discount_amount: number;
  control_number: string | null;
  control_number_expires_at: string | null;
  control_number_issued_at: string | null;
  notes: string | null;
  created_by: number | null;
  created_by_name: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  voided_at: string | null;
  void_reason: string | null;
  created_at: string;
  updated_at: string;
  items?: InvoiceItem[];
  audit?: AuditEntry[];
}

export interface AuditEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  actor_id: number | null;
  actor_name: string | null;
  before_json: string | null;
  after_json: string | null;
  detail: string | null;
  created_at: string;
}

export interface CreateInvoiceItemIn {
  bill_id?: number | null;
  fee_type_id?: number | null;
  description: string;
  amount: number;
  discount_amount?: number;
  quantity?: number;
}

export const getInvoices = (params?: {
  student_id?: number;
  academic_year_id?: number;
  status?: InvoiceStatus;
  limit?: number;
}) => api.get<Invoice[]>("/invoices", { params }).then((r) => r.data);

export const getInvoice = (id: number) =>
  api.get<Invoice>(`/invoices/${id}`).then((r) => r.data);

export const createInvoice = (body: {
  student_id: number;
  academic_year_id?: number | null;
  term?: number | null;
  items: CreateInvoiceItemIn[];
  notes?: string;
}) => api.post<{ id: number; invoice_no: string; total_amount: number; status: string }>("/invoices", body).then((r) => r.data);

export const approveInvoice = (id: number) =>
  api.post(`/invoices/${id}/approve`).then((r) => r.data);

export const issueControlNumber = (id: number, expires_days = 30) =>
  api.post<{ ok: boolean; control_number: string; expires_at: string; already_issued?: boolean }>(
    `/invoices/${id}/issue-control-number`,
    { expires_days }
  ).then((r) => r.data);

export const payInvoice = (
  id: number,
  body: {
    control_number: string;
    amount: number;
    payment_date: string;
    method?: string;
    reference_no?: string;
    notes?: string;
  }
) => api.post(`/invoices/${id}/pay`, body).then((r) => r.data);

export const voidInvoice = (id: number, reason: string) =>
  api.post(`/invoices/${id}/void`, { reason }).then((r) => r.data);

export const getInvoiceAudit = (id: number) =>
  api.get<AuditEntry[]>(`/invoices/${id}/audit`).then((r) => r.data);
