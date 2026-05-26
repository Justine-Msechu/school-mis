import { useState, useEffect, useCallback, useRef } from "react";
import { Search, BookOpen, RotateCcw, Plus, ArrowRightLeft } from "lucide-react";
import { getBooks, getLoans, returnBook, createBook, checkoutBook, type Book, type Loan } from "@/api/library";
import { getStudents } from "@/api/students";
import { getClassList, getClassStudents, type ClassRecord, type ClassStudent } from "@/api/classes";
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
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
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
  const [classId, setClassId]     = useState<number | "">("");
  const [studentId, setStudentId] = useState<number | "">("");
  const [classes, setClasses]     = useState<ClassRecord[]>([]);
  const [students, setStudents]   = useState<ClassStudent[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [dueDate, setDueDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 14); return d.toISOString().slice(0, 10);
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  useEffect(() => {
    getClassList().then(setClasses).catch(() => {});
    // Load all students initially
    setLoadingStudents(true);
    getStudents({ per_page: 200 })
      .then((res) => setStudents(res.items.map((s) => ({ id: s.id, first_name: s.first_name, last_name: s.last_name, admission_no: s.admission_no, gender: s.gender }))))
      .catch(() => {})
      .finally(() => setLoadingStudents(false));
  }, []);

  useEffect(() => {
    setStudentId("");
    setLoadingStudents(true);
    if (classId !== "") {
      getClassStudents(Number(classId))
        .then(setStudents)
        .catch(() => setStudents([]))
        .finally(() => setLoadingStudents(false));
    } else {
      getStudents({ per_page: 200 })
        .then((res) => setStudents(res.items.map((s) => ({ id: s.id, first_name: s.first_name, last_name: s.last_name, admission_no: s.admission_no, gender: s.gender }))))
        .catch(() => setStudents([]))
        .finally(() => setLoadingStudents(false));
    }
  }, [classId]);

  const submit = async () => {
    if (!studentId) { setError("Please select a student."); return; }
    if (!dueDate)   { setError("Due date is required."); return; }
    setSaving(true);
    setError("");
    try {
      await checkoutBook(book.id, Number(studentId), dueDate);
      onSave();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to checkout book.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card p-5 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Checkout Book</h2>
        <p className="text-sm text-gray-500 mb-4">{book.title} — {book.author}</p>
        {error && <div className="mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
        <div className="space-y-3">
          <Field label="Filter by Class">
            <select
              className={INPUT}
              value={classId}
              onChange={(e) => setClassId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">All Classes</option>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Student *">
            <select
              className={INPUT}
              value={studentId}
              onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : "")}
              disabled={loadingStudents}
            >
              <option value="">{loadingStudents ? "Loading…" : `Select student (${students.length})`}</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.first_name} {s.last_name} — {s.admission_no}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Due Date *">
            <input
              type="date"
              className={INPUT}
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={saving || !studentId}>
            {saving ? "Saving…" : "Checkout"}
          </Button>
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
    try {
      await returnBook(id);
    } catch {
      // silently ignore — loan refresh below will show current state
    }
    loansLoaded.current = false;
    loadLoans();
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "books", label: "Books" },
    { key: "loans", label: "Active Loans" },
  ];

  return (
    <div className="page-content">
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
            <div className="table-scroll"><table className="w-full text-sm">
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
            </table></div>
          </div>
        </>
      )}

      {tab === "loans" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="table-scroll"><table className="w-full text-sm">
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
                  const returned = l.status === "returned";
                  const overdue  = !returned && new Date(l.due_date) < new Date();
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
                        {returned
                          ? <Badge variant="green">Returned</Badge>
                          : overdue
                          ? <Badge variant="red">Overdue</Badge>
                          : <Badge variant="amber">Active</Badge>
                        }
                      </td>
                      <td className="px-4 py-3">
                        {!returned && (
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
          </table></div>
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
