import { Routes, Route, NavLink } from "react-router-dom";
import { clsx } from "clsx";
import { useAuthStore } from "@/stores/authStore";
import ResultsPage from "./ResultsPage";
import GradeEntryPage from "./GradeEntryPage";
import ApprovalsTab from "./ApprovalsTab";
import ExamManagementTab from "./ExamManagementTab";
import ChangeRequestsTab from "./ChangeRequestsTab";
import HomeworkTab from "./HomeworkTab";

const tabs = [
  { label: "Grade Entry",       path: "",          perm: "grades.write"                  },
  { label: "Approvals",         path: "approvals", perm: "grades.approve"                },
  { label: "Results & Reports", path: "results",   perm: "grades.view"                   },
  { label: "Exam Management",   path: "exams",     perm: "grades.approve"                },
  {
    label: "Change Requests", path: "changes",
    // Teachers can see their submitted requests; academic can review them
    perms: ["grades.change_request.create", "grades.change_request.review"],
  },
  { label: "Homework",          path: "homework",  perm: "homework.view"                 },
];

export default function GradesPage() {
  const { can } = useAuthStore();
  const visibleTabs = tabs.filter((t) => {
    if ((t as any).perms) return (t as any).perms.some((p: string) => can(p));
    return !t.perm || can(t.perm);
  });

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="bg-white border-b border-gray-200 px-8">
        <div className="flex gap-1">
          {visibleTabs.map((t) => (
            <NavLink
              key={t.path}
              to={`/grades${t.path ? "/" + t.path : ""}`}
              end={t.path === ""}
              className={({ isActive }) =>
                clsx(
                  "px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                  isActive
                    ? "border-violet-600 text-violet-700"
                    : "border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300"
                )
              }
            >
              {t.label}
            </NavLink>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        <Routes>
          <Route index            element={<GradeEntryPage />} />
          <Route path="results"   element={<ResultsPage />} />
          <Route path="approvals" element={<ApprovalsTab />} />
          <Route path="exams"     element={<ExamManagementTab />} />
          <Route path="changes"   element={<ChangeRequestsTab />} />
          <Route path="homework"  element={<HomeworkTab />} />
        </Routes>
      </div>
    </div>
  );
}
