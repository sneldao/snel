#!/usr/bin/env python3
import subprocess
import sys

def generate_requirements():
    """Generate requirements.txt from poetry dependencies."""
    try:
        # Run poetry export command
        result = subprocess.run(
            ["poetry", "export", "-f", "requirements.txt", "--without-hashes"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Write the output to requirements.txt
        with open("requirements.txt", "w") as f:
            f.write(result.stdout)
            
        print("Successfully generated requirements.txt")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating requirements.txt: {e.stderr}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(generate_requirements()) 