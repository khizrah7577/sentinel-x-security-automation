"""
End-to-end integration test for CyberSecurity_FYP.
Run: D:\\CyberSecurity_FYP\\.venv\\Scripts\\python.exe scripts\\e2e_integration_test.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
ROOT = Path(r"D:\CyberSecurity_FYP")


class Results:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed.append(name)
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str) -> None:
        self.failed.append(name)
        print(f"[FAIL] {name} — {detail}")


def main() -> int:
    r = Results()
    client = httpx.Client(timeout=120.0)

    # 1 Health / DB
    try:
        h = client.get("http://127.0.0.1:8000/health").json()
        assert h.get("database", {}).get("status") == "connected"
        r.ok("health_db_connected", f"phase={h.get('phase')}")
    except Exception as exc:
        r.fail("health_db_connected", str(exc))
        _write_report(r)
        return 1

    # 2 Auth success
    try:
        tok = client.post(
            f"{BASE}/auth/login",
            json={"email": "admin@localhost", "password": "ChangeMeAdmin123!"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}
        me = client.get(f"{BASE}/auth/me", headers=headers).json()
        assert me["role"] == "admin"
        r.ok("auth_admin_login")
    except Exception as exc:
        r.fail("auth_admin_login", str(exc))
        _write_report(r)
        return 1

    # 3 Auth failure
    try:
        bad = client.post(
            f"{BASE}/auth/login",
            json={"email": "admin@localhost", "password": "wrong-password"},
        )
        assert bad.status_code == 401
        r.ok("auth_invalid_password_rejected")
    except Exception as exc:
        r.fail("auth_invalid_password_rejected", str(exc))

    # 4 Unauthorized restricted action
    try:
        noauth = client.get(f"{BASE}/users")
        assert noauth.status_code == 401
        r.ok("unauthorized_users_list_rejected")
    except Exception as exc:
        r.fail("unauthorized_users_list_rejected", str(exc))

    # 5 Analyst cannot manage AI key
    try:
        atok = client.post(
            f"{BASE}/auth/login",
            json={"email": "analyst@localhost", "password": "ChangeMeAnalyst123!"},
        ).json()["access_token"]
        aheaders = {"Authorization": f"Bearer {atok}"}
        denied = client.get(f"{BASE}/settings/ai", headers=aheaders)
        assert denied.status_code == 403
        r.ok("analyst_ai_settings_forbidden")
    except Exception as exc:
        r.fail("analyst_ai_settings_forbidden", str(exc))

    # 6 Invalid PCAP upload
    try:
        files = {"file": ("bad.txt", b"not a pcap", "text/plain")}
        up = client.post(f"{BASE}/network/pcaps/upload", headers=headers, files=files)
        assert up.status_code == 400
        r.ok("invalid_pcap_rejected", up.json().get("detail", "")[:80])
    except Exception as exc:
        r.fail("invalid_pcap_rejected", str(exc))

    # 7 Demo PCAP + process
    try:
        demo = client.post(f"{BASE}/network/pcaps/demo", headers=headers).json()
        assert demo["is_demo"] is True
        proc = client.post(f"{BASE}/network/pcaps/{demo['id']}/process", headers=headers).json()
        assert proc["flows"] > 0
        r.ok("pcap_demo_process", f"flows={proc['flows']} suspicious={proc['suspicious_flows']}")
        pcap_id = demo["id"]
    except Exception as exc:
        r.fail("pcap_demo_process", str(exc))
        pcap_id = None

    # 8 Ensure model / train if needed
    try:
        status = client.get(f"{BASE}/ml/status", headers=headers).json()
        if not status.get("active_model"):
            client.post(f"{BASE}/ml/datasets/baseline", headers=headers)
            train = client.post(
                f"{BASE}/ml/train",
                headers=headers,
                json={"model_type": "random_forest", "activate": True},
            )
            assert train.status_code == 200
            status = client.get(f"{BASE}/ml/status", headers=headers).json()
        assert status.get("active_model")
        r.ok("ml_active_model", status["active_model"])
    except Exception as exc:
        r.fail("ml_active_model", str(exc))

    # 9 Predict
    try:
        body = {"limit": 200}
        if pcap_id:
            body["pcap_id"] = pcap_id
        pred = client.post(f"{BASE}/ml/predict", headers=headers, json=body).json()
        assert pred["predictions"] > 0
        r.ok("ml_predict", f"predictions={pred['predictions']} attacks={pred['attacks']}")
    except Exception as exc:
        r.fail("ml_predict", str(exc))

    # 10 Investigate (no OpenAI key — rule-based)
    try:
        preds = client.get(f"{BASE}/ml/predictions?limit=20", headers=headers).json()
        attack = next((p for p in preds if p.get("predicted_label") == "attack"), preds[0])
        inv = client.post(
            f"{BASE}/agents/investigate",
            headers=headers,
            json={"prediction_id": attack["id"]},
        ).json()
        assert inv.get("investigation_id")
        assert len(inv.get("agent_trace") or []) == 5
        r.ok(
            "agent_investigate_rule_based",
            f"id={inv['investigation_id']} severity={inv['severity']} ai={inv['used_openai']}",
        )
        rec_id = inv.get("recommendation_id")
    except Exception as exc:
        r.fail("agent_investigate_rule_based", str(exc))
        rec_id = None

    # 11 Invalid OpenAI key save/test
    try:
        save = client.put(
            f"{BASE}/settings/ai",
            headers=headers,
            json={"api_key": "sk-invalid-key-for-test-only-xxxxxx", "model": "gpt-4o-mini"},
        )
        assert save.status_code == 200
        test = client.post(f"{BASE}/settings/ai/test", headers=headers)
        assert test.status_code == 400
        # remove key again so app stays usable without burning quota expectations
        client.delete(f"{BASE}/settings/ai", headers=headers)
        r.ok("invalid_openai_key_test_fails")
    except Exception as exc:
        r.fail("invalid_openai_key_test_fails", str(exc))
        try:
            client.delete(f"{BASE}/settings/ai", headers=headers)
        except Exception:
            pass

    # 12 Response approve/execute/rollback (or reject path)
    try:
        client.put(
            f"{BASE}/response/mode",
            headers=headers,
            json={"mode": "approval_required"},
        )
        if not rec_id:
            pending = client.get(
                f"{BASE}/response/recommendations?status=pending", headers=headers
            ).json()
            rec_id = pending[0]["id"] if pending else None
        assert rec_id
        approved = client.post(
            f"{BASE}/response/recommendations/{rec_id}/approve",
            headers=headers,
            json={"execute_now": True},
        ).json()
        assert approved["recommendation"]["approval_status"] == "approved"
        executed = approved.get("executed")
        if executed and executed.get("rollback_available") and not executed.get("rolled_back"):
            rb = client.post(
                f"{BASE}/response/executed/{executed['id']}/rollback",
                headers=headers,
            ).json()
            assert rb.get("rolled_back") is True
            r.ok("response_approve_execute_rollback", executed.get("verification_result", "")[:80])
        else:
            r.ok("response_approve_execute", "executed without rollbackable artifact")
    except Exception as exc:
        r.fail("response_approve_execute_rollback", str(exc))

    # 13 Public IP blocked by guardrail
    try:
        sys.path.insert(0, str(ROOT / "backend"))
        from app.response.actions import ActionError, validate_lab_ip

        try:
            validate_lab_ip("1.1.1.1")
            r.fail("public_ip_guardrail", "unexpectedly accepted")
        except ActionError:
            r.ok("public_ip_guardrail")
    except Exception as exc:
        r.fail("public_ip_guardrail", str(exc))

    # 14 Reports export
    try:
        csv_res = client.get(f"{BASE}/reports/incidents.csv", headers=headers)
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers.get("content-type", "")
        js = client.get(f"{BASE}/reports/incidents.json", headers=headers)
        assert js.status_code == 200
        r.ok("reports_csv_json_export")
    except Exception as exc:
        r.fail("reports_csv_json_export", str(exc))

    # 15 Dashboard real data
    try:
        dash = client.get(f"{BASE}/dashboard/stats", headers=headers).json()
        assert "total_network_events" in dash
        r.ok(
            "dashboard_stats",
            f"events={dash['total_network_events']} attacks={dash['detected_attacks']} pending={dash['pending_approvals']}",
        )
    except Exception as exc:
        r.fail("dashboard_stats", str(exc))

    # 16 Predict without model message (simulate by checking endpoint contract when none — skip if model exists)
    try:
        # Invalid CSV import
        files = {"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")}
        bad_ds = client.post(f"{BASE}/ml/datasets/import", headers=headers, files=files)
        assert bad_ds.status_code == 400
        r.ok("invalid_dataset_csv_rejected", str(bad_ds.json().get("detail", ""))[:80])
    except Exception as exc:
        r.fail("invalid_dataset_csv_rejected", str(exc))

    # 17 Frontend reachable
    try:
        fe = httpx.get("http://127.0.0.1:5173", timeout=10.0)
        assert fe.status_code == 200
        r.ok("frontend_reachable")
    except Exception as exc:
        r.fail("frontend_reachable", str(exc))

    _write_report(r)
    print("\n==== SUMMARY ====")
    print(f"Passed: {len(r.passed)}")
    print(f"Failed: {len(r.failed)}")
    if r.failed:
        print("Failures:", ", ".join(r.failed))
        return 1
    return 0


def _write_report(r: Results) -> None:
    out = ROOT / "docs" / "INTEGRATION_TEST_REPORT.md"
    lines = [
        "# Integration Test Report",
        "",
        f"Passed: **{len(r.passed)}**",
        f"Failed: **{len(r.failed)}**",
        "",
        "## Passed",
    ]
    lines += [f"- {x}" for x in r.passed] or ["- (none)"]
    lines += ["", "## Failed"]
    lines += [f"- {x}" for x in r.failed] or ["- (none)"]
    lines += [
        "",
        "## Workflow covered",
        "1. Login",
        "2. PCAP demo upload/process",
        "3. ML predict",
        "4. Agentic investigation",
        "5. Response approve/execute/rollback",
        "6. Reports + dashboard",
        "7. Negative cases (auth, invalid PCAP, invalid key, public IP, bad CSV)",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {out}")


if __name__ == "__main__":
    raise SystemExit(main())
