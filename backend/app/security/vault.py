import json
import os
import base64
from argon2.low_level import hash_secret_raw, Type
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

VAULT_FILE = os.path.join(os.path.dirname(__file__), 'vault.json')

class VaultLockedError(Exception):
    pass

class VaultItemNotFoundError(Exception):
    pass

class PersonalVault:
    def __init__(self):
        self._key = None
        
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        # Argon2id for key derivation (OWASP recommended)
        return hash_secret_raw(
            secret=password.encode('utf-8'),
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID
        )

    def initialize(self, password: str):
        """Creates a new vault or overrides the existing one."""
        salt = get_random_bytes(16)
        self._key = self._derive_key(password, salt)
        data = {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "items": {}
        }
        with open(VAULT_FILE, 'w') as f:
            json.dump(data, f)

    def unlock(self, password: str) -> bool:
        """Unlocks the vault."""
        if not os.path.exists(VAULT_FILE):
            return False
            
        with open(VAULT_FILE, 'r') as f:
            data = json.load(f)
            
        salt = base64.b64decode(data['salt'])
        self._key = self._derive_key(password, salt)
        return True
        
    def lock(self):
        self._key = None
        
    def is_locked(self) -> bool:
        return self._key is None

    def set(self, field_name: str, value: str):
        if self.is_locked():
            raise VaultLockedError("Vault is locked")
            
        # Encrypt with AES-256-GCM
        nonce = get_random_bytes(12)
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(value.encode('utf-8'))
        
        with open(VAULT_FILE, 'r') as f:
            data = json.load(f)
            
        data['items'][field_name] = {
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }
        
        with open(VAULT_FILE, 'w') as f:
            json.dump(data, f)

    def get(self, field_name: str) -> str:
        if self.is_locked():
            raise VaultLockedError("Vault is locked")
            
        with open(VAULT_FILE, 'r') as f:
            data = json.load(f)
            
        if field_name not in data.get('items', {}):
            raise VaultItemNotFoundError(f"Item '{field_name}' not found in vault")
            
        item = data['items'][field_name]
        nonce = base64.b64decode(item['nonce'])
        tag = base64.b64decode(item['tag'])
        ciphertext = base64.b64decode(item['ciphertext'])
        
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext.decode('utf-8')
        except ValueError:
            raise VaultLockedError("Decryption failed. Incorrect master password.")

# Global singleton
vault = PersonalVault()
