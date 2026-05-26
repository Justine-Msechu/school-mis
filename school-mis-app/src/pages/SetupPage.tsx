import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, School, User, Check, ChevronRight, Eye, EyeOff } from "lucide-react";
import { initializeSystem } from "@/api/setup";

const INPUT = "w-full h-10 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 bg-white text-gray-900";
const LABEL = "block text-xs font-semibold text-gray-600 mb-1";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

const STEPS = [
  { icon: School, title: "School Information",  desc: "Tell us about your school" },
  { icon: User,   title: "Admin Account",        desc: "Create your administrator login" },
  { icon: Check,  title: "Finish Setup",          desc: "Review and complete" },
];

export default function SetupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [done, setDone] = useState(false);

  const [form, setForm] = useState({
    school_name:    "",
    school_address: "",
    school_phone:   "",
    school_email:   "",
    school_type:    "primary",
    admin_username: "",
    admin_fullname: "",
    admin_password: "",
    admin_confirm:  "",
  });

  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const validateStep = () => {
    setError("");
    if (step === 0) {
      if (!form.school_name.trim()) { setError("School name is required."); return false; }
    }
    if (step === 1) {
      if (!form.admin_username.trim()) { setError("Username is required."); return false; }
      if (!form.admin_fullname.trim()) { setError("Full name is required."); return false; }
      if (form.admin_password.length < 8) { setError("Password must be at least 8 characters."); return false; }
      if (form.admin_password !== form.admin_confirm) { setError("Passwords do not match."); return false; }
    }
    return true;
  };

  const next = () => {
    if (!validateStep()) return;
    setStep((s) => s + 1);
  };

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      await initializeSystem({
        school_name:    form.school_name.trim(),
        school_address: form.school_address.trim(),
        school_phone:   form.school_phone.trim(),
        school_email:   form.school_email.trim(),
        school_type:    form.school_type,
        admin_username: form.admin_username.trim(),
        admin_fullname: form.admin_fullname.trim(),
        admin_password: form.admin_password,
      });
      setDone(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Setup failed. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-violet-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="modal-card p-6 sm:p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
            <Check size={32} className="text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Setup Complete!</h2>
          <p className="text-gray-600 mb-1">
            <strong>{form.school_name}</strong> is ready to use.
          </p>
          <p className="text-sm text-gray-500 mb-6">
            You have a 30-day free trial. Log in with <strong>{form.admin_username}</strong> to get started.
          </p>
          <button
            onClick={() => navigate("/login")}
            className="w-full h-11 bg-violet-600 hover:bg-violet-700 text-white font-semibold rounded-lg transition-colors"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-violet-600 mb-4">
            <BookOpen size={28} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">School MIS</h1>
          <p className="text-gray-500 mt-1">First-time setup — takes about 2 minutes</p>
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-center gap-0 mb-8">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm transition-colors ${
                  i < step ? "bg-green-500 text-white" :
                  i === step ? "bg-violet-600 text-white" :
                  "bg-gray-200 text-gray-500"
                }`}>
                  {i < step ? <Check size={16} /> : i + 1}
                </div>
                <span className={`text-xs mt-1 font-medium hidden sm:block ${i === step ? "text-violet-700" : "text-gray-400"}`}>
                  {s.title.split(" ")[0]}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`w-16 h-0.5 mx-1 mb-4 ${i < step ? "bg-green-400" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-3">
            {(() => { const Icon = STEPS[step].icon; return <Icon size={20} className="text-violet-600" />; })()}
            <div>
              <h2 className="text-base font-semibold text-gray-900">{STEPS[step].title}</h2>
              <p className="text-xs text-gray-500">{STEPS[step].desc}</p>
            </div>
          </div>

          <div className="p-6">
            {error && (
              <div className="mb-4 px-4 py-2.5 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
                {error}
              </div>
            )}

            {/* Step 0 — School info */}
            {step === 0 && (
              <div className="flex flex-col gap-4">
                <Field label="School Name *">
                  <input className={INPUT} value={form.school_name}
                    onChange={(e) => set("school_name", e.target.value)}
                    placeholder="e.g. Kibandani Primary School" />
                </Field>
                <Field label="School Type">
                  <select className={INPUT} value={form.school_type}
                    onChange={(e) => set("school_type", e.target.value)}>
                    <option value="primary">Primary School</option>
                    <option value="secondary">Secondary School</option>
                    <option value="mixed">Mixed (Primary + Secondary)</option>
                    <option value="nursery">Nursery / Pre-school</option>
                  </select>
                </Field>
                <Field label="Address">
                  <input className={INPUT} value={form.school_address}
                    onChange={(e) => set("school_address", e.target.value)}
                    placeholder="P.O. Box, Town, Region" />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Phone">
                    <input className={INPUT} value={form.school_phone}
                      onChange={(e) => set("school_phone", e.target.value)}
                      placeholder="+255 222 123456" />
                  </Field>
                  <Field label="Email">
                    <input className={INPUT} value={form.school_email}
                      onChange={(e) => set("school_email", e.target.value)}
                      placeholder="info@school.tz" type="email" />
                  </Field>
                </div>
              </div>
            )}

            {/* Step 1 — Admin account */}
            {step === 1 && (
              <div className="flex flex-col gap-4">
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-100 text-xs text-blue-700">
                  This account will have full administrator access. Keep the credentials safe.
                </div>
                <Field label="Full Name *">
                  <input className={INPUT} value={form.admin_fullname}
                    onChange={(e) => set("admin_fullname", e.target.value)}
                    placeholder="e.g. John Doe" />
                </Field>
                <Field label="Username *">
                  <input className={INPUT} value={form.admin_username}
                    onChange={(e) => set("admin_username", e.target.value.toLowerCase().replace(/\s+/g, ""))}
                    placeholder="e.g. admin" autoComplete="username" />
                </Field>
                <Field label="Password *">
                  <div className="relative">
                    <input
                      className={INPUT + " pr-10"}
                      type={showPw ? "text" : "password"}
                      value={form.admin_password}
                      onChange={(e) => set("admin_password", e.target.value)}
                      placeholder="Minimum 8 characters"
                      autoComplete="new-password"
                    />
                    <button type="button" onClick={() => setShowPw((p) => !p)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </Field>
                <Field label="Confirm Password *">
                  <input className={INPUT} type="password"
                    value={form.admin_confirm}
                    onChange={(e) => set("admin_confirm", e.target.value)}
                    placeholder="Re-enter password"
                    autoComplete="new-password" />
                </Field>
              </div>
            )}

            {/* Step 2 — Review */}
            {step === 2 && (
              <div className="flex flex-col gap-4">
                <div className="rounded-xl border border-gray-100 overflow-hidden">
                  <div className="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    School
                  </div>
                  <div className="px-4 py-3 flex flex-col gap-1.5 text-sm">
                    <div className="flex justify-between"><span className="text-gray-500">Name</span><span className="font-medium">{form.school_name}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Type</span><span className="capitalize">{form.school_type}</span></div>
                    {form.school_address && <div className="flex justify-between"><span className="text-gray-500">Address</span><span className="text-right max-w-[60%]">{form.school_address}</span></div>}
                  </div>
                </div>
                <div className="rounded-xl border border-gray-100 overflow-hidden">
                  <div className="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Admin Account
                  </div>
                  <div className="px-4 py-3 flex flex-col gap-1.5 text-sm">
                    <div className="flex justify-between"><span className="text-gray-500">Name</span><span className="font-medium">{form.admin_fullname}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Username</span><span className="font-mono">{form.admin_username}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Password</span><span>{"•".repeat(form.admin_password.length)}</span></div>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-100 text-xs text-amber-700 flex gap-2">
                  <span>⏱</span>
                  <span>You'll get a <strong>30-day free trial</strong>. No credit card needed to start.</span>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 pb-6 flex justify-between items-center">
            {step > 0 ? (
              <button onClick={() => setStep((s) => s - 1)}
                className="h-9 px-4 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                Back
              </button>
            ) : <div />}
            {step < 2 ? (
              <button onClick={next}
                className="h-9 px-5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-lg flex items-center gap-1.5 transition-colors">
                Continue <ChevronRight size={15} />
              </button>
            ) : (
              <button onClick={submit} disabled={saving}
                className="h-9 px-5 bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg flex items-center gap-1.5 transition-colors">
                {saving ? "Setting up…" : "Complete Setup"}
                {!saving && <Check size={15} />}
              </button>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          Already set up? <a href="/login" className="text-violet-600 hover:underline">Go to login</a>
        </p>
      </div>
    </div>
  );
}
