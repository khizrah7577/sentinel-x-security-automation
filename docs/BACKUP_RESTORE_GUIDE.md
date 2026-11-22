# Backup and Restore

## Local Windows

```bat
backup.bat
restore.bat D:\CyberSecurity_FYP\data\backups\TIMESTAMP
```

`restore.bat` asks you to type **YES** before overwriting the database.

Includes:

- PostgreSQL SQL dump
- ML models
- Reports
- Encrypted secrets store

Does **not** auto-copy large PCAPs (copy `data\pcaps` yourself if needed).

## Cloud

```bash
./backup-cloud.sh
./restore-cloud.sh /path/to/backup_dir
```

Same YES confirmation for restore.

## Safety rules

- Never run restore against production without confirmation
- Keep backups on D: / separate disk
- Test restore on a disposable DB when possible
