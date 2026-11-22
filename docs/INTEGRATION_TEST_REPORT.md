# Integration Test Report

Passed: **17**
Failed: **0**

## Passed
- health_db_connected
- auth_admin_login
- auth_invalid_password_rejected
- unauthorized_users_list_rejected
- analyst_ai_settings_forbidden
- invalid_pcap_rejected
- pcap_demo_process
- ml_active_model
- ml_predict
- agent_investigate_rule_based
- invalid_openai_key_test_fails
- response_approve_execute_rollback
- public_ip_guardrail
- reports_csv_json_export
- dashboard_stats
- invalid_dataset_csv_rejected
- frontend_reachable

## Failed
- (none)

## Workflow covered
1. Login
2. PCAP demo upload/process
3. ML predict
4. Agentic investigation
5. Response approve/execute/rollback
6. Reports + dashboard
7. Negative cases (auth, invalid PCAP, invalid key, public IP, bad CSV)
