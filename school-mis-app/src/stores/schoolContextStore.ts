import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SchoolContextState {
  schoolId:   number | null;
  schoolName: string;
  setSchool:  (id: number, name: string) => void;
  clear:      () => void;
}

export const useSchoolContextStore = create<SchoolContextState>()(
  persist(
    (set) => ({
      schoolId:   null,
      schoolName: "",
      setSchool:  (id, name) => set({ schoolId: id, schoolName: name }),
      clear:      () => set({ schoolId: null, schoolName: "" }),
    }),
    { name: "mis-school-ctx" },
  ),
);
