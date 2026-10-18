using System.Security.Cryptography;
using System.Text;

namespace LegacyExport;

public static class ExportCrypto
{
    private static readonly byte[] Magic = Encoding.ASCII.GetBytes("TMX1");
    private const int NonceSize = 12;
    private const int TagSize = 16;

    public static byte[] Encrypt(byte[] plaintext, byte[] key)
    {
        ValidateKey(key);
        var nonce = RandomNumberGenerator.GetBytes(NonceSize);
        var ciphertext = new byte[plaintext.Length];
        var tag = new byte[TagSize];
        using var aes = new AesGcm(key, TagSize);
        aes.Encrypt(nonce, plaintext, ciphertext, tag, Magic);
        return [.. Magic, .. nonce, .. ciphertext, .. tag];
    }

    public static byte[] Decrypt(byte[] envelope, byte[] key)
    {
        ValidateKey(key);
        if (envelope.Length <= Magic.Length + NonceSize + TagSize ||
            !envelope.AsSpan(0, Magic.Length).SequenceEqual(Magic))
        {
            throw new CryptographicException("Invalid legacy export envelope");
        }

        var nonce = envelope.AsSpan(Magic.Length, NonceSize);
        var body = envelope.AsSpan(Magic.Length + NonceSize);
        var ciphertext = body[..^TagSize];
        var tag = body[^TagSize..];
        var plaintext = new byte[ciphertext.Length];
        using var aes = new AesGcm(key, TagSize);
        aes.Decrypt(nonce, ciphertext, tag, plaintext, Magic);
        return plaintext;
    }

    private static void ValidateKey(byte[] key)
    {
        if (key.Length != 32)
        {
            throw new ArgumentException("Encryption key must be 32 bytes", nameof(key));
        }
    }
}
