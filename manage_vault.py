import sys
import os

# Add backend to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.security.vault import vault, VaultLockedError

def main():
    print("🛡️ VisiLite Personal Vault Manager")
    print("1. Initialize New Vault")
    print("2. Add/Update Field")
    print("3. Read Field")
    
    choice = input("Select an option (1-3): ")
    
    if choice == '1':
        password = input("Create Master Password: ")
        vault.initialize(password)
        print("✅ Vault initialized successfully!")
        
    elif choice == '2':
        password = input("Enter Master Password: ")
        if not vault.unlock(password):
            print("❌ Vault not found. Please initialize first.")
            return
        
        field = input("Field Name (e.g. FIRST_NAME): ")
        value = input(f"Value for {field}: ")
        vault.set(field, value)
        print(f"✅ Secured {field} into vault.")
        
    elif choice == '3':
        password = input("Enter Master Password: ")
        if not vault.unlock(password):
            print("❌ Vault not found. Please initialize first.")
            return
            
        field = input("Field Name to read: ")
        try:
            val = vault.get(field)
            print(f"🔓 {field} = {val}")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
