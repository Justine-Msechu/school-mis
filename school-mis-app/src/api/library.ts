import api from "./client";

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string | null;
  category: string | null;
  copies_total: number;
  copies_available: number;
  publisher: string | null;
  published_year: number | null;
  is_active: number;
}

export interface Loan {
  id: number;
  book_id: number;
  book_title: string;
  student_id: number;
  student_name: string;
  admission_no: string;
  issued_at: string;
  due_date: string;
  returned_at: string | null;
}

export interface LibraryStats {
  total_books: number;
  available_books: number;
  active_loans: number;
  overdue_loans: number;
}

export const getBooks = (search = "", category = "", available_only = false) =>
  api.get<Book[]>("/library/books", { params: { search, category, available_only } }).then((r) => r.data);

export const getCategories = () =>
  api.get<string[]>("/library/books/categories").then((r) => r.data);

export const getBook = (id: number) =>
  api.get<Book>(`/library/books/${id}`).then((r) => r.data);

export const createBook = (body: Partial<Book>) =>
  api.post<Book>("/library/books", body).then((r) => r.data);

export const getLoans = (status?: string) =>
  api.get<Loan[]>("/library/loans", { params: { status } }).then((r) => r.data);

export const checkoutBook = (book_id: number, student_id: number, due_date: string) =>
  api.post("/library/checkout", { book_id, student_id, due_date }).then((r) => r.data);

export const returnBook = (loan_id: number) =>
  api.post(`/library/return/${loan_id}`).then((r) => r.data);

export const getLibraryStats = () =>
  api.get<LibraryStats>("/library/stats").then((r) => r.data);
