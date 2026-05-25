import { useState, useEffect, useCallback, useRef } from "react";
import { Search, BookOpen, RotateCcw, Plus, ArrowRightLeft } from "lucide-react";
import { getBooks, getLoans, returnBook, createBook, checkoutBook, type Book, type Loan } from "@/api/library";
import { getStudents } from "@/api/students";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "books" | "loans";

const INPUT = "w-full h-9 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function BookDialog({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({ title: "", author: "", isbn: "", category: "", copies_total: "1", publisher: "", published_year: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.title || !form.author) { setError("Title and author are required."); return; }
    setSaving(true);
    setError("");
    try {
      await createBook({
        title:        form.title,
        author:       form.author       || null,
        isbn:         form.isbn         || null,
        category:     form.category     || null,
        total_copies: Number(form.copies_total) || 1,
        publisher:    form.publisher    || null,
        year:         form.published_year || null,
      });
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to add book.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Add Book</h2>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Field label="Title *"><input className={INPUT} value={form.title} onChange={(e) => set("title", e.target.value)} /></Field></div>
          <div className="col-span-2"><Field label="Author *"><input className={INPUT} value={form.author} onChange={(e) => set("author", e.target.value)} /></Field></div>
          <Field label="ISBN"><input className={INPUT} value={form.isbn} onChange={(e) => set("isbn", e.target.value)} /></Field>
          <Field label="Category"><input className={INPUT} value={form.category} onChange={(e) => set("category", e.target.value)} /></Field>
          <Field label="Copies"><input type="number" min="1" className={INPUT} value={form.copies_total} onChange={(e) => set("copies_total", e.target.value)} /></Field>
          <Field label="Published Year"><input type="number" className={INPUT} value={form.published_year} onChange={(e) => set("published_year", e.target.value)} placeholder="e.g. 2020" /></Field>
          <div className="col-span-2"><Field label="Publisher"><input className={INPUT} value={form.publisher} onChange={(e) => set("publisher", e.target.value)} /></Field></div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Add Book"}</Button>
        </div>
      </div>
    </div>
  );
}

function CheckoutDialog({ book, onSave, onClose }: { book: Book; onSave: () => void; onClose: () => void }) {
  const [form, setForm] = useState({
    admission_no: "",
    student_id:   null as number | null,
    student_name: "",
    due_date:     (() => { const d = new Date(); d.setDate(d.getDate() + 14); return d.toISOString().slice(0, 10); })(),
  });
  const [lookupState, setLookupState] = useState<"idle" | "loading" | "found" | "error">("idle");
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  const lookupStudent = async () => {
    if (!form.admission_no.trim()) return;
    setLookupState("loading");
    try {
      const res = await getStudents({ search: form.admission_no.trim(), per_page: 10 });
      const student = res.items.find((s) => s.admission_no === form.admission_no.trim());
      if (student) {
        setForm((f) => ({ ...f, student_id: student.id, student_name: `${student.first_name} ${student.last_name}` }));
        setLookupState("found");
      } else {
        setForm((f) => ({ ...f, student_id: null, student_name: "" }));
        setLookupState("error");
      }
    } catch {
      setLookupState("error");
    }
  };

  const submit = async () => {
    if (!form.student_id) { setError("Please look up a valid student first."); return; }
    if (!form.due_date)   { setError("Due date is required."); return; }
    setSaving(true);
    setError("");
    try {
      await checkoutBook(book.id, form.student_id!, form.due_date);
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to checkout book.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Checkout Book</h2>
        <p className="text-sm text-gray-500 mb-4">{book.title} — {book.author}</p>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Student Admission No *">
            <div className="flex gap-2">
              <input
                className={INPUT}
                value={form.admission_no}
                placeholder="e.g. ADM001"
                onChange={(e) => {
                  setLookupState("idle");
                  setForm((f) => ({ ...f, admission_no: e.target.value, student_id: null, student_name: "" }));
                }}
                onKeyDown={(e) => e.key === "Enter" && lookupStudent()}
              />
              <Button variant="outline" size="sm" onClick={lookupStudent} disabled={lookupState === "loading"}>
                {lookupState === "loading" ? "…" : "Find"}
              </Button>
            </div>
            {lookupState === "found" && <p className="text-xs text-green-600 mt-1">✓ {form.student_name}</p>}
            {lookupState === "error"  && <p className="text-xs text-red-600 mt-1">Student not found</p>}
          </Field>
          <Field label="Due Date *">
            <input type="date" className={INPUT} value={form.due_date} onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Checkout"}</Button>
        </div>
      </div>
    </div>
  );
}

export default function LibraryPage() {
  const [tab, setTab]             = useState<Tab>("books");
  const [books, setBooks]         = useState<Book[]>([]);
  const [loans, setLoans]         = useState<Loan[]>([]);
  const [search, setSearch]       = useState("");
  const [loading, setLoading]     = useState(true);
  const [bookDialog, setBookDialog]       = useState(false);
  const [checkoutBook_, setCheckoutBook_] = useState<Book | null>(null);
  const booksLoaded = useRef(false);
  const loansLoaded = useRef(false);

  const loadBooks = useCallback(() => {
    if (!booksLoaded.current) setLoading(true);
    getBooks(search).then(setBooks).catch(() => {}).finally(() => { setLoading(false); booksLoaded.current = true; });
  }, [search]);

  const loadLoans = useCallback(() => {
    if (!loansLoaded.current) setLoading(true);
    getLoans().then(setLoans).catch(() => {}).finally(() => { setLoading(false); loansLoaded.current = true; });
  }, []);

  useEffect(() => { if (tab === "books") loadBooks(); else loadLoans(); }, [tab, loadBooks, loadLoans]);

  const handleReturn = async (id: number) => {
    await returnBook(id).catch(() => {});
    loadLoans();
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "books", label: "Books" },
    { key: "loans", label: "Active Loans" },
  ];

  return (
    <div className="p-8 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Library</h1>
          <p className="text-sm text-gray-500 mt-0.5">Books and loan management</p>
        </div>
        {tab === "books" && (
          <Button variant="primary" icon={<Plus size={15} />} onClick={() => setBookDialog(true)}>Add Book</Button>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key ? "border-violet-600 text-violet-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "books" && (
        <>
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1 max-w-xs">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title, author…"
                className="w-full h-9 pl-8 pr-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Author</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Copies</th>
                  <th className="px-4 py-3">Available</th>
                  <th className="px-4 py-3 w-24" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading
                  ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                  : books.length === 0
                  ? <tr><td colSpan={6} className="py-16"><EmptyState icon={BookOpen} title="No books found" /></td></tr>
                  : books.map((b) => (
                    <tr key={b.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{b.title}</td>
                      <td className="px-4 py-3 text-gray-600">{b.author}</td>
                      <td className="px-4 py-3 text-gray-500">{b.category || "—"}</td>
                      <td className="px-4 py-3 text-gray-600">{b.total_copies}</td>
                      <td className="px-4 py-3">
                        <Badge variant={b.available_copies > 0 ? "green" : "red"}>{b.available_copies}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        {b.available_copies > 0 && (
                          <Button variant="outline" size="sm" icon={<ArrowRightLeft size={12} />} onClick={() => setCheckoutBook_(b)}>
                            Checkout
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "loans" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Book</th>
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Issued</th>
                <th className="px-4 py-3">Due</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={6} />)
                : loans.length === 0
                ? <tr><td colSpan={6} className="py-16"><EmptyState icon={BookOpen} title="No active loans" /></td></tr>
                : loans.map((l) => {
                  const overdue = !l.returned_at && new Date(l.due_date) < new Date();
                  return (
                    <tr key={l.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{l.book_title}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {l.borrower_name}
                        <span className="text-xs text-gray-400 ml-1">({l.borrower_type})</span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{l.issue_date?.slice(0, 10)}</td>
                      <td className="px-4 py-3 text-gray-500">{l.due_date}</td>
                      <td className="px-4 py-3">
                        {l.returned_at
                          ? <Badge variant="green">Returned</Badge>
                          : overdue
                          ? <Badge variant="red">Overdue</Badge>
                          : <Badge variant="amber">Active</Badge>
                        }
                      </td>
                      <td className="px-4 py-3">
                        {!l.returned_at && (
                          <Button variant="outline" size="sm" icon={<RotateCcw size={13} />} onClick={() => handleReturn(l.id)}>
                            Return
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}

      {bookDialog && (
        <BookDialog onSave={() => { setBookDialog(false); loadBooks(); }} onClose={() => setBookDialog(false)} />
      )}
      {checkoutBook_ && (
        <CheckoutDialog
          book={checkoutBook_}
          onSave={() => { setCheckoutBook_(null); loadBooks(); }}
          onClose={() => setCheckoutBook_(null)}
        />
      )}
    </div>
  );
}
