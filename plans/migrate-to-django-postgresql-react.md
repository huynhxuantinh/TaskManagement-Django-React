# Blueprint: chuyển Task Management sang Django, PostgreSQL và React

## Mục tiêu và quyết định kiến trúc

Viết lại hệ thống thành ba phần độc lập, giữ bản ASP.NET/SQL Server làm đối chiếu đến khi nghiệm thu:

- `backend/`: Python 3.14, Django 5.2 LTS, Django REST Framework 3.18.x.
- `frontend/`: Node.js 24 LTS, React 19.3, TypeScript, Vite và Tailwind CSS.
- `infra/`: PostgreSQL 18.x, Docker Compose cho môi trường dev/test/prod-like.

Dependency phải được khóa bằng `requirements.txt` và `package-lock.json`; patch version được chọn tại lúc scaffold và phải qua audit/test trước khi commit.

Các miền nghiệp vụ được giữ: User/Role, Project, ProjectMember, TaskStatus, Task, Notification, UserNotificationPreference, Report và avatar.

## Trạng thái thực thi

- S0 hoàn thành ngày 2026-10-18: commits `2608bad`, `4687043`.
- S1 hoàn thành ngày 2026-10-18: contract, parity, schema map, baseline dữ liệu và cutover runbook đã được xác minh.
- S2 hoàn thành ngày 2026-10-18: Django/DRF, React/Vite/Tailwind, PostgreSQL 18, Docker Compose và CI nền đã chạy xanh.
- S3 hoàn thành ngày 2026-10-18: schema đầy đủ, export mã hóa chỉ đọc và rehearsal dữ liệu thật hai lần đã đối soát bằng count/hash/media checksum.
- S4 hoàn thành ngày 2026-10-19: JWT access, refresh cookie rotation/blacklist, CSRF, Argon2, adapter BCrypt.Net, RBAC primitives và OpenAPI đã chạy xanh cho ba role.

### Quyết định bảo mật bắt buộc

- Backend lấy danh tính/role từ JWT, không tin `userId` hoặc `role` do client gửi.
- Access token chỉ giữ trong memory của React; refresh token dùng cookie `HttpOnly`, `Secure` ở production, `SameSite=Lax`, rotation và blacklist/reuse detection.
- Refresh/logout dùng CSRF token; CORS dev chỉ cho đúng origin React và bật credentials. Production phục vụ cùng site qua reverse proxy.
- Mật khẩu mới dùng Argon2. Hash BCrypt.Net cũ phải được adapter/importer chuyển sang định dạng Django BCrypt có thể nhận diện, rồi tự rehash sang Argon2 sau lần đăng nhập thành công.
- Soft delete cho Project/Task; queryset phải scope theo quyền trước khi retrieve để chống IDOR.

### Ma trận quyền đích

| Tài nguyên/hành động | Admin | Manager | Employee |
|---|---|---|---|
| User list/detail, đổi role, deactivate | Toàn bộ | Không | Chỉ profile của mình |
| Avatar/preferences/password | Của mình hoặc hỗ trợ theo policy | Của mình | Của mình |
| Project list/detail | Toàn bộ | Dự án quản lý/tham gia | Dự án tham gia |
| Tạo project | Có | Có | Không |
| Sửa/xóa project | Toàn bộ | Project do mình quản lý | Không |
| Member list/add/remove/invite | Toàn bộ | Project do mình quản lý | Chỉ xem trong project tham gia |
| Task list/detail | Toàn bộ | Project quản lý/tham gia | Task được giao hoặc thuộc project tham gia theo quyết định S1 |
| Tạo/giao/sửa/xóa task | Toàn bộ | Project do mình quản lý | Không |
| Đổi trạng thái task | Toàn bộ | Project quản lý | Task được giao |
| Notification read/mark-read | Toàn bộ theo audit | Của mình | Của mình |
| Report/dashboard | Toàn hệ thống | Project quản lý | Cá nhân |

Mọi endpoint phải test: anonymous, self, người cùng role khác project, người khác role, object soft-deleted và object không tồn tại.

## Chế độ thực thi và dependency graph

Repo đang ở `main`, có remote nhưng không có GitHub CLI, nên dùng **Direct mode**: một commit nhỏ cho mỗi bước, stage đúng path, không tự push. Không gom `bin/`, `obj/`, `node_modules/`, `.env`, media hoặc dump vào commit.

```text
S0 Repo hygiene
 -> S1 Contract + dữ liệu + quyết định nghiệp vụ
   -> S2 Scaffold + dev compose + CI nền
     -> S3 Schema + rehearsal import
       -> S4 Auth/JWT/RBAC
         -> S5 Projects/Members API
         -> S8 React shell/Auth       (có thể song song S5)
S5 -> S6 Tasks/Notifications API
S5 + S6 -> S7 Users/Media/Reports API
S5 + S6 + S8 -> S9 React core UI
S7 + S9 -> S10 React support UI + full E2E
S10 -> S11 production compose + final migration + cutover
```

## S0 — Preflight và vệ sinh repository

**Context:** repo hiện đang track nhiều artifact `node_modules`, `bin/obj`, `.vs`; worktree có artifact build và một avatar phát sinh. Không được xóa mù vì có thể chứa dữ liệu người dùng.

**Output:** `.gitignore`, `docs/repo-hygiene.md`, danh sách artifact tracked cần người dùng xác nhận trước khi bỏ track.

**Công việc:**

- Ghi lại branch, remote, commit đầu vào, trạng thái dịch vụ hiện chạy.
- Thêm ignore cho Python, Node, .NET build, IDE, `.env`, media dev, coverage và export chứa PII.
- Chỉ bỏ track artifact bằng commit riêng sau khi xác nhận; không xóa avatar/dữ liệu chưa rõ nguồn.
- Quy định lệnh chạy từ repo root và chiến lược stage theo path.

**Verify:** `git status --short`, kiểm tra secrets bằng scanner repo-local nếu có; `.env`/dump/media mới không xuất hiện trong `git status`.

**Exit:** không còn nguy cơ commit nhầm secrets/artifact; dữ liệu hiện có không bị xóa.

**Rollback:** revert riêng commit hygiene; không chạy clean/reset. **Model tier:** mặc định.

## S1 — Chốt contract, parity và quy tắc dữ liệu

**Context:** ASP.NET hiện có Auth, Users, Projects, ProjectMembers, Tasks, Notifications và Reports. Một số UI là mock/no-op; API hiện truyền role/userId từ client và Employee đang thấy task theo project membership.

**Output:** `docs/api-contract.md`, `docs/parity-checklist.md`, `docs/schema-map.md`, `docs/cutover-runbook.md` bản nháp.

**Công việc:**

- Lập bảng từng hành vi: `preserve`, `repair`, hoặc `drop có chủ đích`; đặc biệt CheckIn, ChangePassword, DeactivateAccount, Invite và Employee task visibility.
- Chốt endpoint `/api/v1/...`, envelope `success/message/data/errors`, pagination, filter, search, mã lỗi và OpenAPI.
- Thêm endpoint metadata cho task statuses và dashboard aggregate.
- Lập endpoint × actor × resource-scope matrix, bao gồm profile, avatar, preferences, notification, report message/read và member list.
- Chốt schema từng cột, constraint, delete rule, creator phải là member, email unique không phân biệt hoa thường, preference unique/user và status dùng code ổn định thay vì ID cứng.
- Xác nhận timestamp SQL Server hiện tại được hiểu là `Asia/Saigon`; importer chuyển timestamp sang UTC, còn ngày deadline thuần ngày dùng `DateField` nếu nghiệp vụ cho phép.
- Lấy baseline count, orphan/duplicate report và mẫu dữ liệu cho từng bảng.

**Verify:** đối chiếu 100% controller/DTO/model/view hiện tại; review ma trận quyền và parity checklist.

**Exit:** không còn quyết định nghiệp vụ mơ hồ; mọi chức năng có acceptance criteria.

**Rollback:** xóa/revert tài liệu mới. **Model tier:** mạnh nhất.

## S2 — Scaffold stack mới, dev Compose và CI nền

**Context:** stack mới sống cạnh ứng dụng cũ, chưa thay traffic.

**Output:** `backend/`, `frontend/`, `infra/compose.dev.yaml`, `.env.example`, workflow CI.

**Công việc:**

- Django settings tách base/dev/test/prod; DRF, health `/health/`, readiness `/ready/`, structured logging.
- React/Vite/TypeScript/Tailwind, ESLint, Vitest, React Router.
- PostgreSQL healthcheck và volume; backend dev service chạy migration bằng job riêng, không tự migrate trên mọi replica.
- Pin dependencies/lockfiles; thêm CORS/CSRF dev tối thiểu.
- CI có PostgreSQL service và jobs backend test, frontend lint/test/build; chưa cần E2E.

**Verify từ repo root:**

```bash
docker compose -f infra/compose.dev.yaml up -d db
docker compose -f infra/compose.dev.yaml run --rm backend python manage.py check
curl --fail http://localhost:8010/health/
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

**Exit:** DB healthy, health HTTP 200, fresh backend/frontend checks xanh trên máy và CI.

**Rollback:** dừng compose, giữ volume để điều tra, revert đúng commit scaffold. **Model tier:** mạnh nhất.

## S3 — Django schema và migration rehearsal sớm

**Context:** cần chứng minh dữ liệu SQL Server có thể sang PostgreSQL trước khi xây API/UI sâu.

**Output:** Django models/migrations, `tools/legacy-export/`, command `import_legacy`, manifest đối soát.

**Công việc:**

- Tạo custom User ngay migration đầu; quyết định Role là bảng tham chiếu có code `ADMIN/MANAGER/EMPLOYEE`.
- Tạo models/constraints/indexes cho toàn bộ domain; TaskStatus có code ổn định.
- Export chạy trên Windows host bằng .NET/SQL Server tooling, chỉ đọc; dump vào thư mục ignored và mã hóa khi lưu/chuyển.
- Import có `--dry-run`, transaction, giữ mapping PK/FK, reset PostgreSQL sequences và báo conflict email/preference/orphan.
- Chuyển `Asia/Saigon` → UTC có test boundary; copy media kèm SHA-256.
- Manifest gồm count, canonical row hashes theo bảng, orphan/duplicate report và media checksums.

**Verify:** migration từ DB rỗng; `makemigrations --check`; export/import rehearsal hai lần; lần hai không nhân bản; count + hashes + FK + media checksum khớp.

**Exit:** rehearsal nhập dữ liệu thật thành công và có báo cáo sai khác bằng 0 hoặc exception được duyệt.

**Rollback:** drop riêng PostgreSQL rehearsal DB/volume đã xác định, tuyệt đối không sửa SQL Server. **Model tier:** mạnh nhất.

## S4 — Auth, password migration và primitive RBAC

**Context:** auth mới thay session MVC; phải chứng minh tài khoản BCrypt.Net cũ đăng nhập được.

**Output:** `/api/v1/auth/*`, permission primitives, auth tests, OpenAPI auth schema.

**Công việc:**

- Login, refresh, logout/revoke, me, register theo policy, change password và deactivate.
- Access token memory; refresh cookie HttpOnly/Secure/SameSite; CSRF cho cookie mutation; rotation và reuse detection.
- Argon2 là hasher mặc định. Importer/adapter dùng Django BCrypt hasher để nhận hash `$2a$...` thực tế, rồi `check_password` tự nâng cấp sang Argon2.
- Viết role/ownership permission primitives và scoped queryset helpers.
- Rate-limit login/refresh; không log token/password/hash.

**Verify:** test một hash BCrypt.Net export thật đăng nhập thành công, hash trong DB đổi sang Argon2 sau login; test refresh rotation/reuse, CSRF, logout, anonymous và ba role. `pytest --cov --cov-fail-under=80` cho auth.

**Exit:** auth hoàn chỉnh, không truyền role/userId để cấp quyền, OpenAPI validate thành công.

**Rollback:** revoke token/cookie mới và revert auth commit; dữ liệu schema vẫn giữ. **Model tier:** mạnh nhất.

## S5 — Projects và ProjectMembers API

**Context:** đây là gốc ownership cho task/report, phải ổn định trước các miền phụ thuộc.

**Output:** serializers/services/viewsets/tests cho project/member.

**Công việc:** CRUD, filter/search/pagination, soft delete, creator-member invariant, add/remove/invite member an toàn; bỏ mật khẩu invite cố định.

**Verify:** tests 400/401/403/404/conflict và full actor-resource matrix; query count; OpenAPI schema; luồng tạo project → add/remove member.

**Exit:** parity mục Project/Team đạt; không IDOR và không lộ project ngoài scope.

**Rollback:** revert S5; schema/auth vẫn chạy. **Model tier:** mạnh nhất.

## S6 — Tasks và Notifications API

**Context:** notification phát sinh trực tiếp từ giao việc, status và deadline nên làm cùng task thay vì tách song song.

**Output:** Task/Notification endpoints, domain services và tests.

**Công việc:** Task CRUD, assignee membership validation, filter/search/pagination, priority/deadline/status code, soft delete; notification khi assign/status/deadline; list/mark-read chỉ đúng chủ sở hữu.

**Verify:** luồng project → member → assign task → employee status update → notification; actor-resource matrix; transaction rollback nếu notification/task thất bại; coverage app ≥80%.

**Exit:** task và notification đạt parity, không hard-code StatusId.

**Rollback:** revert S6; project/member API không đổi. **Model tier:** mạnh nhất.

## S7 — Users, media, dashboard và reports API

**Context:** reports phụ thuộc dữ liệu Project/Task nên chỉ làm sau S6.

**Output:** user/profile/preferences/media/report/dashboard endpoints và tests.

**Công việc:** self profile, Admin role management, avatar upload, notification preferences; workload, project summary, top contributors, messages; queryset theo scope; tối ưu aggregation/select-related/prefetch.

**Bảo mật media:** allowlist MIME thực, giới hạn kích thước, tên file do server sinh, chống path traversal, không phục vụ file executable.

**Verify:** permissions matrix, malicious upload, report values đối chiếu fixture, query-count tests, OpenAPI validation.

**Exit:** toàn bộ API backend đạt parity checklist; full backend test/coverage xanh.

**Rollback:** revert S7; core API còn nguyên. **Model tier:** mạnh nhất.

## S8 — React shell và xác thực

**Context:** có thể làm song song S5 sau khi auth contract S4 ổn định.

**Output:** app shell, router, API client, auth store, login/register/profile tối thiểu, design system trung tính.

**Công việc:** access token memory, refresh cookie với credentials/CSRF, restore session, logout, error mapping, protected/role routes; component chung table/form/modal/toast/loading/error/empty.

**Verify:** Vitest cho auth state/refresh/reuse/logout/route guards; build; test thủ công ba tài khoản seed. Backend vẫn là nơi quyết định quyền cuối.

**Exit:** auth UI ổn định, không còn nhận diện Starbucks, reload không làm hỏng phiên.

**Rollback:** revert frontend S8; backend dùng qua Swagger. **Model tier:** mặc định.

## S9 — React core UI: Dashboard, Projects, Team, Tasks

**Context:** phụ thuộc S5/S6 và app shell S8.

**Output:** màn hình core và component tests.

**Công việc:** dashboard theo role; project list/detail/create/edit; member management; task list/create/edit/filter/search/status; responsive và accessibility cơ bản.

**Verify:** lint, component tests, build; Playwright cho Admin quản lý project, Manager giao task, Employee xem/cập nhật task; kiểm tra UI ẩn action và API vẫn trả 403 khi gọi trực tiếp.

**Exit:** core parity đạt cho ba role.

**Rollback:** revert từng feature slice; auth shell giữ nguyên. **Model tier:** mặc định.

## S10 — React support UI, full-stack E2E và CI hoàn chỉnh

**Context:** Users/Notifications/Reports API S7 đã ổn định.

**Output:** Notifications, Reports, Settings/Profile/Avatar UI; `infra/compose.e2e.yaml`; Playwright suite; CI E2E.

**Công việc:** hoàn thiện màn hình phụ trợ; compose E2E dựng db/backend/frontend; seed cố định; test accessibility/smoke; validate OpenAPI client compatibility.

**Verify từ root:**

```bash
docker compose -f infra/compose.e2e.yaml up --build -d
curl --fail http://localhost:8000/ready/
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend exec playwright test
```

**Exit:** parity checklist 100%; E2E ba role xanh trên fresh DB và upgraded DB; CI xanh.

**Rollback:** dừng compose E2E và revert support UI/test commit; không đụng dữ liệu nguồn. **Model tier:** mạnh nhất cho E2E, mặc định cho UI.

## S11 — Production hardening, final migration và cutover

**Context:** đây là bước duy nhất đổi traffic. Mục tiêu đề xuất cho hệ thống nội bộ: RPO 0, RTO 30 phút; người dùng xác nhận lại trước khi thực hiện.

**Output:** production-like compose, Dockerfiles non-root, reverse proxy, backup/restore scripts, runbook đã diễn tập và biên bản đối soát.

**Công việc trước cutover:**

- Pin image digest/version, readiness/liveness, resource limits, HTTPS, static/media volume, secrets ngoài repo.
- Migration là one-shot job có lock; app replicas không tự migrate.
- Backup PostgreSQL và thực hiện restore drill vào DB mới; rehearsal full import ít nhất một lần gần ngày cutover.

**Runbook cutover:**

1. Thông báo maintenance và bật read-only/write-freeze trên hệ thống ASP.NET.
2. Backup SQL Server; final export + media manifest.
3. Import PostgreSQL trong transaction; reset sequences.
4. Đối soát 100% counts, canonical hashes, FK, duplicate/orphan report và media checksums.
5. Chạy smoke, OpenAPI, auth BCrypt→Argon2 và Playwright ba role.
6. Go/no-go: nếu bất kỳ gate nào lỗi, quay về ASP.NET khi write-freeze vẫn còn, nên không mất write.
7. Nếu đạt, switch traffic sang React/Django rồi mới mở write.

**Quy tắc rollback sau khi mở write:** PostgreSQL trở thành source of truth. Không được trỏ ngược về SQL Server nếu chưa maintenance + reverse-delta export/import + đối soát; nếu không đủ thời gian thì sửa/restore PostgreSQL thay vì rollback mù.

**Verify:** `docker compose ps` kèm health HTTP thực, restore drill, migration từ empty và upgraded DB, full tests/coverage/build/E2E, restart không mất DB/media.

**Exit:** hệ thống mới healthy, dữ liệu khớp, ba role nghiệm thu, backup/restore chứng minh được; ASP.NET chỉ đánh dấu legacy sau thời gian ổn định đã thống nhất.

**Rollback:** theo runbook RPO 0 ở trên; không xóa SQL Server trong giai đoạn bảo hành. **Model tier:** mạnh nhất.

## Commit map đề xuất

1. `chore: establish repository hygiene for migration`
2. `docs: define parity API security and data contracts`
3. `chore: scaffold Django React PostgreSQL and CI`
4. `feat: add PostgreSQL schema and legacy import rehearsal`
5. `feat: add JWT auth password migration and RBAC`
6. `feat: add project and membership APIs`
7. `feat: add task and notification APIs`
8. `feat: add user media dashboard and report APIs`
9. `feat: add React shell and authentication`
10. `feat: add React project team and task workflows`
11. `feat: add support screens and full-stack E2E`
12. `ops: add production deployment migration and cutover runbook`

## Protocol thay đổi kế hoạch

- Muốn thêm/bỏ chức năng: cập nhật `parity-checklist` và ma trận quyền trước khi sửa code.
- Bước vượt một commit review được: tách theo model/API/UI, cập nhật dependency graph và exit criteria.
- Chỉ chạy song song khi không sửa chung file và contract đầu vào đã khóa.
- Không bỏ qua auth tests, import rehearsal, write-freeze, checksum hay go/no-go.
- Mọi deviation ghi vào changelog cuối file với lý do, tác động và người chấp thuận.

## Changelog

- 2026-10-18: tạo blueprint; sau adversarial review đã bổ sung password compatibility, IDOR matrix, schema decisions, early rehearsal, repo hygiene, CI, write-freeze và rollback không mất dữ liệu.
