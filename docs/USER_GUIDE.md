# User Guide

## Login

- URL: http://127.0.0.1:5173
- Admin: `admin@localhost` / `ChangeMeAdmin123!`
- Analyst: `analyst@localhost` / `ChangeMeAnalyst123!`

Change passwords after first use in a shared lab.

## Typical demo path

1. **PCAP Analysis** → Create labelled demo PCAP → Process
2. **ML Models** → Train all (or use existing active model) → Run predictions
3. **Attack Detection** → Review ML results
4. **AI Investigation** → Investigate top ML attacks
5. **Response Center** → Approve / Reject / Rollback
6. **Reports** → Download CSV/JSON
7. **Settings** → Theme + AI Configuration (optional OpenAI key)

## Roles

| Capability | Admin | Analyst |
|------------|-------|---------|
| View dashboards / events | Yes | Yes |
| Train/activate models | Yes | No |
| Manage OpenAI key | Yes | No |
| Approve/execute responses | Yes | No |
| Create users | Yes | No |

## Themes

Settings → Theme: Light / Dark / System. Preference is stored in the browser.

## AI without a key

All monitoring, PCAP, ML, and basic incident features work without OpenAI.  
Investigation still runs with a **rule-based** path and shows a Settings link when AI is not configured.
