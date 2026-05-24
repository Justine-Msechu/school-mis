import api from "./client";

export interface InventoryItem {
  id: number;
  name: string;
  category: string | null;
  quantity: number;
  unit: string;
  min_quantity: number;
  location: string | null;
  description: string | null;
}

export interface Transaction {
  id: number;
  item_id: number;
  item_name: string;
  transaction_type: string;
  quantity: number;
  notes: string | null;
  created_at: string;
}

export const getInventoryItems = (search = "") =>
  api.get<InventoryItem[]>("/inventory/items", { params: { search } }).then((r) => r.data);

export const getLowStock = () =>
  api.get<InventoryItem[]>("/inventory/low-stock").then((r) => r.data);

export const createItem = (body: Partial<InventoryItem>) =>
  api.post<InventoryItem>("/inventory/items", body).then((r) => r.data);

export const addStock = (item_id: number, quantity: number, notes = "") =>
  api.post("/inventory/add-stock", { item_id, quantity, notes }).then((r) => r.data);

export const issueStock = (item_id: number, quantity: number, notes = "") =>
  api.post("/inventory/issue", { item_id, quantity, notes }).then((r) => r.data);

export const getTransactions = (item_id?: number, limit = 50) =>
  api.get<Transaction[]>("/inventory/transactions", { params: { item_id, limit } }).then((r) => r.data);
