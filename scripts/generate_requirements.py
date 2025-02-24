import subprocess
import sys
from pathlib import Path

def generate_requirements():
    """Generate requirements.txt from poetry dependencies."""
    try:
        # Run poetry export
        result = subprocess.run(
            ["poetry", "export", "-f", "requirements.txt", "--without-hashes"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Write to requirements.txt
        requirements_path = Path("requirements.txt")
        requirements_path.write_text(result.stdout)
        print("Successfully generated requirements.txt")
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating requirements.txt: {e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_requirements() 