"""Generate easy-English SENTINEL X project explanation DOCX."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

out = Path(r"D:\CyberSecurity_FYP\docs\SENTINEL_X_Project_Explanation.docx")
doc = Document()

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)


def para(text: str, bold: bool = False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(11)
    return p


def bullets(items: list[str]):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


title = doc.add_heading("SENTINEL X", 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("Intelligent Cybersecurity & Threat Response Platform")
r.bold = True
r.font.size = Pt(14)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Project Explanation (Easy English)\nFinal Year Project Document").italic = True

para(
    "This document explains the SENTINEL X project in simple words. "
    "It covers what the system is, why it was built, how it works, and what features it includes."
)

doc.add_heading("1. What is SENTINEL X?", level=1)
para(
    "SENTINEL X is a smart cybersecurity software platform. It helps security teams find cyber "
    "attacks in network traffic, understand what happened, and respond in a safe and controlled way."
)
para(
    "Think of it like a digital security operations center (SOC) for a lab or academic environment. "
    "It watches network data, uses machine learning to detect attacks, uses AI agents to investigate, "
    "and helps admins take approved defensive actions."
)
para(
    "Important: This is an academic Final Year Project prototype. It is designed for controlled / "
    "offline lab use. It is not meant to freely attack or block systems on the public internet."
)

doc.add_heading("2. Why was this project built?", level=1)
bullets(
    [
        "Cyber attacks are increasing, and security teams need faster detection.",
        "Many tools detect threats but do not explain them clearly.",
        "Manual investigation takes a lot of time.",
        "Automated response is risky if it is not carefully controlled.",
        "Students and researchers need a full end-to-end system that combines ML, AI agents, automation, and a modern dashboard.",
    ]
)
para("SENTINEL X was built to show a complete pipeline:")
bullets(
    [
        "Collect or upload network traffic (PCAP files).",
        "Detect attacks with machine learning.",
        "Investigate with AI agents.",
        "Create incidents and recommendations.",
        "Ask an admin for approval before risky actions.",
        "Keep records, reports, and notifications.",
    ]
)

doc.add_heading("3. Who can use it?", level=1)
doc.add_heading("Administrator", level=3)
bullets(
    [
        "Full access to settings, users, response approvals, and automation.",
        "Can approve or reject defensive actions.",
        "Can configure OpenAI API key safely in Settings.",
        "Can manage workflows, scheduler tasks, and response policies.",
    ]
)
doc.add_heading("Analyst", level=3)
bullets(
    [
        "Can view dashboards, detections, investigations, and reports.",
        "Can upload PCAPs and run analysis.",
        "Cannot perform high-risk admin-only actions.",
    ]
)

doc.add_heading("4. Main features (simple list)", level=1)

doc.add_heading("4.1 Login and user roles", level=2)
bullets(
    [
        "Secure login with email and password.",
        "Passwords are stored in hashed form (not plain text).",
        "Two roles: Admin and Analyst.",
        "Only authorized users can open the SOC screens.",
    ]
)

doc.add_heading("4.2 Dashboard and visualizations", level=2)
bullets(
    [
        "Home dashboard with key security numbers.",
        "Graphs and charts for threats and activity.",
        "Modern Graphite Emerald theme.",
        "Light mode and dark mode.",
        "Easy navigation with a sidebar.",
    ]
)

doc.add_heading("4.3 Network monitoring", level=2)
bullets(
    [
        "View network events and traffic information.",
        "Monitor activity related to the project lab environment.",
        "See source IP, destination IP, ports, and protocols where available.",
    ]
)

doc.add_heading("4.4 PCAP analysis", level=2)
bullets(
    [
        "Upload PCAP / PCAPNG capture files.",
        "Extract flow features from the traffic.",
        "Store file metadata in the database.",
        "Keep the actual PCAP files on disk (not inside the database).",
        "Optional Zeek support for deeper log analysis in lab setups.",
    ]
)

doc.add_heading("4.5 Machine Learning (ML) attack detection", level=2)
bullets(
    [
        "Train and manage ML models (for example Random Forest, SVM, Isolation Forest).",
        "Import or prepare datasets.",
        "Run predictions on network flows / PCAP-derived features.",
        "Show predicted label (normal or attack), category, severity, and confidence.",
        "ML detection still works even if OpenAI is not configured.",
    ]
)

doc.add_heading("4.6 AI investigation (LangGraph agents)", level=2)
para(
    "When a suspicious event is found, SENTINEL X can start an investigation using multiple AI agents. "
    "These agents work together like a small investigation team."
)
bullets(
    [
        "Collect related evidence (logs, flow details, ML prediction).",
        "Study source and destination IPs, ports, protocols, and timing.",
        "Suggest possible attack categories.",
        "Estimate severity and confidence.",
        "Separate clear facts from uncertain guesses.",
        "Write an investigation summary.",
        "Save the full investigation in the database.",
    ]
)
para(
    "If the OpenAI API key is missing, the system does not invent fake AI answers. "
    "It continues with rule-based / non-OpenAI investigation support and clearly shows that AI is unavailable or limited."
)

doc.add_heading("4.7 Incident management", level=2)
bullets(
    [
        "Create security incidents from detections.",
        "Track incident status.",
        "Link incidents to predictions and investigations.",
        "Avoid creating duplicate incidents for the same event where possible.",
    ]
)

doc.add_heading("4.8 Response Center (safe automated defense)", level=2)
bullets(
    [
        "Create response recommendations (for example create alert, recommend block, temporary lab firewall rule).",
        "Admin approval is required for disruptive actions by default.",
        "Only allowlisted (pre-approved) actions are allowed.",
        "No free-form shell commands from the AI.",
        "IP and parameter validation.",
        "Public / third-party blocking is restricted.",
        "Lab-only firewall automation for authorized isolated environments.",
        "Verify whether an action succeeded.",
        "Support expiration and rollback for temporary changes.",
        "Keep full audit logs.",
    ]
)
para("Important safety rule: an uncertain ML prediction alone is never enough for automatic blocking.")

doc.add_heading("4.9 Automation Center", level=2)
para("This is the smart SOC automation area of SENTINEL X.")
bullets(
    [
        "Automation Overview — see workflows, jobs, and activity at a glance.",
        "Workflow Builder — create rules using TRIGGER → CONDITION → ACTION.",
        "Active Workflows — enable or disable live workflows.",
        "Agent Scheduler — run recurring tasks (health checks, summaries, cleanup, etc.).",
        "Response Automation — configure safe response policies.",
        "Notification Rules — decide what events create alerts.",
        "Automation History — see what ran, what succeeded, and what failed.",
    ]
)
para("Example workflow:")
bullets(
    [
        "Trigger: New suspicious network event / ML attack prediction.",
        "Condition: Severity is High or Critical.",
        "Action: Create incident, start AI investigation, notify administrator.",
    ]
)

doc.add_heading("4.10 Real-time notifications", level=2)
bullets(
    [
        "In-app notification center and header bell.",
        "Alerts for critical threats, new investigations, failures, and pending approvals.",
        "Real-time updates using WebSockets where configured.",
    ]
)

doc.add_heading("4.11 Reports", level=2)
bullets(
    [
        "Generate security reports from incidents and system activity.",
        "Useful for demos, reviews, and academic presentation.",
    ]
)

doc.add_heading("4.12 Settings and OpenAI configuration", level=2)
bullets(
    [
        "Configure the OpenAI API key at runtime through Settings.",
        "The key is handled on the backend and stored securely (encrypted secret store).",
        "The frontend never shows the full secret key after saving.",
        "Core ML detection works without any OpenAI key.",
    ]
)

doc.add_heading("4.13 Docker deployment", level=2)
bullets(
    [
        "Local start with Docker Desktop using start.bat.",
        "Services: frontend, backend, PostgreSQL, and nginx reverse proxy.",
        "Persistent data kept on the D: drive.",
        "Backup and restore scripts.",
        "Cloud-ready production compose file for Oracle Cloud Always Free (Ubuntu ARM64).",
    ]
)

doc.add_heading("5. How the system works (simple flow)", level=1)
para("Here is the easy end-to-end flow:")
bullets(
    [
        "1. A PCAP is uploaded or a network event is recorded.",
        "2. The system validates and stores the event/file metadata.",
        "3. The active ML model analyzes the traffic features.",
        "4. If an attack is predicted with enough severity/confidence, an incident can be created automatically.",
        "5. An investigation workflow can start (AI agents + evidence).",
        "6. The dashboard and notifications update.",
        "7. A response recommendation may be created.",
        "8. An administrator reviews and approves risky actions.",
        "9. The approved action is executed, verified, and logged.",
        "10. Reports and history remain available for review.",
    ]
)

doc.add_heading("6. Technology stack (easy words)", level=1)
bullets(
    [
        "Frontend: React (modern web interface).",
        "Backend: FastAPI (Python web API).",
        "Database: PostgreSQL (stores users, incidents, predictions, investigations, automation history).",
        "Machine Learning: scikit-learn models.",
        "AI Agents: LangGraph-based multi-agent workflow.",
        "Network parsing: Scapy (and optional Zeek).",
        "Automation scheduling: APScheduler inside the backend.",
        "Deployment: Docker + Docker Compose + nginx.",
    ]
)

doc.add_heading("7. What is stored where?", level=1)
bullets(
    [
        "Database: users, incidents, predictions, investigations, workflows, notifications, approvals, report metadata.",
        "Disk storage: PCAP files, trained ML model files, logs, generated reports, encrypted secrets.",
        "Large PCAP files are not stored inside PostgreSQL.",
    ]
)

doc.add_heading("8. Security design (important points)", level=1)
bullets(
    [
        "Role-based access control (Admin / Analyst).",
        "Secure password hashing.",
        "Backend-only secret handling for OpenAI keys.",
        "Restricted CORS and API validation.",
        "Allowlisted response actions only.",
        "Approval required for disruptive actions by default.",
        "Audit logging for important actions.",
        "Database is not exposed publicly in production Docker setup.",
        "Attack lab machines and unrestricted firewall control are not published to the internet.",
    ]
)

doc.add_heading("9. What SENTINEL X does NOT do", level=1)
bullets(
    [
        "It does not invent fake network attacks or fake AI investigation results.",
        "It does not let the AI run random shell commands.",
        "It does not automatically block public internet systems.",
        "It does not replace a full commercial enterprise SOC product.",
        "It is a learning and research prototype for controlled environments.",
    ]
)

doc.add_heading("10. How to start (local Docker)", level=1)
bullets(
    [
        "Open the project folder: D:\\CyberSecurity_FYP",
        "Run start.bat",
        "Open http://127.0.0.1:8080 in your browser",
        "Login with the default admin account (change the password after first login)",
        "Use status.bat, logs.bat, backup.bat, and stop.bat as needed",
    ]
)

doc.add_heading("11. Summary", level=1)
para(
    "SENTINEL X is a complete academic cybersecurity platform that connects detection, investigation, "
    "automation, and safe response in one system. It gives students and examiners a clear, visual, and "
    "practical demonstration of modern Security Operations Center ideas using machine learning and AI "
    "agents — with strong safety controls."
)

end = doc.add_paragraph()
end.add_run("Document location: ").bold = True
end.add_run(str(out))

doc.save(out)
print(f"Wrote {out}")
print(f"Size={out.stat().st_size}")
