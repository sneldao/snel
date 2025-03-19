#!/usr/bin/env python
"""
Script to update all import statements from emp_agents to app.utils.

This script scans through all Python files in the project and replaces
import statements referencing emp_agents with imports from app.utils.
"""
import os
import re
import sys
from pathlib import Path

def fix_imports(file_path):
    """Fix imports in a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace import statements
    updated_content = re.sub(
        r'from emp_agents(\.[\w\.]+)? import ([\w\, ]+)',
        r'from app.utils\1 import \2  # Updated from emp_agents',
        content
    )
    
    # Replace raw imports
    updated_content = re.sub(
        r'import app.utils  # Updated from emp_agents(\.[\w\.]+)?( as [\w]+)?',
        r'import app.utils\1\2  # Updated from emp_agents',
        updated_content
    )
    
    # Write back if changes were made
    if content != updated_content:
        print(f"Updating imports in {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        return True
    return False

def main():
    """Main function to run the script."""
    # Get the root directory (parent of the script directory)
    root_dir = Path(__file__).parent.parent
    
    print(f"Starting import fixes from {root_dir}")
    
    # Count of files updated
    updated_count = 0
    
    # Walk through directories
    for dirpath, _, filenames in os.walk(root_dir):
        # Skip virtual environments and hidden directories
        if (
            '__pycache__' in dirpath or 
            '.git' in dirpath or 
            '.venv' in dirpath or
            'node_modules' in dirpath
        ):
            continue
        
        # Process Python files
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                if fix_imports(filepath):
                    updated_count += 1
    
    print(f"Updated imports in {updated_count} files")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 