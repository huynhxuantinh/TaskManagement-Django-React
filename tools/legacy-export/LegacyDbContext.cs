using Microsoft.EntityFrameworkCore;

namespace LegacyExport;

public sealed class LegacyDbContext(DbContextOptions<LegacyDbContext> options)
    : DbContext(options)
{
    public DbSet<RoleRow> Roles => Set<RoleRow>();
    public DbSet<UserRow> Users => Set<UserRow>();
    public DbSet<ProjectRow> Projects => Set<ProjectRow>();
    public DbSet<ProjectMemberRow> ProjectMembers => Set<ProjectMemberRow>();
    public DbSet<TaskStatusRow> TaskStatuses => Set<TaskStatusRow>();
    public DbSet<TaskRow> Tasks => Set<TaskRow>();
    public DbSet<NotificationRow> Notifications => Set<NotificationRow>();
    public DbSet<PreferenceRow> UserNotificationPreferences => Set<PreferenceRow>();
    public DbSet<ReportRow> Reports => Set<ReportRow>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        Map<RoleRow>(modelBuilder, "Roles", nameof(RoleRow.RoleId));
        Map<UserRow>(modelBuilder, "Users", nameof(UserRow.UserId));
        Map<ProjectRow>(modelBuilder, "Projects", nameof(ProjectRow.ProjectId));
        Map<ProjectMemberRow>(modelBuilder, "ProjectMembers", nameof(ProjectMemberRow.Id));
        Map<TaskStatusRow>(modelBuilder, "TaskStatuses", nameof(TaskStatusRow.StatusId));
        Map<TaskRow>(modelBuilder, "Tasks", nameof(TaskRow.TaskId));
        Map<NotificationRow>(modelBuilder, "Notifications", nameof(NotificationRow.NotificationId));
        Map<PreferenceRow>(modelBuilder, "UserNotificationPreferences", nameof(PreferenceRow.PreferenceId));
        Map<ReportRow>(modelBuilder, "Reports", nameof(ReportRow.ReportId));
    }

    private static void Map<TEntity>(ModelBuilder modelBuilder, string table, string key)
        where TEntity : class
    {
        modelBuilder.Entity<TEntity>().ToTable(table).HasKey(key);
    }
}

public sealed class RoleRow
{
    public int RoleId { get; set; }
    public string RoleName { get; set; } = "";
}

public sealed class UserRow
{
    public int UserId { get; set; }
    public string FullName { get; set; } = "";
    public string Email { get; set; } = "";
    public string PasswordHash { get; set; } = "";
    public int RoleId { get; set; }
    public bool IsDeleted { get; set; }
    public DateTime CreatedAt { get; set; }
    public string? AvatarUrl { get; set; }
}

public sealed class ProjectRow
{
    public int ProjectId { get; set; }
    public string Name { get; set; } = "";
    public string? Description { get; set; }
    public DateTime? StartDate { get; set; }
    public DateTime? EndDate { get; set; }
    public int CreatedBy { get; set; }
    public bool IsDeleted { get; set; }
    public DateTime CreatedAt { get; set; }
}

public sealed class ProjectMemberRow
{
    public int Id { get; set; }
    public int ProjectId { get; set; }
    public int UserId { get; set; }
    public DateTime JoinedAt { get; set; }
}

public sealed class TaskStatusRow
{
    public int StatusId { get; set; }
    public string StatusName { get; set; } = "";
}

public sealed class TaskRow
{
    public int TaskId { get; set; }
    public string Title { get; set; } = "";
    public string? Description { get; set; }
    public int ProjectId { get; set; }
    public int? AssignedTo { get; set; }
    public int StatusId { get; set; }
    public byte Priority { get; set; }
    public DateTime? Deadline { get; set; }
    public bool IsDeleted { get; set; }
    public DateTime CreatedAt { get; set; }
}

public sealed class NotificationRow
{
    public int NotificationId { get; set; }
    public int UserId { get; set; }
    public string Message { get; set; } = "";
    public int Type { get; set; }
    public bool IsPriority { get; set; }
    public bool IsRead { get; set; }
    public DateTime CreatedAt { get; set; }
}

public sealed class PreferenceRow
{
    public int PreferenceId { get; set; }
    public int UserId { get; set; }
    public int NotificationType { get; set; }
    public bool IsPriority { get; set; }
}

public sealed class ReportRow
{
    public int ReportId { get; set; }
    public int ProjectId { get; set; }
    public int SenderId { get; set; }
    public int ReceiverId { get; set; }
    public string Title { get; set; } = "";
    public string Content { get; set; } = "";
    public bool IsRead { get; set; }
    public DateTime CreatedAt { get; set; }
}
