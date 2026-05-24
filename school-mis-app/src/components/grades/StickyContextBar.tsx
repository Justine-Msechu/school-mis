import { Lock, AlertCircle } from "lucide-react";
import { clsx } from "clsx";
import Button from "@/components/ui/Button";

interface StatusCounts {
  draft: number;
  locked: number;
  approved: number;
  empty: number;
  total: number;
}

interface StickyContextBarProps {
  examLabel: string;
  classLabel: string;
  subjectLabel: string;
  status: StatusCounts;
  hasEditable: boolean;
  saving: boolean;
  submitting: boolean;
  onSave: () => void;
  onSubmit: () => void;
}

function StatusPill({ count, label, color }: { count: number; label: string; color: string }) {
  if (count === 0) return null;
  return (
    <span className={clsx("status-chip text-2xs", color)}>
      {count} {label}
    </span>
  );
}

export default function StickyContextBar({
  examLabel, classLabel, subjectLabel,
  status, hasEditable, saving, submitting,
  onSave, onSubmit,
}: StickyContextBarProps) {
  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex items-center gap-4 px-5 py-2.5">
        {/* Context chips */}
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          <span className="text-xs font-medium text-gray-500 flex-shrink-0">Editing:</span>
          <span className="status-chip bg-violet-100 text-violet-700">{examLabel}</span>
          <span className="status-chip bg-blue-100 text-blue-700">{classLabel}</span>
          <span className="status-chip bg-cyan-100 text-cyan-700">{subjectLabel}</span>
        </div>

        {/* Status pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <StatusPill count={status.draft}    label="Draft"    color="bg-amber-100 text-amber-700" />
          <StatusPill count={status.locked}   label="Locked"   color="bg-blue-100 text-blue-700" />
          <StatusPill count={status.approved} label="Approved" color="bg-emerald-100 text-emerald-700" />
          <StatusPill count={status.empty}    label="Not entered" color="bg-gray-100 text-gray-500" />
        </div>

        {status.locked > 0 && (
          <span className="flex items-center gap-1 text-2xs text-amber-700">
            <Lock size={10} />
            Use 'Request Change' for locked rows
          </span>
        )}

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!hasEditable}
            loading={saving}
            onClick={onSave}
          >
            Save Draft
          </Button>
          <Button
            variant="success"
            size="sm"
            disabled={!hasEditable}
            loading={submitting}
            onClick={onSubmit}
            icon={<AlertCircle size={13} />}
          >
            Finalize & Submit
          </Button>
        </div>
      </div>
    </div>
  );
}
