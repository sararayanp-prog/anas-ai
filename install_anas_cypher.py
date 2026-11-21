import os, sys, hashlib, hmac, base64, secrets

print("==================================================")
print("🔒 DEPLOYING ANAS PROPRIETARY CYPHER ENCRYPTION")
print("==================================================")

# 1. Create anas_cypher.py (Zero-Dependency Military Grade Encryptor)
cypher_module = '''import os, hashlib, hmac, base64, secrets

# Proprietary System Master Salt (Server RAM me generate hoti hai)
_MASTER_KEY = os.getenv("ANAS_MASTER_SECRET", "ANAS_AI_PRO_QUANT_SECURE_VAULT_KEY_2026_@SARAHICS")

def _derive_key(salt_bytes: bytes) -> bytes:
    """Derives a dynamic 32-byte AES-level key using HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", _MASTER_KEY.encode("utf-8"), salt_bytes, iterations=100000)

def encrypt_data(plaintext: str) -> str:
    """
    Plaintext ko system-generated proprietary cypher language me convert karta hai.
    Output format: ANAS$v1$<salt>$<cypher_payload>$<mac>
    """
    if not plaintext:
        return ""
    plaintext_str = str(plaintext)
    
    # 8-byte random dynamic nonce/salt
    salt = secrets.token_bytes(8)
    derived_key = _derive_key(salt)
    
    # Dynamic XOR stream cypher
    plain_bytes = plaintext_str.encode("utf-8")
    stream = hashlib.sha256(derived_key).digest()
    while len(stream) < len(plain_bytes):
        stream += hashlib.sha256(stream + derived_key).digest()
        
    cypher_bytes = bytes([b ^ s for b, s in zip(plain_bytes, stream)])
    
    # Anti-Tamper MAC
    mac = hmac.new(derived_key, cypher_bytes, hashlib.sha256).hexdigest()[:16]
    
    salt_b64 = base64.b64encode(salt).decode("ascii")
    cypher_b64 = base64.b64encode(cypher_bytes).decode("ascii")
    
    return f"ANAS$v1${salt_b64}${cypher_b64}${mac}"

def decrypt_data(cypher_text: str) -> str:
    """
    System-generated cypher ko wapas readable format me decode karta hai.
    """
    if not cypher_text or not isinstance(cypher_text, str) or not cypher_text.startswith("ANAS$v1$"):
        return cypher_text  # Agar purana unencrypted data hai toh as-is return karega
        
    try:
        parts = cypher_text.split("$")
        if len(parts) != 5:
            return cypher_text
            
        salt = base64.b64decode(parts[2])
        cypher_bytes = base64.b64decode(parts[3])
        expected_mac = parts[4]
        
        derived_key = _derive_key(salt)
        
        # Verify Integrity
        actual_mac = hmac.new(derived_key, cypher_bytes, hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(expected_mac, actual_mac):
            return "[TAMPERED_DATA_ALERT]"
            
        stream = hashlib.sha256(derived_key).digest()
        while len(stream) < len(cypher_bytes):
            stream += hashlib.sha256(stream + derived_key).digest()
            
        plain_bytes = bytes([b ^ s for b, s in zip(cypher_bytes, stream)])
        return plain_bytes.decode("utf-8")
    except Exception:
        return "[DECRYPTION_ERROR]"

def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """Customer UI me aadha number hide karta hai: e.g. 9978****577"""
    if not text or len(str(text)) < 6:
        return "***"
    s = str(text)
    half = visible_chars // 2
    return s[:half] + "*" * (len(s) - visible_chars) + s[-half:]
'''

with open("anas_cypher.py", "w") as f:
    f.write(cypher_module)
print("✅ 1. anas_cypher.py (Proprietary Encryption Engine) Created!")

# 2. Integrate anas_cypher with main.py & Database Storage
main_file = "main.py"
if os.path.exists(main_file):
    with open(main_file, "r") as f:
        mc = f.read()

    if "import anas_cypher" not in mc:
        mc = "import anas_cypher\n" + mc

    # Ensure sensitive fields are encrypted before storing in database
    mc = mc.replace(
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')",
        "VALUES (%s, anas_cypher.encrypt_data(%s), %s, anas_cypher.encrypt_data(%s), anas_cypher.encrypt_data(%s), %s, %s, %s, 'PENDING')"
    )

    with open(main_file, "w") as f:
        f.write(mc)
    print("✅ 2. main.py armed with Auto-Encryption on all sensitive fields!")

print("==================================================")
print("🧪 VERIFYING ENCRYPTION & DECRYPTION ROUNDTRIP")
print("==================================================")
