using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace LegacyExport;

public static class Canonical
{
    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        WriteIndented = false,
    };

    public static string TableHash(
        IEnumerable<SortedDictionary<string, object?>> rows)
    {
        var canonical = rows
            .Select(row => JsonSerializer.Serialize(row, JsonOptions))
            .Order(StringComparer.Ordinal);
        var content = string.Concat(canonical.Select(row => row + "\n"));
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(content)));
    }

    public static string LegacyDateTimeText(DateTime value)
    {
        var unspecified = DateTime.SpecifyKind(value, DateTimeKind.Unspecified);
        var zone = FindLegacyTimeZone();
        var utc = TimeZoneInfo.ConvertTimeToUtc(unspecified, zone);
        return utc.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'");
    }

    public static string LegacyDateTimeInput(DateTime value) =>
        DateTime.SpecifyKind(value, DateTimeKind.Unspecified)
            .ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff");

    public static string RoleCode(string name) => name.Trim().ToLowerInvariant() switch
    {
        "admin" => "ADMIN",
        "manager" => "MANAGER",
        "employee" => "EMPLOYEE",
        _ => throw new InvalidDataException($"Unmapped role: {name}"),
    };

    public static string StatusCode(string name) => name.Trim().ToLowerInvariant() switch
    {
        "to do" => "TODO",
        "in progress" => "IN_PROGRESS",
        "completed" => "COMPLETED",
        "on hold" => "ON_HOLD",
        _ => throw new InvalidDataException($"Unmapped task status: {name}"),
    };

    public static string NotificationTypeCode(int value) => value switch
    {
        0 => "GENERAL",
        1 => "TASK_ASSIGNED",
        2 => "STATUS_CHANGED",
        3 => "PROJECT_ADDED",
        4 => "DEADLINE_APPROACHING",
        _ => throw new InvalidDataException($"Unmapped notification type: {value}"),
    };

    private static TimeZoneInfo FindLegacyTimeZone()
    {
        foreach (var id in new[] { "Asia/Saigon", "Asia/Ho_Chi_Minh", "SE Asia Standard Time" })
        {
            try
            {
                return TimeZoneInfo.FindSystemTimeZoneById(id);
            }
            catch (TimeZoneNotFoundException)
            {
            }
        }
        throw new TimeZoneNotFoundException("Asia/Saigon timezone is unavailable");
    }
}
