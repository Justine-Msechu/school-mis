import ReactDOM from "react-dom/client";
import App from "./App";
import { ToastProvider } from "./components/ui/Toast";
import { installGlobalErrorHandlers } from "./components/ui/ErrorBoundary";
import "./index.css";

installGlobalErrorHandlers();

// Remove the HTML skeleton the instant React takes over — no flash.
const skeleton = document.getElementById("app-skeleton");
if (skeleton) skeleton.remove();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <ToastProvider>
    <App />
  </ToastProvider>
);
