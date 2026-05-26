import api from "./client";

export interface InventoryItem {
  id: number;
  name: string;
  item_type: "consumable" | "asset";
  main_category: string;
  subcategory: string;
  unit: string;
  unit_price: number;
  quantity: number;
  reorder_qty: number;
  location: string;
  status: string;
  is_active: number;
}

export interface InventoryStats {
  total_items: number;
  low_stock_count: number;
  stock_value: number;
  pending_requests: number;
  today_movements: number;
}

export interface InventoryTransaction {
  id: number;
  item_id: number;
  item_name: string;
  item_unit: string;
  type: "stock_in" | "issued" | "adjusted" | "returned";
  qty: number;
  supplier: string | null;
  unit_cost: number | null;
  issued_to: string | null;
  department: string | null;
  reference: string | null;
  notes: string | null;
  recorded_by_name: string | null;
  created_at: string;
}

export interface InventoryRequest {
  id: number;
  item_id: number;
  item_name: string;
  unit: string;
  requested_by: number;
  requester_name: string;
  reviewer_name: string | null;
  quantity: number;
  purpose: string | null;
  department: string | null;
  status: "pending" | "approved" | "rejected" | "issued";
  notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface ItemPayload {
  name: string;
  item_type?: string;
  main_category?: string;
  subcategory?: string;
  unit?: string;
  quantity?: number;
  reorder_qty?: number;
  unit_price?: number;
  location?: string;
  status?: string;
}

export interface ReceivePayload {
  item_id: number;
  quantity: number;
  supplier?: string;
  unit_cost?: number;
  reference?: string;
  notes?: string;
}

export interface IssuePayload {
  item_id: number;
  quantity: number;
  issued_to?: string;
  department?: string;
  purpose?: string;
  notes?: string;
}

export interface RequestPayload {
  item_id: number;
  quantity: number;
  purpose?: string;
  department?: string;
  notes?: string;
}

export const getInventoryItems = (search = "", main_category = "", item_type = "", status = "") =>
  api.get<InventoryItem[]>("/inventory/items", { params: { search, main_category, item_type, status } }).then((r) => r.data);

export const getInventoryItem = (id: number) =>
  api.get<InventoryItem>(`/inventory/items/${id}`).then((r) => r.data);

export const getLowStock = () =>
  api.get<InventoryItem[]>("/inventory/low-stock").then((r) => r.data);

export const getInventoryStats = () =>
  api.get<InventoryStats>("/inventory/stats").then((r) => r.data);

export const getCategories = () =>
  api.get<string[]>("/inventory/categories").then((r) => r.data);

export const createItem = (body: ItemPayload) =>
  api.post<InventoryItem>("/inventory/items", body).then((r) => r.data);

export const updateItem = (id: number, body: ItemPayload) =>
  api.put<InventoryItem>(`/inventory/items/${id}`, body).then((r) => r.data);

export const deactivateItem = (id: number) =>
  api.delete(`/inventory/items/${id}`).then((r) => r.data);

export const receiveStock = (body: ReceivePayload) =>
  api.post<InventoryItem>("/inventory/receive", body).then((r) => r.data);

// backward compat alias
export const addStock = (item_id: number, quantity: number, notes = "") =>
  receiveStock({ item_id, quantity, notes });

export const issueStock = (body: IssuePayload) =>
  api.post<InventoryItem>("/inventory/issue", body).then((r) => r.data);

export const doStocktake = (entries: { item_id: number; physical_qty: number }[], notes = "") =>
  api.post("/inventory/stocktake", { entries, notes }).then((r) => r.data);

export const getTransactions = (item_id?: number, type?: string, limit = 100) =>
  api.get<InventoryTransaction[]>("/inventory/transactions", { params: { item_id, type, limit } }).then((r) => r.data);

export const getRequests = (status = "", my_only = false) =>
  api.get<InventoryRequest[]>("/inventory/requests", { params: { status, my_only } }).then((r) => r.data);

export const createRequest = (body: RequestPayload) =>
  api.post<InventoryRequest>("/inventory/requests", body).then((r) => r.data);

export const approveRequest = (id: number, notes = "") =>
  api.post(`/inventory/requests/${id}/approve`, { notes }).then((r) => r.data);

export const rejectRequest = (id: number, notes = "") =>
  api.post(`/inventory/requests/${id}/reject`, { notes }).then((r) => r.data);
