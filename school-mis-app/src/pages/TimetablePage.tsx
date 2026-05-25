import { useEffect, useRef, useState } from "react";
import { Plus, Calendar } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import Modal from "@/components/ui/Modal";
import FormField from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";
import {
  getPeriods, listVersions, createVersion, activateVersion,
  getClassTimetable, setSlot, deleteSlot,
  type TimetablePeriod, type TimetableVersion,
} from "@/api/timetable";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";

const DAYS = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface AcademicYear { id: number; label: string; is_current: number; }
interface ClassRow { id: number; name: string; }
interface SubjectRow { id: number; name: string; }
interface TeacherRow { id: number; first_name: string; last_name: string; }

export default function TimetablePage() {
  const toast = useToast();
  const { can } = useAuthStore();
  const canManage = can("timetable.manage");
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [subjects, setSubjects] = useState<SubjectRow[]>([]);
  const [teachers, setTeachers] = useState<TeacherRow[]>([]);
  const [periods, setPeriods] = useState<TimetablePeriod[]>([]);
  const [versions, setVersions] = useState<TimetableVersion[]>([]);
  const [year, setYear] = useState<number | "">("");
  const [version, setVersion] = useState<number | "">("");
  const [classId, setClassId] = useState<number | "">("");
  const [grid, setGrid] = useState<Record<number, Record<number, any>>>({});
  const [slots, setSlots] = useState<any[]>([]);
  const [slotOpen, setSlotOpen] = useState(false);
  const [slotForm, setSlotForm] = useState<any>({ day_of_week: 1 });
  const [newVerOpen, setNewVerOpen] = useState(false);
  const [newVerName, setNewVerName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get("/settings/academic-years").then((r) => r.data),
      api.get("/classes").then((r) => r.data),
      api.get("/grades/subjects").then((r) => r.data),
      api.get("/teachers").then((r) => r.data),
      getPeriods(),
    ]).then(([yrs, cls, subs, tchs, pds]) => {
      setYears(yrs);
      setClasses(cls.items || cls);
      setSubjects(subs.items || subs);
      setTeachers(tchs.items || tchs);
      setPeriods(pds);
      const cur = yrs.find((y: AcademicYear) => y.is_current === 1);
      if (cur) setYear(cur.id);
    });
  }, []);

  useEffect(() => {
    if (!year) return;
    listVersions(year as number).then((vs) => {
      setVersions(vs);
      const active = vs.find((v: TimetableVersion) => v.status === "active");
      if (active) setVersion(active.id);
      else if (vs.length > 0) setVersion(vs[0].id);
    });
  }, [year]);

  useEffect(() => {
    if (!version || !classId) { setGrid({}); setSlots([]); return; }
    getClassTimetable(version as number, classId as number).then((data) => {
      setGrid(data.grid || {});
      setSlots(data.slots || []);
    });
  }, [version, classId]);

  const handleSetSlot = async () => {
    setSaving(true);
    try {
      await setSlot(version as number, {
        class_id: classId as number,
        subject_id: Number(slotForm.subject_id),
        period_id: Number(slotForm.period_id),
        day_of_week: Number(slotForm.day_of_week),
        teacher_id: slotForm.teacher_id ? Number(slotForm.teacher_id) : undefined,
        room: slotForm.room,
      });
      toast.success("Slot saved");
      setSlotOpen(false);
      getClassTimetable(version as number, classId as number).then((data) => {
        setGrid(data.grid || {}); setSlots(data.slots || []);
      });
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to save slot");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSlot = async (slotId: number) => {
    try {
      await deleteSlot(slotId);
      toast.success("Slot removed");
      getClassTimetable(version as number, classId as number).then((data) => {
        setGrid(data.grid || {}); setSlots(data.slots || []);
      });
    } catch {
      toast.error("Failed to remove slot");
    }
  };

  const handleCreateVersion = async () => {
    if (!newVerName || !year) return;
    setSaving(true);
    try {
      const v = await createVersion({ academic_year_id: year as number, name: newVerName });
      setVersions((prev) => [v, ...prev]);
      setVersion(v.id);
      setNewVerOpen(false);
      setNewVerName("");
      toast.success("Version created");
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async () => {
    if (!version) return;
    try {
      await activateVersion(version as number);
      toast.success("Version activated");
      listVersions(year as number).then(setVersions);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed");
    }
  };

  const teachingPeriods = periods.filter((p) => !p.is_break);

  return (
    <div className="p-6">
      <PageHeader
        title="Timetable"
        subtitle="Manage school schedule and class timetables"
        actions={
          canManage ? (
            <button onClick={() => setNewVerOpen(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition-colors">
              <Plus size={15} /> New Version
            </button>
          ) : undefined
        }
      />

      <div className="flex gap-3 mb-6 flex-wrap">
        <select value={year} onChange={(e) => setYear(Number(e.target.value))}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
          <option value="">Year</option>
          {years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
        </select>
        <select value={version} onChange={(e) => setVersion(Number(e.target.value))}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
          <option value="">Version</option>
          {versions.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.status})</option>)}
        </select>
        {version && canManage && (
          <button onClick={handleActivate}
            className="px-3 py-2 text-sm border border-violet-200 text-violet-700 rounded-lg hover:bg-violet-50">
            Activate
          </button>
        )}
        <select value={classId} onChange={(e) => setClassId(Number(e.target.value))}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
          <option value="">Select class</option>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {version && classId && canManage && (
          <button onClick={() => { setSlotForm({ day_of_week: 1 }); setSlotOpen(true); }}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">
            <Plus size={13} /> Add Slot
          </button>
        )}
      </div>

      {classId && version ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 w-28">Period</th>
                {[1,2,3,4,5].map((d) => (
                  <th key={d} className="px-4 py-3 text-left text-xs font-semibold text-gray-700">{DAYS[d]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {periods.map((p) => (
                <tr key={p.id} className={`border-b border-gray-50 ${p.is_break ? "bg-gray-50" : ""}`}>
                  <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                    <div className="font-medium text-gray-700">{p.name}</div>
                    <div>{p.start_time}–{p.end_time}</div>
                  </td>
                  {[1,2,3,4,5].map((d) => {
                    if (p.is_break) return (
                      <td key={d} className="px-4 py-2 text-xs text-gray-400 italic">Break</td>
                    );
                    const slot = grid[d]?.[p.id];
                    return (
                      <td key={d} className="px-3 py-2">
                        {slot ? (
                          <div className="bg-violet-50 border border-violet-100 rounded-lg px-2 py-1 group relative">
                            <div className="font-medium text-violet-800 text-xs">{slot.subject_name}</div>
                            {slot.teacher_name && <div className="text-violet-600 text-xs">{slot.teacher_name}</div>}
                            {slot.room && <div className="text-violet-400 text-xs">{slot.room}</div>}
                            {canManage && (
                              <button
                                onClick={() => handleDeleteSlot(slot.id)}
                                className="absolute top-1 right-1 hidden group-hover:block text-red-400 hover:text-red-600 text-xs leading-none"
                              >✕</button>
                            )}
                          </div>
                        ) : canManage ? (
                          <button
                            onClick={() => { setSlotForm({ day_of_week: d, period_id: String(p.id) }); setSlotOpen(true); }}
                            className="w-full h-8 border border-dashed border-gray-200 rounded-lg hover:border-violet-300 hover:bg-violet-50/50 transition-colors text-gray-300 hover:text-violet-400 text-xs"
                          >+</button>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 bg-white rounded-2xl border border-gray-100 text-gray-400">
          <div className="text-center">
            <Calendar size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm">Select a version and class to view the timetable</p>
          </div>
        </div>
      )}

      <Modal open={slotOpen} onClose={() => setSlotOpen(false)} title="Set Timetable Slot"
        footer={
          <>
            <button onClick={() => setSlotOpen(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
            <button onClick={handleSetSlot} disabled={saving} className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {saving ? "Saving…" : "Save"}
            </button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <FormField label="Day of Week" required>
            <select value={slotForm.day_of_week} onChange={(e) => setSlotForm((f: any) => ({ ...f, day_of_week: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
              {[1,2,3,4,5].map((d) => <option key={d} value={d}>{DAYS[d]}</option>)}
            </select>
          </FormField>
          <FormField label="Period" required>
            <select value={slotForm.period_id || ""} onChange={(e) => setSlotForm((f: any) => ({ ...f, period_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
              <option value="">Select period</option>
              {teachingPeriods.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.start_time}–{p.end_time})</option>)}
            </select>
          </FormField>
          <FormField label="Subject" required>
            <select value={slotForm.subject_id || ""} onChange={(e) => setSlotForm((f: any) => ({ ...f, subject_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
              <option value="">Select subject</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </FormField>
          <FormField label="Teacher">
            <select value={slotForm.teacher_id || ""} onChange={(e) => setSlotForm((f: any) => ({ ...f, teacher_id: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none">
              <option value="">No teacher assigned</option>
              {teachers.map((t) => <option key={t.id} value={t.id}>{t.first_name} {t.last_name}</option>)}
            </select>
          </FormField>
          <FormField label="Room">
            <input type="text" value={slotForm.room || ""} onChange={(e) => setSlotForm((f: any) => ({ ...f, room: e.target.value }))}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none"
              placeholder="e.g. Room 12A" />
          </FormField>
        </div>
      </Modal>

      <Modal open={newVerOpen} onClose={() => setNewVerOpen(false)} title="Create Timetable Version"
        footer={
          <>
            <button onClick={() => setNewVerOpen(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
            <button onClick={handleCreateVersion} disabled={saving || !newVerName}
              className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {saving ? "Creating…" : "Create"}
            </button>
          </>
        }
      >
        <FormField label="Version Name" required>
          <input value={newVerName} onChange={(e) => setNewVerName(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none w-full"
            placeholder="e.g. Term 1 2025/26" />
        </FormField>
      </Modal>
    </div>
  );
}
