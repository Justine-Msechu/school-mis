import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ImpersonationState {
  active:     boolean;
  schoolId:   number | null;
  schoolName: string;
  enter:      (schoolId: number, schoolName: string) => void;
  exit:       () => void;
}

// Read synchronously so the first render already knows impersonation state.
const _readImpersonation = () => {
  try {
    const raw = localStorage.getItem("mis-impersonation");
    if (!raw) return { active: false, schoolId: null as null, schoolName: "" };
    const s = (JSON.parse(raw) as { state?: { active?: boolean; schoolId?: number | null; schoolName?: string } })?.state ?? {};
    return { active: !!s.active, schoolId: s.schoolId ?? null, schoolName: s.schoolName ?? "" };
  } catch {
    return { active: false, schoolId: null as null, schoolName: "" };
  }
};
const _imp = _readImpersonation();

export const useImpersonationStore = create<ImpersonationState>()(
  persist(
    (set) => ({
      active:     _imp.active,
      schoolId:   _imp.schoolId,
      schoolName: _imp.schoolName,
      enter: (schoolId, schoolName) => set({ active: true, schoolId, schoolName }),
      exit:  ()                     => set({ active: false, schoolId: null, schoolName: "" }),
    }),
    {
      name: "mis-impersonation",
      // We already pre-read localStorage synchronously above — skip Zustand's
      // own async hydration pass so it doesn't fire a spurious re-render.
      skipHydration: true,
    },
  ),
);
