import api from "./client";

export interface Expense {
  id: number;
  category: string;
  description: string;
  amount: number;
  expense_date: string;
  reference: string;
  vendor: string;
}

export interface AccountingSummary {
  income: number;
  expenses: number;
  net: number;
  period: string;
}

export const getExpenses = (limit = 50) =>
  api.get<Expense[]>("/accounting/expenses", { params: { limit } }).then((r) => r.data);

export const recordExpense = (body: { category: string; description: string; amount: number; expense_date: string; reference?: string; vendor?: string }) =>
  api.post("/accounting/expenses", body).then((r) => r.data);

export const getAccountingSummary = (period = "month") =>
  api.get<AccountingSummary>("/accounting/summary", { params: { period } }).then((r) => r.data);

export const getExpenseCategories = () =>
  api.get<string[]>("/accounting/categories").then((r) => r.data);
