import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { BookOpen, Building2, User, Lock, Phone, Mail, Eye, EyeOff } from "lucide-react";
import { registerSchool } from "@/api/schools";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    school_name:    "",
    school_email:   "",
    contact_phone:  "",
    admin_fullname: "",
    admin_username: "",
    admin_password: "",
    confirm_password: "",
  });
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [success, setSuccess]   = useState("");

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (form.admin_password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    if (form.admin_password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await registerSchool({
        school_name:    form.school_name.trim(),
        school_email:   form.school_email.trim(),
        contact_phone:  form.contact_phone.trim(),
        admin_fullname: form.admin_fullname.trim(),
        admin_username: form.admin_username.trim(),
        admin_password: form.admin_password,
      });
      setSuccess(res.data.message);
      setTimeout(() => navigate("/login"), 2500);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-xl p-10 w-full max-w-sm text-center">
          <div className="w-14 h-14 rounded-2xl bg-green-50 border border-green-100 flex items-center justify-center mx-auto mb-4">
            <BookOpen size={24} className="text-green-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Registration successful!</h2>
          <p className="text-sm text-gray-500 mb-1">{success}</p>
          <p className="text-xs text-gray-400">Redirecting to login…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Brand */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-xl bg-violet-600 flex items-center justify-center">
            <BookOpen size={18} className="text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">School MIS</span>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-xl p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Register your school</h1>
          <p className="text-sm text-gray-500 mb-6">30-day free trial · No credit card required</p>

          {error && (
            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* School info */}
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">School information</p>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">School name *</label>
                <div className="relative">
                  <Building2 size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text" required value={form.school_name} onChange={set("school_name")}
                    placeholder="Sunrise Primary School"
                    className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">School email</label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email" value={form.school_email} onChange={set("school_email")}
                      placeholder="info@school.ac.tz"
                      className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <div className="relative">
                    <Phone size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="tel" value={form.contact_phone} onChange={set("contact_phone")}
                      placeholder="+255 700 000 000"
                      className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Admin account */}
            <div className="space-y-3 pt-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Admin account</p>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full name *</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text" required value={form.admin_fullname} onChange={set("admin_fullname")}
                    placeholder="John Mwangi"
                    className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text" required value={form.admin_username} onChange={set("admin_username")}
                    placeholder="john.mwangi"
                    className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type={showPw ? "text" : "password"} required value={form.admin_password}
                      onChange={set("admin_password")} placeholder="Min. 8 characters"
                      className="w-full pl-9 pr-9 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                    />
                    <button
                      type="button" onClick={() => setShowPw((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                    >
                      {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confirm *</label>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type={showPw ? "text" : "password"} required value={form.confirm_password}
                      onChange={set("confirm_password")} placeholder="Repeat password"
                      className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
                    />
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full py-3 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-60 rounded-xl transition-colors mt-2"
            >
              {loading ? "Creating account…" : "Create school account"}
            </button>
          </form>

          <p className="text-sm text-center text-gray-500 mt-4">
            Already have an account?{" "}
            <Link to="/login" className="text-violet-600 font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
