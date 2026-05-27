import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ImpersonationState {
  active:     boolean;
  schoolId:   number | null;
  schoolName: string;
  enter:      (schoolId: number, schoolName: string) => void;
  exit:       () => void;
}

export const useImpersonationStore = create<ImpersonationState>()(
  persist(
    (set) => ({
      active:     false,
      schoolId:   null,
      schoolName: "",
      enter: (schoolId, schoolName) => set({ active: true, schoolId, schoolName }),
      exit:  ()                     => set({ active: false, schoolId: null, schoolName: "" }),
    }),
    { name: "mis-impersonation" },
  ),
);
