import { useState, useEffect, useCallback } from "react";
import { Search, BookOpen, RotateCcw } from "lucide-react";
import { getBooks, getLoans, returnBook, type Book, type Loan } from "@/api/library";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import SkeletonRow from "@/components/ui/SkeletonRow";

type Tab = "books" | "loans";

export default function LibraryPage() {
  const [tab, setTab]         = useState<Tab>("books");
  const [books, setBooks]     = useState<Book[]>([]);
  const [loans, setLoans]     = useState<Loan[]>([]);
  const [search, setSearch]   = useState("");
  const [loading, setLoading] = useState(true);
  const [loanStatus, setLoanStatus] = useState("active");

  const loadBooks = useCallback(() => {
    setLoading(true);
    getBooks(search).then(setBooks).catch(() => {}).finally(() => setLoading(false));
  }, [search]);

  const loadLoans = useCallback(() => {
    setLoading(true);
    getLoans(loanStatus === "active" ? undefined : undefined)
      .then(setLoans).catch(() => {}).finally(() => setLoading(false));
  }, [loanStatus]);

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
      </div>

      {/* Tabs */}
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
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading
                  ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
                  : books.length === 0
                  ? <tr><td colSpan={5} className="py-16"><EmptyState icon={BookOpen} title="No books found" /></td></tr>
                  : books.map((b) => (
                    <tr key={b.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{b.title}</td>
                      <td className="px-4 py-3 text-gray-600">{b.author}</td>
                      <td className="px-4 py-3 text-gray-500">{b.category || "—"}</td>
                      <td className="px-4 py-3 text-gray-600">{b.copies_total}</td>
                      <td className="px-4 py-3">
                        <Badge variant={b.copies_available > 0 ? "green" : "red"}>
                          {b.copies_available}
                        </Badge>
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
                <th className="px-4 py-3"></th>
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
                      <td className="px-4 py-3 text-gray-600">{l.student_name} <span className="text-xs text-gray-400">({l.admission_no})</span></td>
                      <td className="px-4 py-3 text-gray-500">{l.issued_at?.slice(0, 10)}</td>
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
    </div>
  );
}
