using Microsoft.EntityFrameworkCore;
using TaskManagement.API.Data;
using TaskManagement.API.Models.Entities;
using TaskStatusEntity = TaskManagement.API.Models.Entities.TaskStatus;
using Xunit;

namespace TaskManagement.API.Tests;

public class SeedDataTests
{
    [Fact]
    public async System.Threading.Tasks.Task InitializeAsync_UsesExistingTaskStatusIds()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        await using var context = new ApplicationDbContext(options);

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

    [Fact]
    public async System.Threading.Tasks.Task InitializeAsync_SeedsTasksAfterPartialProjectSeed()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        await using var context = new ApplicationDbContext(options);

        context.TaskStatuses.AddRange(
            new TaskStatusEntity { StatusId = 10, StatusName = "To Do" },
            new TaskStatusEntity { StatusId = 20, StatusName = "In Progress" },
            new TaskStatusEntity { StatusId = 30, StatusName = "Completed" },
            new TaskStatusEntity { StatusId = 40, StatusName = "On Hold" });

        var adminRole = new Role { RoleName = "Admin" };
        var managerRole = new Role { RoleName = "Manager" };
        var employeeRole = new Role { RoleName = "Employee" };
        context.Roles.AddRange(adminRole, managerRole, employeeRole);
        await context.SaveChangesAsync();

        var admin = new User { FullName = "Admin", Email = "admin@test.local", PasswordHash = "hash", RoleId = adminRole.RoleId };
        var manager = new User { FullName = "Manager", Email = "manager@test.local", PasswordHash = "hash", RoleId = managerRole.RoleId };
        var employees = Enumerable.Range(1, 3)
            .Select(index => new User { FullName = $"Employee {index}", Email = $"employee{index}@test.local", PasswordHash = "hash", RoleId = employeeRole.RoleId })
            .ToList();
        context.Users.AddRange(new[] { admin, manager }.Concat(employees));
        await context.SaveChangesAsync();

        var project = new Project { Name = "Existing project", CreatedBy = manager.UserId };
        context.Projects.Add(project);
        await context.SaveChangesAsync();

        context.ProjectMembers.Add(new ProjectMember { ProjectId = project.ProjectId, UserId = manager.UserId });
        context.ProjectMembers.AddRange(employees.Select(employee => new ProjectMember { ProjectId = project.ProjectId, UserId = employee.UserId }));
        await context.SaveChangesAsync();

        await SeedData.InitializeAsync(context);

        Assert.Equal(3, await context.Tasks.CountAsync());
    }
}
