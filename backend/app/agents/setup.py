#!/usr/bin/env python3
"""
SNEL DeFi Agent Setup Script
ENHANCEMENT FIRST: Easy setup for Coral Protocol integration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_status(message):
    print(f"[SETUP] {message}")

def run_command(command, check=True):
    """Run command with error handling"""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {command}")
        print(f"[ERROR] Output: {e.stdout}")
        print(f"[ERROR] Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def setup_environment():
    """Setup Python environment and dependencies"""
    print_status("Setting up SNEL DeFi Agent environment...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print(f"[ERROR] Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    print_status(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
    
    # Install dependencies
    print_status("Installing Coral Protocol dependencies...")
    agents_dir = Path(__file__).parent
    requirements_file = agents_dir / "requirements.txt"
    
    if requirements_file.exists():
        result = run_command(f"pip install -r {requirements_file}")
        if result.returncode == 0:
            print_status("Dependencies installed successfully")
        else:
            print_status("Some dependencies may have failed to install")
    else:
        print_status("Requirements file not found, skipping dependency installation")

def setup_config():
    """Setup configuration files"""
    print_status("Setting up configuration...")
    
    agents_dir = Path(__file__).parent
    env_template = agents_dir / ".env.template"
    env_file = agents_dir / ".env"
    
    if env_template.exists() and not env_file.exists():
        shutil.copy(env_template, env_file)
        print_status(f"Created {env_file} from template")
        print_status("Please edit .env file with your configuration values")
    elif env_file.exists():
        print_status("Configuration file already exists")
    else:
        print_status("No template file found")

def verify_snel_services():
    """Verify SNEL backend services are available"""
    print_status("Verifying SNEL backend services...")
    
    backend_dir = Path(__file__).parent.parent
    service_dirs = [
        "services/ai",
        "services/external", 
        "services/portfolio"
    ]
    
    missing_services = []
    for service_dir in service_dirs:
        service_path = backend_dir / service_dir
        if not service_path.exists():
            missing_services.append(service_dir)
    
    if missing_services:
        print_status(f"WARNING: Missing SNEL services: {missing_services}")
        print_status("Please ensure SNEL backend is properly installed")
    else:
        print_status("SNEL backend services verified")

def create_startup_script():
    """Create startup script for the agent"""
    print_status("Creating startup script...")
    
    agents_dir = Path(__file__).parent
    startup_script = agents_dir / "start_agent.py"
    
    startup_content = '''#!/usr/bin/env python3
"""
SNEL DeFi Agent Startup Script
ENHANCEMENT: Easy agent startup with error handling
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from snel_defi_agent import main
    
    if __name__ == "__main__":
        print("Starting SNEL DeFi Agent...")
        asyncio.run(main())
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Agent startup failed: {e}")
    sys.exit(1)
'''
    
    with open(startup_script, 'w') as f:
        f.write(startup_content)
    
    # Make executable
    os.chmod(startup_script, 0o755)
    print_status("Startup script created")

def main():
    """Main setup process"""
    print("=" * 60)
    print("SNEL DeFi Agent - Coral Protocol Setup")
    print("AI-Powered Cross-Chain DeFi Assistant")
    print("=" * 60)
    
    try:
        setup_environment()
        setup_config()
        verify_snel_services()
        create_startup_script()
        
        print_status("Setup completed successfully!")
        print_status("Next steps:")
        print_status("1. Edit .env file with your configuration")
        print_status("2. Ensure SNEL backend services are running")
        print_status("3. Run: python start_agent.py")
        
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
