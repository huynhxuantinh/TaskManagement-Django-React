using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;

namespace LegacyExport;

using Row = SortedDictionary<string, object?>;
using Payload = Dictionary<string, List<SortedDictionary<string, object?>>>;

public sealed class ExportService(LegacyDbContext db)
{
    public async Task<Payload> ReadPayloadAsync()
    {
        db.ChangeTracker.QueryTrackingBehavior = QueryTrackingBehavior.NoTracking;
        var roles = await db.Roles.OrderBy(row => row.RoleId).ToListAsync();
        var users = await db.Users.OrderBy(row => row.UserId).ToListAsync();
        var projects = await db.Projects.OrderBy(row => row.ProjectId).ToListAsync();
        var projectMembers = await db.ProjectMembers.OrderBy(row => row.Id).ToListAsync();
        var taskStatuses = await db.TaskStatuses.OrderBy(row => row.StatusId).ToListAsync();
        var tasks = await db.Tasks.OrderBy(row => row.TaskId).ToListAsync();
        var notifications = await db.Notifications.OrderBy(row => row.NotificationId).ToListAsync();
        var preferences = await db.UserNotificationPreferences.OrderBy(row => row.PreferenceId).ToListAsync();
        var reports = await db.Reports.OrderBy(row => row.ReportId).ToListAsync();
        return new Payload
        {
            ["roles"] = roles.Select(row => new Row
            {
                ["legacy_id"] = row.RoleId,
                ["name"] = row.RoleName,
            }).ToList(),
            ["users"] = users.Select(row => new Row
            {
                ["id"] = row.UserId,
                ["full_name"] = row.FullName,
                ["email"] = row.Email,
                ["password"] = row.PasswordHash,
                ["role_legacy_id"] = row.RoleId,
                ["is_active"] = !row.IsDeleted,
                ["created_at"] = Canonical.LegacyDateTimeInput(row.CreatedAt),
                ["avatar"] = NormalizeAvatar(row.AvatarUrl),
            }).ToList(),
            ["projects"] = projects.Select(row => new Row
            {
                ["id"] = row.ProjectId,
                ["name"] = row.Name,
                ["description"] = row.Description,
                ["start_date"] = row.StartDate.HasValue ? row.StartDate.Value.ToString("yyyy-MM-dd") : null,
                ["end_date"] = row.EndDate.HasValue ? row.EndDate.Value.ToString("yyyy-MM-dd") : null,
                ["creator_id"] = row.CreatedBy,
                ["is_deleted"] = row.IsDeleted,
                ["created_at"] = Canonical.LegacyDateTimeInput(row.CreatedAt),
            }).ToList(),
            ["project_members"] = projectMembers.Select(row => new Row
            {
                ["id"] = row.Id,
                ["project_id"] = row.ProjectId,
                ["user_id"] = row.UserId,
                ["joined_at"] = Canonical.LegacyDateTimeInput(row.JoinedAt),
            }).ToList(),
            ["task_statuses"] = taskStatuses.Select(row => new Row
            {
                ["legacy_id"] = row.StatusId,
                ["name"] = row.StatusName,
            }).ToList(),
            ["tasks"] = tasks.Select(row => new Row
            {
                ["id"] = row.TaskId,
                ["title"] = row.Title,
                ["description"] = row.Description,
                ["project_id"] = row.ProjectId,
                ["assignee_id"] = row.AssignedTo,
                ["status_legacy_id"] = row.StatusId,
                ["priority"] = row.Priority,
                ["deadline"] = row.Deadline.HasValue ? row.Deadline.Value.ToString("yyyy-MM-dd") : null,
                ["is_deleted"] = row.IsDeleted,
                ["created_at"] = Canonical.LegacyDateTimeInput(row.CreatedAt),
            }).ToList(),
            ["notifications"] = notifications.Select(row => new Row
            {
                ["id"] = row.NotificationId,
                ["user_id"] = row.UserId,
                ["message"] = row.Message,
                ["type"] = Canonical.NotificationTypeCode((int)row.Type),
                ["is_priority"] = row.IsPriority,
                ["is_read"] = row.IsRead,
                ["created_at"] = Canonical.LegacyDateTimeInput(row.CreatedAt),
            }).ToList(),
            ["preferences"] = preferences.Select(row => new Row
            {
                ["id"] = row.PreferenceId,
                ["user_id"] = row.UserId,
                ["type"] = Canonical.NotificationTypeCode((int)row.NotificationType),
                ["is_priority"] = row.IsPriority,
            }).ToList(),
            ["reports"] = reports.Select(row => new Row
            {
                ["id"] = row.ReportId,
                ["project_id"] = row.ProjectId,
                ["sender_id"] = row.SenderId,
                ["receiver_id"] = row.ReceiverId,
                ["title"] = row.Title,
                ["content"] = row.Content,
                ["is_read"] = row.IsRead,
                ["created_at"] = Canonical.LegacyDateTimeInput(row.CreatedAt),
            }).ToList(),
        };
    }

    public static Payload TargetRows(Payload payload)
    {
        var target = payload.ToDictionary(
            pair => pair.Key,
            pair => pair.Value.Select(Clone).ToList());
        foreach (var row in target["roles"])
            row["code"] = Canonical.RoleCode((string)row["name"]!);
        foreach (var row in target["users"])
        {
            row["email"] = ((string)row["email"]!).Trim().ToLowerInvariant();
            row["avatar"] ??= "";
            row["created_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["created_at"]));
        }
        foreach (var row in target["projects"])
        {
            row["description"] ??= "";
            row["created_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["created_at"]));
        }
        foreach (var row in target["project_members"])
            row["joined_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["joined_at"]));
        foreach (var row in target["task_statuses"])
            row["code"] = Canonical.StatusCode((string)row["name"]!);
        foreach (var row in target["tasks"])
        {
            row["description"] ??= "";
            row["created_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["created_at"]));
        }
        foreach (var row in target["notifications"])
            row["created_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["created_at"]));
        foreach (var row in target["reports"])
            row["created_at"] = Canonical.LegacyDateTimeText(ParseDateTime(row["created_at"]));
        return target;
    }

    public static Dictionary<string, object> Diagnostics(Payload payload)
    {
        var duplicateEmails = payload["users"]
            .GroupBy(row => ((string)row["email"]!).Trim(), StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1)
            .Select(group => group.Key)
            .Order()
            .ToArray();
        var duplicatePreferences = payload["preferences"]
            .GroupBy(row => $"{row["user_id"]}:{row["type"]}")
            .Where(group => group.Count() > 1)
            .Select(group => group.Key)
            .Order()
            .ToArray();
        var orphans = FindOrphans(payload).ToArray();
        return new Dictionary<string, object>
        {
            ["duplicate_emails"] = duplicateEmails,
            ["duplicate_preferences"] = duplicatePreferences,
            ["orphans"] = orphans,
        };
    }

    private static IEnumerable<string> FindOrphans(Payload payload)
    {
        var roleIds = Ids(payload["roles"], "legacy_id");
        var userIds = Ids(payload["users"], "id");
        var projectIds = Ids(payload["projects"], "id");
        var statusIds = Ids(payload["task_statuses"], "legacy_id");
        foreach (var row in payload["users"])
            if (!roleIds.Contains(Convert.ToInt64(row["role_legacy_id"]))) yield return $"users:{row["id"]}:role";
        foreach (var row in payload["projects"])
            if (!userIds.Contains(Convert.ToInt64(row["creator_id"]))) yield return $"projects:{row["id"]}:creator";
        foreach (var row in payload["project_members"])
            if (!projectIds.Contains(Convert.ToInt64(row["project_id"])) || !userIds.Contains(Convert.ToInt64(row["user_id"]))) yield return $"project_members:{row["id"]}";
        foreach (var row in payload["tasks"])
        {
            if (!projectIds.Contains(Convert.ToInt64(row["project_id"]))) yield return $"tasks:{row["id"]}:project";
            if (row["assignee_id"] is not null && !userIds.Contains(Convert.ToInt64(row["assignee_id"]))) yield return $"tasks:{row["id"]}:assignee";
            if (!statusIds.Contains(Convert.ToInt64(row["status_legacy_id"]))) yield return $"tasks:{row["id"]}:status";
        }
        foreach (var table in new[] { "notifications", "preferences" })
            foreach (var row in payload[table])
                if (!userIds.Contains(Convert.ToInt64(row["user_id"]))) yield return $"{table}:{row["id"]}:user";
        foreach (var row in payload["reports"])
            if (!projectIds.Contains(Convert.ToInt64(row["project_id"])) || !userIds.Contains(Convert.ToInt64(row["sender_id"])) || !userIds.Contains(Convert.ToInt64(row["receiver_id"]))) yield return $"reports:{row["id"]}";
    }

    private static HashSet<long> Ids(IEnumerable<Row> rows, string field) =>
        rows.Select(row => Convert.ToInt64(row[field])).ToHashSet();

    private static Row Clone(Row source) => new(source, StringComparer.Ordinal);
    private static DateTime ParseDateTime(object? value) =>
        DateTime.Parse((string)value!, System.Globalization.CultureInfo.InvariantCulture);
    private static string? NormalizeAvatar(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Replace('\\', '/').TrimStart('/');
}
