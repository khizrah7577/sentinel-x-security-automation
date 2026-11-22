import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { api, getWebSocketUrl, getToken } from "../../services/api";

type Notif = {
  id: number;
  title: string;
  body: string;
  severity: string;
  link: string;
  is_read: boolean;
  created_at: string;
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notif[]>([]);

  const load = async () => {
    try {
      const rows = await api<Notif[]>("/automation/notifications?unread_only=false");
      setItems(rows.slice(0, 12));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 15000);
    const token = getToken();
    let ws: WebSocket | null = null;
    if (token) {
      try {
        const wsUrl = getWebSocketUrl("/automation/ws", token);
        ws = new WebSocket(wsUrl);
        ws.onmessage = () => {
          void load();
        };
        ws.onerror = () => {
          /* fail gracefully if websockets are not reachable */
        };
      } catch {
        /* fail gracefully */
      }
    }
    return () => {
      window.clearInterval(id);
      ws?.close();
    };
  }, []);

  const unread = items.filter((i) => !i.is_read).length;

  return (
    <div className="relative">
      <button
        type="button"
        className="rounded-xl border p-2 relative"
        style={{ borderColor: "var(--border)" }}
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full text-[10px] font-bold grid place-items-center"
            style={{ background: "var(--critical)", color: "#fff" }}
          >
            {unread}
          </span>
        )}
      </button>
      {open && (
        <div
          className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-xl border z-50 shadow-lg"
          style={{ background: "var(--elevated)", borderColor: "var(--border)" }}
        >
          <div className="px-3 py-2 border-b flex justify-between items-center" style={{ borderColor: "var(--border)" }}>
            <span className="text-xs font-bold">Notifications</span>
            <Link
              to="/automation/notifications"
              className="text-[11px] font-semibold"
              style={{ color: "var(--accent)" }}
              onClick={() => setOpen(false)}
            >
              Open center
            </Link>
          </div>
          {items.length === 0 && (
            <p className="text-xs p-3 m-0" style={{ color: "var(--muted)" }}>
              No notifications yet.
            </p>
          )}
          {items.map((n) => (
            <Link
              key={n.id}
              to={n.link || "/automation/notifications"}
              className="block px-3 py-2 border-b no-underline"
              style={{ borderColor: "var(--border)", color: "var(--text)", opacity: n.is_read ? 0.7 : 1 }}
              onClick={() => setOpen(false)}
            >
              <div className="text-xs font-semibold">{n.title}</div>
              <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                {(n.body || "").slice(0, 90)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
