using System.Security.Cryptography;
using LegacyExport;
using Xunit;

namespace LegacyExport.Tests;

public class ExportFormatTests
{
    [Fact]
    public void EncryptionEnvelopeRoundTrips()
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var plaintext = "sensitive legacy data"u8.ToArray();

        var encrypted = ExportCrypto.Encrypt(plaintext, key);

        Assert.Equal("TMX1", System.Text.Encoding.ASCII.GetString(encrypted[..4]));
        Assert.Equal(plaintext, ExportCrypto.Decrypt(encrypted, key));
    }

    [Fact]
    public void CanonicalHashDoesNotDependOnRowOrder()
    {
        var first = new[]
        {
            new SortedDictionary<string, object?> { ["id"] = 2, ["name"] = "B" },
            new SortedDictionary<string, object?> { ["id"] = 1, ["name"] = "A" },
        };

        Assert.Equal(Canonical.TableHash(first), Canonical.TableHash(first.Reverse()));
    }

    [Fact]
    public void LegacySaigonTimeConvertsAcrossUtcDateBoundary()
    {
        var legacy = new DateTime(2026, 1, 1, 0, 30, 0, DateTimeKind.Unspecified);

        Assert.Equal(
            "2025-12-31T17:30:00.000000Z",
            Canonical.LegacyDateTimeText(legacy)
        );
    }
}
