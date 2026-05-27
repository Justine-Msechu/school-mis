import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen, Users, GraduationCap, DollarSign, Bus, Package,
  Heart, BarChart2, Shield, Bell, Calendar, Clock, Check,
  Menu, X, Mail, Phone, MapPin, ChevronRight,
} from "lucide-react";

const FEATURES = [
  { icon: Users,         title: "Student Admission & Records",  desc: "Manage student enrollment, profiles, and complete academic history in one place." },
  { icon: GraduationCap, title: "Staff Management",             desc: "Track teachers, support staff, payroll, and leave records efficiently." },
  { icon: BookOpen,      title: "Academic Records & Results",   desc: "Enter grades, generate report cards, and publish results with ease." },
  { icon: Calendar,      title: "Timetable Management",         desc: "Build and share class timetables for teachers and students automatically." },
  { icon: Clock,         title: "Attendance Tracking",          desc: "Mark and monitor daily attendance with real-time reports and alerts." },
  { icon: DollarSign,    title: "Financial Management",         desc: "Collect fees, manage expenses, and generate financial reports." },
  { icon: Bell,          title: "SMS Notifications",            desc: "Send instant alerts to parents about fees, results, and school events." },
  { icon: BarChart2,     title: "Analytics Dashboard",          desc: "Get data-driven insights on student performance, attendance, and finances." },
  { icon: Shield,        title: "Secure Access Control",        desc: "Role-based permissions ensure every user sees only what they should." },
];

const STATS = [
  { value: "500+",   label: "Schools Registered" },
  { value: "200K+",  label: "Students Managed" },
  { value: "99.9%",  label: "System Uptime" },
  { value: "24/7",   label: "Support Available" },
];

const PLANS = [
  {
    name: "Basic",
    color: "#0891B2",
    desc: "Perfect for small schools just getting started.",
    features: [
      "Up to 25 staff accounts",
      "Up to 300 students",
      "Students, Classes & Attendance",
      "Grades & Report Cards",
      "Basic Finance & Fees",
      "Email support",
    ],
  },
  {
    name: "Standard",
    color: "#7C3AED",
    desc: "Everything you need to run a full school.",
    popular: true,
    features: [
      "Up to 100 staff accounts",
      "Up to 1,000 students",
      "Everything in Basic",
      "Payroll Management",
      "Transport & Inventory",
      "Library & Welfare",
      "NGO Partners",
      "Advanced Reports",
      "Priority support",
    ],
  },
  {
    name: "Premium",
    color: "#059669",
    desc: "Unlimited power for large schools and networks.",
    features: [
      "Up to 500 staff accounts",
      "Up to 5,000 students",
      "Everything in Standard",
      "AI Chat Assistant",
      "Multi-school network",
      "API access",
      "Dedicated support",
    ],
  },
];

const HOW_IT_WORKS = [
  { step: "1", title: "Register your school",  desc: "Fill in your school details and create an admin account. Takes less than 5 minutes." },
  { step: "2", title: "Set up your school",    desc: "Add your classes, teachers, and students. Import existing data easily." },
  { step: "3", title: "Go live",               desc: "Start managing attendance, grades, fees, and more from day one." },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [contact, setContact] = useState({ name: "", email: "", phone: "", school: "", message: "" });

  const navLinks = [
    { label: "Home",         href: "#home" },
    { label: "Features",     href: "#features" },
    { label: "How it works", href: "#how" },
    { label: "Pricing",      href: "#pricing" },
    { label: "Contact",      href: "#contact" },
  ];

  return (
    <div className="min-h-screen bg-white font-sans">
      {/* ── Navbar ─────────────────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-100 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <BookOpen size={16} className="text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">School MIS</span>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6">
            {navLinks.map(l => (
              <a key={l.label} href={l.href} className="text-sm text-gray-600 hover:text-blue-600 transition-colors font-medium">
                {l.label}
              </a>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-3">
            <button onClick={() => navigate("/login")} className="text-sm font-semibold text-blue-600 hover:text-blue-700 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors">
              Login
            </button>
            <button onClick={() => navigate("/register")} className="text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors">
              Register your School
            </button>
          </div>

          {/* Mobile menu toggle */}
          <button className="md:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100" onClick={() => setMenuOpen(v => !v)}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile nav */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-100 bg-white px-4 py-3 flex flex-col gap-2">
            {navLinks.map(l => (
              <a key={l.label} href={l.href} onClick={() => setMenuOpen(false)} className="py-2 text-sm text-gray-700 font-medium">
                {l.label}
              </a>
            ))}
            <div className="flex gap-2 pt-2 border-t border-gray-100">
              <button onClick={() => navigate("/login")} className="flex-1 py-2 text-sm font-semibold text-blue-600 border border-blue-200 rounded-lg">Login</button>
              <button onClick={() => navigate("/register")} className="flex-1 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg">Register</button>
            </div>
          </div>
        )}
      </header>

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section id="home" className="pt-32 pb-20 px-4 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Web-based School Management Platform
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-5">
            Complete School Management System<br className="hidden md:block" />
            <span className="text-blue-600"> for Modern Education</span>
          </h1>
          <p className="text-lg text-gray-500 mb-10 max-w-2xl mx-auto">
            Web-based platform integrating students, parents, teachers, and administration
            for seamless educational management.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate("/register")}
              className="flex items-center gap-2 px-7 py-3.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-200 transition-colors"
            >
              Register your School
              <ChevronRight size={18} />
            </button>
            <button
              onClick={() => navigate("/login")}
              className="px-7 py-3.5 text-base font-semibold text-blue-600 border-2 border-blue-200 hover:border-blue-400 rounded-xl transition-colors"
            >
              Sign in to your account
            </button>
          </div>
        </div>
      </section>

      {/* ── Stats strip ────────────────────────────────────────────────────── */}
      <section className="bg-blue-600 py-10 px-4">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-bold text-white">{s.value}</p>
              <p className="text-sm text-blue-100 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────────────────── */}
      <section id="features" className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Everything your school needs</h2>
            <p className="text-gray-500 max-w-xl mx-auto">
              A complete set of tools to run your school efficiently — from admissions to alumni.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-white rounded-2xl p-6 border border-gray-100 hover:shadow-md transition-shadow">
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center mb-4">
                  <Icon size={20} className="text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────────────────── */}
      <section id="how" className="py-20 px-4 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Get started in minutes</h2>
            <p className="text-gray-500">No technical skills required. Your school can be live today.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map(({ step, title, desc }) => (
              <div key={step} className="text-center">
                <div className="w-12 h-12 rounded-full bg-blue-600 text-white text-xl font-bold flex items-center justify-center mx-auto mb-4">
                  {step}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-12 bg-blue-50 border border-blue-100 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <p className="font-bold text-gray-900 text-lg mb-1">Ready to get started?</p>
              <p className="text-gray-500 text-sm">Join 500+ schools already using School MIS. Free 30-day trial.</p>
              <ul className="mt-3 space-y-1.5">
                {["No credit card required", "Full access during trial", "Dedicated onboarding support"].map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                    <Check size={14} className="text-blue-600 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <button
              onClick={() => navigate("/register")}
              className="flex-shrink-0 px-7 py-3.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-md transition-colors"
            >
              Register your School
            </button>
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Simple, transparent pricing</h2>
            <p className="text-gray-500 max-w-xl mx-auto">
              Choose the plan that fits your school. All plans include a 30-day free trial.
              Contact us for exact pricing in your currency.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={`relative bg-white rounded-2xl border-2 p-6 flex flex-col shadow-sm ${
                  p.popular ? "border-violet-500 shadow-violet-100" : "border-gray-100"
                }`}
              >
                {p.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-violet-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                )}
                <div className="mb-4">
                  <div
                    className="inline-block w-10 h-10 rounded-xl mb-3"
                    style={{ backgroundColor: `${p.color}20` }}
                  >
                    <div
                      className="w-full h-full rounded-xl flex items-center justify-center"
                      style={{ color: p.color }}
                    >
                      <GraduationCap size={20} />
                    </div>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{p.desc}</p>
                </div>
                <ul className="space-y-2 flex-1 mb-6">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                      <Check size={14} className="mt-0.5 flex-shrink-0 text-green-500" />
                      {f}
                    </li>
                  ))}
                </ul>
                <a
                  href="#contact"
                  className="block text-center py-2.5 rounded-xl text-sm font-semibold transition-colors"
                  style={
                    p.popular
                      ? { backgroundColor: p.color, color: "#fff" }
                      : { border: `2px solid ${p.color}`, color: p.color }
                  }
                >
                  Get in touch
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Contact ────────────────────────────────────────────────────────── */}
      <section id="contact" className="py-20 px-4 bg-white">
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-12">
          {/* Info */}
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Get in touch</h2>
            <p className="text-gray-500 mb-8">Have questions? Our team is happy to help you get started.</p>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <MapPin size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-gray-600">Arusha, Tanzania</p>
              </div>
              <div className="flex items-start gap-3">
                <Mail size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-gray-600">support@youthtech.or.tz</p>
              </div>
              <div className="flex items-start gap-3">
                <Phone size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-gray-600">+255 764454097</p>
              </div>
            </div>
          </div>

          {/* Contact form */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Full Name</label>
                  <input value={contact.name} onChange={e => setContact(c => ({...c, name: e.target.value}))}
                    placeholder="John Mwangi" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                  <input type="email" value={contact.email} onChange={e => setContact(c => ({...c, email: e.target.value}))}
                    placeholder="john@school.tz" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                  <input value={contact.phone} onChange={e => setContact(c => ({...c, phone: e.target.value}))}
                    placeholder="+255 700 000 000" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">School Name</label>
                  <input value={contact.school} onChange={e => setContact(c => ({...c, school: e.target.value}))}
                    placeholder="Sunrise Primary" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Message</label>
                <textarea value={contact.message} onChange={e => setContact(c => ({...c, message: e.target.value}))}
                  rows={4} placeholder="Tell us about your school…"
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none" />
              </div>
              <button className="w-full py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors">
                Send Message
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="bg-gray-900 text-gray-400 py-12 px-4">
        <div className="max-w-6xl mx-auto grid sm:grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
                <BookOpen size={13} className="text-white" />
              </div>
              <span className="font-bold text-white text-sm">School MIS</span>
            </div>
            <p className="text-xs leading-relaxed">Complete school management for modern education. Built for African schools.</p>
          </div>
          <div>
            <p className="font-semibold text-white text-sm mb-3">Quick Links</p>
            <ul className="space-y-2 text-xs">
              {["Home", "Features", "How it works", "Contact"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition-colors">{l}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white text-sm mb-3">Services</p>
            <ul className="space-y-2 text-xs">
              {["Student Management", "Finance & Fees", "Attendance", "Report Cards", "Transport"].map(l => (
                <li key={l}><span>{l}</span></li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white text-sm mb-3">Support & Legal</p>
            <ul className="space-y-2 text-xs">
              {["Help Center", "Privacy Policy", "Terms of Service", "Cookie Policy"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition-colors">{l}</a></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-6 text-center text-xs">
          © {new Date().getFullYear()} School MIS. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
