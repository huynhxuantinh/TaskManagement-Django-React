# Cutover runbook

Mục tiêu đề xuất: **RPO 0**, **RTO 30 phút** cho hệ thống nội bộ. Hai giá trị này phải được người dùng xác nhận trước cutover thật.

Không chạy phần **Final cutover** nếu chưa có xác nhận maintenance window, RPO/RTO và người chịu trách nhiệm GO/NO-GO. Rehearsal không được đổi traffic thật.

## Triển khai production

- Sao chép `infra/.env.prod.example` ra thư mục bí mật ngoài repository, điền secret thật và đường dẫn TLS/backup tuyệt đối.
- Chứng thư TLS phải có `fullchain.pem` và `privkey.pem`; không commit hai file này.
- DB/backend chỉ nằm trên mạng `private`; chỉ proxy công khai cổng HTTPS.
- `migration` là one-shot job dùng PostgreSQL advisory lock. Backend replica không tự migrate.

```bash
docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml config --quiet
docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml pull
docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml up --build -d --wait --scale backend=2
curl --fail https://tasks.example.internal/ready/
docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml ps
```

Backup và restore drill vào DB mới, tuyệt đối không đặt `TARGET_DATABASE` trùng `POSTGRES_DB`:

```bash
docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml --profile ops run --rm backup
ALLOW_RESTORE=YES TARGET_DATABASE=task_management_restore_drill RESTORE_DUMP=/backups/<file>.dump \
  docker compose --env-file /secure/task-management.env -f infra/compose.prod.yaml --profile ops run --rm restore
```

Sau restore, chạy `database_manifest()` trên DB nguồn và DB drill; `counts` và toàn bộ canonical SHA-256 phải giống nhau.

## Điều kiện trước cutover

- Parity checklist đạt 100% cho mục Preserve/Repair.
- Backend tests/coverage, frontend lint/test/build và Playwright ba role đều xanh.
- Import rehearsal dữ liệu thật đã chạy thành công ít nhất hai lần.
- Backup SQL Server đã restore thử; backup PostgreSQL cũng restore thử vào DB mới.
- Counts, canonical row hashes, FK/orphan report và media checksums có baseline.
- Người vận hành có quyền bật maintenance/read-only cho ASP.NET.

## Rehearsal

1. Tạo backup SQL Server chỉ đọc.
2. Export vào `exports/<timestamp>/` với manifest; không commit.
3. Import vào PostgreSQL rehearsal bằng `--dry-run`, sau đó import transaction thật.
4. Reset sequences và chạy validation manifest.
5. Chạy login bằng một BCrypt hash thật và xác minh rehash Argon2.
6. Chạy smoke/API/OpenAPI/Playwright ba role.
7. Ghi thời gian từng bước để xác nhận RTO.

Biên bản gần nhất: `docs/production-rehearsal-2026-10-19.md`.

## Final cutover

1. Thông báo maintenance window.
2. Bật write-freeze trên ASP.NET; từ thời điểm này không được phát sinh write mới.
3. Backup SQL Server và media.
4. Final export + manifest có timestamp/checksum.
5. Import PostgreSQL trong transaction; reset sequences.
6. Đối soát 100% counts, canonical hashes, FK, duplicate/orphan và media checksums.
7. Chạy readiness, auth legacy, smoke và E2E ba role.
8. Go/no-go review.
9. Nếu GO: switch traffic sang Django/React, quan sát lỗi rồi mới mở write.
10. Giữ SQL Server read-only trong thời gian bảo hành; không xóa.

## Go/no-go gate

NO-GO nếu xảy ra một trong các điều kiện:

- count/hash/checksum không khớp mà chưa có exception được duyệt;
- login legacy hoặc refresh/logout thất bại;
- bất kỳ test phân quyền/IDOR critical nào lỗi;
- health/readiness hoặc migration job lỗi;
- E2E Admin/Manager/Employee không hoàn tất;
- thời gian dự kiến vượt maintenance window mà chưa được chấp thuận.

## Rollback

### Trước khi mở write trên hệ thống mới

Trỏ traffic lại ASP.NET rồi tắt write-freeze. Vì hệ thống cũ bị đóng write trong toàn bộ thời gian nên RPO bằng 0.

### Sau khi đã mở write trên hệ thống mới

PostgreSQL là source of truth. Không được trỏ thẳng về SQL Server vì sẽ mất write mới. Phải:

1. bật maintenance trên Django/React;
2. export reverse delta PostgreSQL → SQL Server;
3. import và đối soát;
4. chỉ switch sau khi counts/hashes/FK khớp.

Nếu reverse sync chưa được diễn tập, ưu tiên sửa hoặc restore PostgreSQL thay vì rollback mù.

## Evidence cần lưu

- Commit/image digest được deploy.
- Backup identifiers và restore evidence.
- Export/import manifest.
- Test/coverage/build/E2E reports.
- Thời điểm write-freeze, switch traffic, mở write và kết thúc theo dõi.
- Người đưa ra quyết định GO/NO-GO.

## Dọn rehearsal

Chỉ xóa volume của đúng project rehearsal sau khi đã lưu evidence và xác minh backup. Không chạy `down -v` trên production:

```bash
docker compose -p task-management-s11-drill -f infra/compose.prod.yaml down -v
```
