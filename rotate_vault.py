import sys, os
sys.path.append('backend')
from app.security.vault import vault

if not vault.unlock('Vivek@0570'):
    print('Failed to unlock old vault')
    sys.exit(1)

items = ['Name', 'Phone Number', 'Roll Number']
data = {}
for item in items:
    try:
        data[item] = vault.get(item)
    except Exception as e:
        print(e)

new_pass = os.getenv('VAULT_PASSWORD', 'SecurePass123!')
vault.initialize(new_pass)
for k, v in data.items():
    vault.set(k, v)
print('Vault rotated successfully with new password!')
