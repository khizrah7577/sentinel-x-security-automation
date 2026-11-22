# FYP Demonstration Guide (10–15 minutes)

## Before you start

1. Docker Desktop running  
2. `D:\CyberSecurity_FYP\start.bat`  
3. Browser: http://127.0.0.1:5173  
4. Login as admin  

Optional: configure OpenAI in **Settings → AI Configuration** for LLM narratives (not required).

## Script

### 1. Overview (1 min)
Show live dashboard counts (not fake zeros if demo data already processed). Mention offline/PCAP-first mode.

### 2. PCAP pipeline (3 min)
- Open **PCAP Analysis**
- Create **labelled demo PCAP** (`is_demo=true`)
- Click **Process**
- Show extracted flows + suspicious heuristic labels
- Emphasize files on `D:\...\data\pcaps`, metadata in Postgres

### 3. ML detection (3 min)
- Open **ML Models**
- If needed: **Train all + activate best F1**
- **Run predictions on flows**
- Open **Attack Detection** and show confidence/severity/evidence JSON

### 4. Agentic investigation (3 min)
- Open **AI Investigation**
- **Investigate top ML attacks**
- Open timeline — five agents
- Note evidence-bound reasoning; AI key optional

### 5. Response + safety (3 min)
- Open **Response Center**
- Show mode `approval_required`
- **Approve** a block recommendation → simulated lab firewall rule
- **Rollback** (optional)
- State clearly: allowlisted actions only, lab private IPs only, not a commercial IPS

### 6. Reports (1 min)
Download incidents CSV/JSON from **Reports**.

## Talking points for examiners

- Academic prototype for controlled/offline environments  
- ML independent of LLM  
- Runtime API key via UI, never hardcoded  
- Persistent storage on D: for C: disk constraints  
- Integration tests documented in `docs/INTEGRATION_TEST_REPORT.md`
