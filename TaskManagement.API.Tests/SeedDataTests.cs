using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using TaskManagement.API.Data;
using TaskStatusEntity = TaskManagement.API.Models.Entities.TaskStatus;
using Xunit;

namespace TaskManagement.API.Tests;

public class SeedDataTests
{
    [Fact]
    public async System.Threading.Tasks.Task InitializeAsync_UsesExistingTaskStatusIds()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();

        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseSqlite(connection)
            .Options;

        await using var context = new ApplicationDbContext(options);
        await context.Database.EnsureCreatedAsync();

        context.TaskStatuses.AddRange(
            new TaskStatusEntity { StatusId = 10, StatusName = "To Do" },
            new TaskStatusEntity { StatusId = 20, StatusName = "In Progress" },
            new TaskStatusEntity { StatusId = 30, StatusName = "Completed" },
            new TaskStatusEntity { StatusId = 40, StatusName = "On Hold" });
        await context.SaveChangesAsync();

        await SeedData.InitializeAsync(context);

        var tasks = await context.Tasks.ToListAsync();
        Assert.Equal(6, tasks.Count);
        Assert.All(tasks, task => Assert.Contains(task.StatusId, new[] { 10, 20, 30 }));
    }
}
