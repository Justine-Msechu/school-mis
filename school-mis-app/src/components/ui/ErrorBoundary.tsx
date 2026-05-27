import { Component, type ReactNode, type ErrorInfo } from "react";
import { reportFrontendError } from "@/api/errorLogs";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props  { children: ReactNode; fallback?: ReactNode; }
interface State  { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    reportFrontendError({
      message:    error.message,
      stack:      error.stack,
      path:       window.location.pathname,
      error_type: error.name,
      context:    { componentStack: info.componentStack?.slice(0, 2000) },
    });
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] p-8 gap-4">
          <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
            <AlertTriangle size={28} className="text-red-600" />
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold text-gray-900">Something went wrong</p>
            <p className="text-sm text-gray-500 mt-1 max-w-sm">
              {this.state.error.message || "An unexpected error occurred on this page."}
            </p>
          </div>
          <button
            onClick={() => { this.setState({ error: null }); window.location.reload(); }}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white text-sm font-semibold rounded-xl hover:bg-violet-700"
          >
            <RefreshCw size={14} /> Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Install global unhandled-error catchers once. */
export function installGlobalErrorHandlers() {
  window.addEventListener("error", (e) => {
    reportFrontendError({
      message:    e.message || "Script error",
      stack:      e.error?.stack,
      path:       window.location.pathname,
      error_type: "GlobalError",
      context:    { filename: e.filename, lineno: e.lineno, colno: e.colno },
    });
  });

  window.addEventListener("unhandledrejection", (e) => {
    const err = e.reason;
    // Ignore network/auth errors — those are expected and already handled
    if (err?.response?.status === 401 || err?.response?.status === 402) return;
    reportFrontendError({
      message:    err?.message || String(err) || "Unhandled promise rejection",
      stack:      err?.stack,
      path:       window.location.pathname,
      error_type: "UnhandledRejection",
    });
  });
}
