/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sidebar: {
          bg:      "#0F172A",
          item:    "rgba(255,255,255,0.08)",
          active:  "rgba(255,255,255,0.14)",
          border:  "#1E293B",
          text:    "#94A3B8",
          heading: "#475569",
        },
        grade: {
          a: "#059669",
          b: "#0891B2",
          c: "#D97706",
          d: "#EA580C",
          f: "#DC2626",
        },
        status: {
          draft:    "#F59E0B",
          locked:   "#3B82F6",
          approved: "#059669",
          empty:    "#9CA3AF",
        },
      },
      fontSize: {
        "2xs": ["10px", "14px"],
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
      },
      animation: {
        "pulse-fast": "pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
