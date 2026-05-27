import { useNavigate } from "react-router-dom";
import { Eye, X } from "lucide-react";
import { useImpersonationStore } from "@/stores/impersonationStore";

export default function ImpersonationBanner() {
  const { schoolName, exit } = useImpersonationStore();
  const navigate = useNavigate();

  const handleExit = () => {
    exit();
    navigate("/platform");
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-amber-500 text-white text-sm flex-shrink-0 z-50">
      <div className="flex items-center gap-2">
        <Eye size={15} />
        <span>
          You are viewing <strong>{schoolName}</strong> as Administrator
        </span>
      </div>
      <button
        onClick={handleExit}
        className="flex items-center gap-1.5 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-xs font-semibold transition-colors"
      >
        <X size={13} />
        Exit to Platform Admin
      </button>
    </div>
  );
}
