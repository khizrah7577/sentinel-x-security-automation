import { useState, type FormEvent } from "react";
import { Badge, Card, DataTable, EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../contexts/AuthContext";
import { api, ApiError } from "../services/api";

type UserRow = {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "analyst";
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
};

export default function UsersPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const list = useApi<UserRow[]>(user?.role === "admin" ? `/users?_=${tick}` : null, [tick]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "analyst">("analyst");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          full_name: fullName,
          password,
          role,
        }),
      });
      setMessage("User created.");
      setEmail("");
      setFullName("");
      setPassword("");
      setTick((t) => t + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  if (user?.role !== "admin") {
    return (
      <div className="space-y-4">
        <PageHeader title="User Management" description="Administrator access required." />
        <EmptyState
          title="Restricted"
          detail="Only admin users can list or create accounts."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="Admin and analyst roles. Password hashes are stored with bcrypt; passwords are never logged."
      />

      {list.loading && <LoadingBlock />}
      {list.error && <ErrorBlock message={list.error} />}
      {list.data && list.data.length === 0 && (
        <EmptyState title="No users" detail="Bootstrap should have created admin/analyst accounts." />
      )}
      {list.data && list.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Email", "Role", "Active", "Last login"]}
          rows={list.data.map((u) => [
            u.id,
            u.full_name,
            u.email,
            <Badge tone={u.role === "admin" ? "info" : "neutral"}>{u.role}</Badge>,
            u.is_active ? <Badge tone="ok">Yes</Badge> : <Badge tone="danger">No</Badge>,
            u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "—",
          ])}
        />
      )}

      <Card>
        <h2 className="text-base font-semibold m-0 mb-3">Create user</h2>
        <form onSubmit={onCreate} className="grid gap-3 md:grid-cols-2">
          <label className="text-sm space-y-1">
            <span>Full name</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-transparent"
              style={{ borderColor: "var(--border)" }}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </label>
          <label className="text-sm space-y-1">
            <span>Email</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-transparent"
              style={{ borderColor: "var(--border)" }}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="text-sm space-y-1">
            <span>Password</span>
            <input
              type="password"
              className="w-full rounded-md border px-3 py-2 bg-transparent"
              style={{ borderColor: "var(--border)" }}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="text-sm space-y-1">
            <span>Role</span>
            <select
              className="w-full rounded-md border px-3 py-2 bg-transparent"
              style={{ borderColor: "var(--border)" }}
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "analyst")}
            >
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-md px-4 py-2 text-sm text-white"
              style={{ background: "var(--accent)" }}
            >
              {busy ? "Creating…" : "Create user"}
            </button>
          </div>
        </form>
        {message && <p className="text-sm mt-3 mb-0" style={{ color: "var(--accent)" }}>{message}</p>}
        {error && <p className="text-sm mt-3 mb-0" style={{ color: "var(--danger)" }}>{error}</p>}
      </Card>
    </div>
  );
}
