import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { BookOpen, Cloud, BarChart2, Shield, Headphones, Eye, EyeOff, Check } from "lucide-react";
import { registerSchool } from "@/api/schools";

const BENEFITS = [
  { icon: Cloud,       title: "Cloud-Based Platform",   desc: "Access anywhere, anytime" },
  { icon: BarChart2,   title: "Real-Time Analytics",    desc: "Data-driven decisions" },
  { icon: Shield,      title: "Secure & Reliable",      desc: "Enterprise-grade security" },
  { icon: Headphones,  title: "24/7 Dedicated Support", desc: "We're here to help" },
];

const COUNTRIES = ["Tanzania", "Kenya", "Uganda", "Rwanda", "Burundi"];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    admin_fullname:       "",
    school_name:          "",
    school_type:          "primary",
    school_ownership:     "private",
    registration_number:  "",
    school_email:         "",
    contact_phone:        "",
    school_address:       "",
    school_location:      "",
    country:              "Tanzania",
    website:              "",
    login_header_message: "",
    admin_username:       "",
    admin_password:       "",
    confirm_password:     "",
    accept_terms:         false,
  });
  const [showPw,  setShowPw]  = useState(false);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [success, setSuccess] = useState("");

  const set = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.accept_terms) { setError("You must accept the Terms and Conditions."); return; }
    if (form.admin_password !== form.confirm_password) { setError("Passwords do not match."); return; }
    if (form.admin_password.length < 8) { setError("Password must be at least 8 characters."); return; }

    setLoading(true);
    try {
      const res = await registerSchool({
        school_name:          form.school_name.trim(),
        school_type:          form.school_type,
        school_ownership:     form.school_ownership,
        registration_number:  form.registration_number.trim(),
        school_email:         form.school_email.trim(),
        contact_phone:        form.contact_phone.trim(),
        school_address:       form.school_address.trim(),
        school_location:      form.school_location.trim(),
        country:              form.country,
        website:              form.website.trim(),
        login_header_message: form.login_header_message.trim(),
        admin_fullname:       form.admin_fullname.trim(),
        admin_username:       form.admin_username.trim(),
        admin_password:       form.admin_password,
      });
      setSuccess(res.data.message);
      setTimeout(() => navigate("/login"), 3000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-blue-50">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-xl p-10 w-full max-w-sm text-center">
          <div className="w-14 h-14 rounded-2xl bg-green-50 border border-green-100 flex items-center justify-center mx-auto mb-4">
            <Check size={28} className="text-green-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Registration Successful!</h2>
          <p className="text-sm text-gray-500 mb-1">{success}</p>
          <p className="text-xs text-gray-400 mt-3">Redirecting to login in a few seconds…</p>
        </div>
      </div>
    );
  }

  const Field = ({
    label, required, children,
  }: { label: string; required?: boolean; children: React.ReactNode }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );

  const inputCls = "w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white";
  const selectCls = `${inputCls} appearance-none`;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white py-10 px-4 text-center">
        <div className="flex items-center justify-center gap-2.5 mb-5">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
            <BookOpen size={20} className="text-white" />
          </div>
          <span className="text-xl font-bold">School MIS</span>
        </div>
        <h1 className="text-3xl font-bold mb-2">Join the Digital Education Revolution</h1>
        <p className="text-blue-100 text-sm max-w-xl mx-auto">
          Join 500+ schools across East Africa managing students, teachers, fees, and more in one powerful platform.
        </p>

        {/* Benefit cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-3xl mx-auto mt-8">
          {BENEFITS.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="bg-white/10 border border-white/20 rounded-xl p-3 text-left">
              <Icon size={18} className="text-white mb-2" />
              <p className="text-xs font-semibold text-white">{title}</p>
              <p className="text-xs text-blue-200 mt-0.5">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Back link */}
        <div className="mb-5">
          <Link to="/landing" className="text-sm text-blue-600 hover:underline">← Back to Home</Link>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Register Your School</h2>
          <p className="text-sm text-gray-500 mb-6">Fill in the details below to get started with School MIS.</p>

          {error && (
            <div className="mb-5 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Admin */}
            <Field label="Full Name of Admin" required>
              <input type="text" required value={form.admin_fullname} onChange={set("admin_fullname")}
                placeholder="John Mwangi" className={inputCls} />
            </Field>

            {/* School name */}
            <Field label="School Name" required>
              <input type="text" required value={form.school_name} onChange={set("school_name")}
                placeholder="Sunrise Primary School" className={inputCls} />
            </Field>

            {/* Type + Ownership */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="School Type" required>
                <select value={form.school_type} onChange={set("school_type")} className={selectCls}>
                  <option value="primary">Primary School</option>
                  <option value="secondary">Secondary School</option>
                  <option value="mixed">Mixed (Primary & Secondary)</option>
                </select>
              </Field>
              <Field label="School Ownership" required>
                <select value={form.school_ownership} onChange={set("school_ownership")} className={selectCls}>
                  <option value="private">Private</option>
                  <option value="government">Government</option>
                </select>
              </Field>
            </div>

            {/* Reg number */}
            <Field label="School Registration Number" required>
              <input type="text" required value={form.registration_number} onChange={set("registration_number")}
                placeholder="e.g. PS/DSM/001234" className={inputCls} />
            </Field>

            {/* Email + Phone */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="School Email" required>
                <input type="email" required value={form.school_email} onChange={set("school_email")}
                  placeholder="info@school.ac.tz" className={inputCls} />
              </Field>
              <Field label="School Mobile" required>
                <input type="tel" required value={form.contact_phone} onChange={set("contact_phone")}
                  placeholder="+255 XXX XXX XXX" className={inputCls} />
              </Field>
            </div>

            {/* Address + Location */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="School Address" required>
                <input type="text" required value={form.school_address} onChange={set("school_address")}
                  placeholder="Plot 5, Morogoro Road" className={inputCls} />
              </Field>
              <Field label="School Location" required>
                <input type="text" required value={form.school_location} onChange={set("school_location")}
                  placeholder="Kinondoni, Dar es Salaam" className={inputCls} />
              </Field>
            </div>

            {/* Country */}
            <Field label="Country" required>
              <select value={form.country} onChange={set("country")} className={selectCls}>
                {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>

            {/* Website (optional) */}
            <Field label="School Website">
              <input type="url" value={form.website} onChange={set("website")}
                placeholder="https://www.school.ac.tz" className={inputCls} />
            </Field>

            {/* Login header message */}
            <Field label="Login Header Message">
              <textarea value={form.login_header_message} onChange={set("login_header_message") as any}
                rows={2} placeholder="This message will be shown to your users on the login page"
                className={`${inputCls} resize-none`} />
            </Field>

            {/* Divider */}
            <div className="border-t border-gray-100 pt-5">
              <p className="text-sm font-semibold text-gray-700 mb-4">Admin Login Account</p>
              <div className="space-y-4">
                <Field label="Admin Username" required>
                  <input type="text" required value={form.admin_username} onChange={set("admin_username")}
                    placeholder="john.mwangi" className={inputCls} />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Password" required>
                    <div className="relative">
                      <input type={showPw ? "text" : "password"} required value={form.admin_password}
                        onChange={set("admin_password")} placeholder="Min. 8 characters"
                        className={`${inputCls} pr-9`} />
                      <button type="button" onClick={() => setShowPw(s => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                        {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </Field>
                  <Field label="Confirm Password" required>
                    <input type={showPw ? "text" : "password"} required value={form.confirm_password}
                      onChange={set("confirm_password")} placeholder="Repeat password"
                      className={inputCls} />
                  </Field>
                </div>
              </div>
            </div>

            {/* Terms */}
            <div className="flex items-start gap-2.5 pt-2">
              <input
                id="terms" type="checkbox" checked={form.accept_terms}
                onChange={e => setForm(f => ({ ...f, accept_terms: e.target.checked }))}
                className="mt-0.5 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-400 cursor-pointer"
              />
              <label htmlFor="terms" className="text-sm text-gray-600 cursor-pointer">
                I accept the{" "}
                <a href="#" className="text-blue-600 hover:underline font-medium">Terms and Conditions</a>
              </label>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full py-3 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-xl transition-colors"
            >
              {loading ? "Registering school…" : "Register School"}
            </button>

            <p className="text-sm text-center text-gray-500">
              Already have an account?{" "}
              <Link to="/login" className="text-blue-600 font-medium hover:underline">Sign In</Link>
            </p>
          </form>
        </div>
      </div>

      <div className="text-center text-xs text-gray-400 pb-8">
        © {new Date().getFullYear()} School MIS. All rights reserved.
      </div>
    </div>
  );
}
