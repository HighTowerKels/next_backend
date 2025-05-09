import os
import re
from pathlib import Path

def find_references():
    project_root = Path(__file__).parent
    excluded_dirs = {'venv', '.git', '__pycache__', 'migrations'}
    service_refs = []
    transaction_refs = []
    
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                    if re.search(r'from\s+services\.|import\s+services', content):
                        service_refs.append(filepath)
                        
                    if re.search(r'from\s+transactions\.|import\s+transactions', content):
                        transaction_refs.append(filepath)
    
    print("=== Service References ===")
    print('\n'.join(service_refs) or "No references found")
    
    print("\n=== Transaction References ===")
    print('\n'.join(transaction_refs) or "No references found")

if __name__ == '__main__':
    find_references()