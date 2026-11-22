import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/nexus/primitives";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const [email, setEmail] = useState("admin@localhost");
  const [password, setPassword] = useState("ChangeMeAdmin123!");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2" style={{ color: "var(--text)" }}>
      <div
        className="relative hidden lg:flex flex-col justify-between p-10 nexus-grid-bg overflow-hidden"
        style={{ background: "var(--bg)" }}
      >
        <div
          className="absolute inset-0 opacity-80"
          style={{
            background:
              "radial-gradient(700px 400px at 20% 20%, color-mix(in srgb, var(--accent) 20%, transparent), transparent), radial-gradient(500px 300px at 80% 70%, color-mix(in srgb, var(--accent-ai) 14%, transparent), transparent)",
          }}
        />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-2xl grid place-items-center"
              style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs font-bold tracking-[0.2em] uppercase" style={{ color: "var(--accent)" }}>
                SENTINEL X
              </div>
              <div className="text-sm font-semibold" style={{ color: "var(--muted)" }}>
                Intelligent Cybersecurity & Threat Response Platform
              </div>
            </div>
          </div>
        </div>
        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-extrabold leading-tight m-0">
            Agentic SOC for controlled network environments
          </h1>
          <p className="text-sm mt-4 leading-relaxed" style={{ color: "var(--muted)" }}>
            Offline PCAP ingest, ML detection, evidence-bound agents, and allowlisted response — built for demonstration
            and lab isolation.
          </p>
        </div>
        <p className="relative z-10 text-xs" style={{ color: "var(--muted)" }}>
          Academic prototype · Persistent data on D: · No synthetic live feeds
        </p>
      </div>

      <div className="flex items-center justify-center p-6" style={{ background: "var(--bg-secondary)" }}>
        <motion.form
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={onSubmit}
          className="w-full max-w-md rounded-[18px] border p-8 space-y-5"
          style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--glow-accent)" }}
        >
          <div>
            <h2 className="text-2xl font-extrabold m-0">Sign in</h2>
            <p className="text-sm mt-1 mb-0" style={{ color: "var(--muted)" }}>
              Access the SENTINEL X operations console
            </p>
          </div>

          <label className="block text-sm space-y-1.5">
            <span className="font-medium">Email</span>
            <input
              className="w-full rounded-xl border px-3 py-2.5 bg-transparent outline-none"
              style={{ borderColor: "var(--border)" }}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block text-sm space-y-1.5">
            <span className="font-medium">Password</span>
            <input
              type="password"
              className="w-full rounded-xl border px-3 py-2.5 bg-transparent outline-none"
              style={{ borderColor: "var(--border)" }}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error && (
            <p className="text-sm m-0" style={{ color: "var(--critical)" }}>
              {error}
            </p>
          )}

          <Button type="submit" disabled={submitting} className="w-full py-2.5">
            {submitting ? "Signing in…" : "Enter console"}
          </Button>
        </motion.form>
      </div>
    </div>
  );
}
