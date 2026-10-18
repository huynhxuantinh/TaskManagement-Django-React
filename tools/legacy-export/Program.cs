using System.Security.Cryptography;
using System.Text.Json;
using LegacyExport;
using Microsoft.EntityFrameworkCore;

var arguments = Arguments.Parse(args);
var keyText = Environment.GetEnvironmentVariable(arguments.KeyEnvironment)
    ?? throw new InvalidOperationException($"Missing encryption key env: {arguments.KeyEnvironment}");
var key = Convert.FromBase64String(keyText);
if (key.Length != 32) throw new InvalidOperationException("Encryption key must decode to 32 bytes");

if (Directory.Exists(arguments.Output) && Directory.EnumerateFileSystemEntries(arguments.Output).Any())
    throw new InvalidOperationException("Output directory must be new or empty");
Directory.CreateDirectory(arguments.Output);

var options = new DbContextOptionsBuilder<LegacyDbContext>()
    .UseSqlServer(arguments.Connection)
    .Options;
await using var database = new LegacyDbContext(options);
var service = new ExportService(database);
var payload = await service.ReadPayloadAsync();
var diagnostics = ExportService.Diagnostics(payload);
if (((string[])diagnostics["duplicate_emails"]).Length > 0 ||
    ((string[])diagnostics["duplicate_preferences"]).Length > 0 ||
    ((string[])diagnostics["orphans"]).Length > 0)
    throw new InvalidDataException("Legacy data contains duplicate or orphan records; export aborted");

var targetRows = ExportService.TargetRows(payload);
var media = ExportMedia(payload, arguments.MediaRoot, arguments.Output, key);
var manifest = new Dictionary<string, object?>
{
    ["format_version"] = 1,
    ["generated_at"] = DateTime.UtcNow.ToString("O"),
    ["legacy_timezone"] = "Asia/Saigon",
    ["counts"] = targetRows.ToDictionary(pair => pair.Key, pair => pair.Value.Count),
    ["hashes"] = targetRows.ToDictionary(pair => pair.Key, pair => Canonical.TableHash(pair.Value)),
    ["diagnostics"] = diagnostics,
    ["media"] = media,
};

var payloadBytes = JsonSerializer.SerializeToUtf8Bytes(payload, Canonical.JsonOptions);
await File.WriteAllBytesAsync(
    Path.Combine(arguments.Output, "legacy-export.tmx"),
    ExportCrypto.Encrypt(payloadBytes, key));
await File.WriteAllTextAsync(
    Path.Combine(arguments.Output, "manifest.json"),
    JsonSerializer.Serialize(manifest, new JsonSerializerOptions(Canonical.JsonOptions) { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(manifest, Canonical.JsonOptions));

static List<Dictionary<string, string>> ExportMedia(
    Dictionary<string, List<SortedDictionary<string, object?>>> payload,
    string mediaRoot,
    string output,
    byte[] key)
{
    var result = new List<Dictionary<string, string>>();
    var outputMedia = Path.Combine(output, "media");
    foreach (var avatar in payload["users"]
        .Select(row => row["avatar"] as string)
        .Where(value => !string.IsNullOrWhiteSpace(value))
        .Distinct(StringComparer.OrdinalIgnoreCase))
    {
        var relative = avatar!.Replace('/', Path.DirectorySeparatorChar);
        var source = Path.GetFullPath(Path.Combine(mediaRoot, relative));
        var root = Path.GetFullPath(mediaRoot) + Path.DirectorySeparatorChar;
        if (!source.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(source))
            throw new FileNotFoundException($"Referenced avatar is missing or unsafe: {avatar}");
        var plaintext = File.ReadAllBytes(source);
        Directory.CreateDirectory(outputMedia);
        var encryptedName = Path.GetFileName(relative) + ".tmx";
        File.WriteAllBytes(Path.Combine(outputMedia, encryptedName), ExportCrypto.Encrypt(plaintext, key));
        result.Add(new Dictionary<string, string>
        {
            ["encrypted_file"] = $"media/{encryptedName}",
            ["destination"] = avatar,
            ["sha256"] = Convert.ToHexStringLower(SHA256.HashData(plaintext)),
        });
    }
    return result;
}

file sealed record Arguments(
    string Connection,
    string Output,
    string MediaRoot,
    string KeyEnvironment)
{
    public static Arguments Parse(string[] values)
    {
        var options = values
            .Chunk(2)
            .Where(pair => pair.Length == 2 && pair[0].StartsWith("--"))
            .ToDictionary(pair => pair[0], pair => pair[1]);
        var connection = options.GetValueOrDefault("--connection")
            ?? Environment.GetEnvironmentVariable("LEGACY_SQLSERVER_CONNECTION")
            ?? throw new ArgumentException("Provide --connection or LEGACY_SQLSERVER_CONNECTION");
        var output = options.GetValueOrDefault("--output")
            ?? throw new ArgumentException("Provide --output");
        var mediaRoot = options.GetValueOrDefault("--media-root")
            ?? Path.Combine("TaskManagement.API", "wwwroot");
        var keyEnvironment = options.GetValueOrDefault("--key-env") ?? "LEGACY_EXPORT_KEY";
        return new Arguments(connection, Path.GetFullPath(output), Path.GetFullPath(mediaRoot), keyEnvironment);
    }
}
