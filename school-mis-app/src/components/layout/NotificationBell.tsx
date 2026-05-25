/**
 * NotificationBell — topbar notification dropdown.
 * Polls every 60 seconds for unread count.
 */

import { useState, useEffect, useRef } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { getNotifications, getUnreadCount, markRead, markAllRead, type Notification } from "@/api/notifications";

export default function NotificationBell() {
  const [count,    setCount]    = useState(0);
  const [open,     setOpen]     = useState(false);
  const [notifs,   setNotifs]   = useState<Notification[]>([]);
  const [loading,  setLoading]  = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Poll unread count every 60s
  useEffect(() => {
    const fetchCount = () => getUnreadCount().then(setCount).catch(() => {});
    fetchCount();
    const id = setInterval(fetchCount, 60_000);
    return () => clearInterval(id);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const openPanel = async () => {
    setOpen((o) => !o);
    if (!open) {
      setLoading(true);
      try {
        const data = await getNotifications(false, 30);
        setNotifs(data);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleRead = async (id: number) => {
    await markRead(id).catch(() => {});
    setNotifs((prev) => prev.map((n) => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
    setCount((c) => Math.max(0, c - 1));
  };

  const handleMarkAll = async () => {
    await markAllRead().catch(() => {});
    setNotifs((prev) => prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
    setCount(0);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={openPanel}
        className="relative p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        title="Notifications"
      >
        <Bell size={18} />
        {count > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-2xs rounded-full flex items-center justify-center font-bold leading-none">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="text-sm font-semibold text-gray-900">Notifications</span>
            {count > 0 && (
              <button
                onClick={handleMarkAll}
                className="flex items-center gap-1 text-xs text-violet-600 hover:text-violet-800 transition-colors"
              >
                <CheckCheck size={13} />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
            {loading ? (
              <div className="py-8 text-center text-sm text-gray-400">Loading…</div>
            ) : notifs.length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">No notifications</div>
            ) : (
              notifs.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.read_at && handleRead(n.id)}
                  className={[
                    "px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors",
                    !n.read_at ? "bg-violet-50/60" : "",
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className={["text-xs font-medium text-gray-900 truncate", !n.read_at ? "font-semibold" : ""].join(" ")}>
                        {n.title}
                      </p>
                      {n.body && (
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                      )}
                      <p className="text-2xs text-gray-400 mt-1">
                        {new Date(n.created_at).toLocaleString()}
                      </p>
                    </div>
                    {!n.read_at && (
                      <div className="w-2 h-2 mt-1 flex-shrink-0 rounded-full bg-violet-500" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
