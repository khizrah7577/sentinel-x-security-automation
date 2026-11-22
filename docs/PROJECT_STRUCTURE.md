# Project structure

```
D:\CyberSecurity_FYP\
  start.bat / stop.bat
  docker-compose.yml
  .env.example / .env.production.example
  README.md
  backend\                 FastAPI app, SQLAlchemy, services
  frontend\                React + Vite + Tailwind SOC UI
  ml\datasets\             Training CSVs
  ml\saved_models\         Joblib artifacts + metrics
  data\database\postgres\  Docker volume (persistent)
  data\pcaps\              Captures
  data\secrets\            Encrypted OpenAI store
  data\backups\            Manual backups
  scripts\                 Health, backup, E2E, prod helpers
  docs\                    Guides + QA reports
  logs\ / reports\
```
