import api from "./client";

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string | null;
  category: string | null;
  total_copies: number;
  available_copies: number;
  shelf_location: string | null;
  publisher: string | null;
  year: string | null;
  is_active: number;
}

export interface Loan {
  id: number;
  book_id: number;
  book_title: string;
  borrower_id: number;
  borrower_type: string;  // student | teacher
  borrower_name: string;
  issue_date: string;
  due_date: string;
  return_date: string | null;
  status: string;  // active | returned
}

export const getBooks = (search = "", category = "", available_only = false) =>
  api.get<Book[]>("/library/books", { params: { search, category, available_only } }).then((r) => r.data);

export const getCategories = () =>
  api.get<string[]>("/library/books/categories").then((r) => r.data);

export const getBook = (id: number) =>
  api.get<Book>(`/library/books/${id}`).then((r) => r.data);

export const createBook = (body: { title: string; author?: string | null; isbn?: string | null; category?: string | null; total_copies?: number; shelf_location?: string | null; publisher?: string | null; year?: string | null }) =>
  api.post<Book>("/library/books", body).then((r) => r.data);

export const getLoans = (status?: string) =>
  api.get<Loan[]>("/library/loans", { params: { status } }).then((r) => r.data);

export const checkoutBook = (book_id: number, borrower_id: number, due_date: string, borrower_type = "student") =>
  api.post("/library/checkout", { book_id, borrower_id, borrower_type, due_date }).then((r) => r.data);

export const returnBook = (loan_id: number) =>
  api.post(`/library/return/${loan_id}`).then((r) => r.data);

export const getLibraryStats = () =>
  api.get("/library/stats").then((r) => r.data);
