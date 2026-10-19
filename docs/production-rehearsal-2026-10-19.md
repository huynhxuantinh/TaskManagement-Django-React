# Biên bản production rehearsal — 2026-10-19

## Phạm vi

- Stack cô lập `task-management-s11-drill`, HTTPS `127.0.0.1:8444`; không đổi traffic và không dùng DB dev.
- PostgreSQL 18.6, migration one-shot có advisory lock, 2 Gunicorn replica và Nginx non-root/read-only.
- TLS tự ký chỉ dùng cho rehearsal; secret và backup nằm ngoài repository.

## Image và kiểm soát runtime

| Thành phần | Bằng chứng |
|---|---|
| Backend local image | `sha256:4c4c793077c4255b55567c006e75001f73a5c0fb2d7ba31fca677d0c23afef08`, user `app` |
| Proxy local image | `sha256:e25ce2e32a0aa48deb8cb29b0a5ec4d0df217ee45a3fe987b942a51d59659179`, user `nginx` |
| Python base | `sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576` |
| Node base | `sha256:8510330d3eb72c804231a834b1a8ebb55cb3796c3e4431297a24d246b8add4d5` |
| Nginx base | `sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284` |
| PostgreSQL base | `sha256:885cf05d376c7cf27afef02073e6bdac3841252537f16e244fd1c1e6a7c99fb1` |

Backend và proxy đều chạy `ReadonlyRootfs=true`; DB/backend không publish port. Health, readiness, HSTS, CSP, X-Frame-Options và X-Content-Type-Options đều đạt qua HTTPS.

## Backup/restore và đối soát

- Backup: PostgreSQL custom format, 68,678 byte; SHA-256 kiểm tra `OK` trước restore.
- Restore vào DB mới `task_management_s11_restore_drill`; có 33 migration records.
- Manifest nguồn và DB restore khớp 100%:

| Miền | Số dòng | Canonical SHA-256 |
|---|---:|---|
| roles | 3 | `9a8d711b1e704a9d6e726ed74907485b580fde2433c40c8676c86da2754184c0` |
| users | 3 | `da18aaa0a2ba98b405828ebba869cef9c15f75dd2c97d5d35c45e07c3a435acd` |
| projects | 2 | `3210490f78ea43e1629837d21b9ed1cc26108023cd74d553125f1d0755eaa4bc` |
| project_members | 5 | `fdca952f0b78f8b5177f7a0ea2b96b4b008800e703ef038b1dcee61a01eb2a21` |
| task_statuses | 4 | `92e10de3255515078d81bf3d70922d2d9a93c8d5e74291084e486d446324cc0e` |
| tasks | 6 | `827f46045e73c4099c3bd3e944914e908c89f549c87fcb6057e8595cde41e1d2` |
| notifications | 3 | `b39dbbe228f633788d65e386b28073dd9f902fc55bf8a0ee398e7d5414519ae4` |
| preferences | 15 | `193c29802d699f93773fcd08a7c8a158522d8bd2ec7050e44eb165b976b865a8` |
| reports | 1 | `e7e61304477a8b60d51723208f390536e857cc56a10d22900e2381d3dbd919c4` |

## Kiểm thử

- Migration từ DB rỗng: đạt; chạy lại trên DB đã migrate: đạt, không còn migration chờ.
- HTTPS `/health/`, `/ready/` và React root: HTTP 200.
- Backend: 62 test đạt, coverage 93.76%; Django deploy check, migration check và OpenAPI validation không có lỗi.
- Frontend: lint đạt, 23 test đạt, coverage statement 95.83%, branch 94.20%, function 95.45%, line 98.46%; production build đạt.
- Playwright qua reverse proxy HTTPS trên image cuối: 6/6 đạt cho Admin, Manager, Employee.
- `pip check` không có dependency hỏng; `npm audit` không có vulnerability.
- Backup → checksum → restore DB mới → đối soát manifest: đạt.
- Restart PostgreSQL, 2 backend và proxy: counts/hashes không đổi; avatar vẫn tồn tại trên media volume.

## Kết luận

Production tooling và rehearsal đạt. **Chưa thực hiện final cutover**, chưa write-freeze ASP.NET và chưa đổi traffic. Trước cutover thật vẫn phải lấy final SQL Server export/media manifest gần thời điểm bảo trì và xác nhận RPO 0/RTO 30 phút.
