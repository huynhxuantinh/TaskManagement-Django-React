# Legacy SQL Server export

The exporter opens SQL Server through EF Core with no tracking, emits an AES-256-GCM encrypted `legacy-export.tmx`, encrypts referenced avatar files, and writes a non-sensitive `manifest.json` containing counts, canonical hashes, duplicate/orphan diagnostics, and media checksums.

From the repository root on the Windows host:

```powershell
$env:LEGACY_SQLSERVER_CONNECTION = 'Server=.\SQLEXPRESS;Database=TaskManagementFinalDB;Trusted_Connection=True;Encrypt=False;ApplicationIntent=ReadOnly'
$env:LEGACY_EXPORT_KEY = '<base64-encoded 32-byte key>'
dotnet run --project tools\legacy-export -- --output exports\rehearsal-YYYYMMDD-HHMMSS
```

Never commit the connection string, encryption key, export bundle, decrypted media, or password hashes. `exports/` is ignored by Git.
