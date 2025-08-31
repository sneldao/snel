#!/usr/bin/env python3
"""
Simple validation script for SNEL foundation work.

This script validates core configuration structure and mock elimination
without requiring external dependencies like aiohttp or aioredis.

Usage:
    python simple_validate.py
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def check_mock_elimination(filepath, mock_patterns):
    """Check that mock patterns have been eliminated from a file."""
    if not os.path.exists(filepath):
        print(f"⚠️  Cannot check {filepath} - file not found")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        found_mocks = []
        for pattern in mock_patterns:
            if pattern in content:
                found_mocks.append(pattern)

        if found_mocks:
            print(f"❌ Mock patterns found in {os.path.basename(filepath)}:")
            for mock in found_mocks:
                print(f"   - {mock}")
            return False
        else:
            print(f"✅ No mock patterns found in {os.path.basename(filepath)}")
            return True

    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def validate_imports(module_path, description):
    """Validate that a module can be imported (syntax check)."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec is None:
            print(f"❌ {description}: Cannot create module spec")
            return False

        # Just check if the file can be parsed (syntax validation)
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            compile(content, module_path, 'exec')
            print(f"✅ {description}: Syntax valid")
            return True
        except SyntaxError as e:
            print(f"❌ {description}: Syntax error - {e}")
            return False

    except Exception as e:
        print(f"❌ {description}: Import validation failed - {e}")
        return False

def main():
    """Main validation routine."""
    print("🚀 SNEL Foundation Simple Validation")
    print("=" * 50)
    print("Validating Week 1-2: AGGRESSIVE CONSOLIDATION")
    print("Testing file structure and mock elimination")
    print("")

    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__))
    os.chdir(backend_dir)

    # Check core files exist
    print("📁 File Structure Validation:")
    print("-" * 30)

    file_checks = [
        ("app/core/config_manager.py", "Configuration Manager"),
        ("app/core/errors.py", "Error Framework"),
        ("app/protocols/zerox.py", "0x Protocol"),
        ("app/protocols/zerox_v2.py", "0x Protocol v2"),
        ("app/services/axelar_service.py", "Axelar Service"),
        ("app/protocols/uniswap_adapter.py", "Uniswap Adapter"),
    ]

    files_ok = []
    for filepath, desc in file_checks:
        files_ok.append(check_file_exists(filepath, desc))

    print("")

    # Check syntax validation
    print("🔧 Syntax Validation:")
    print("-" * 30)

    syntax_checks = [
        ("app/core/config_manager.py", "Configuration Manager"),
        ("app/core/errors.py", "Error Framework"),
        ("app/protocols/zerox.py", "0x Protocol"),
        ("app/services/axelar_service.py", "Axelar Service"),
    ]

    syntax_ok = []
    for filepath, desc in syntax_checks:
        if os.path.exists(filepath):
            syntax_ok.append(validate_imports(filepath, desc))
        else:
            syntax_ok.append(False)

    print("")

    # Check mock elimination
    print("🚫 Mock Elimination Validation:")
    print("-" * 30)

    # Patterns that should NOT exist (mock implementations)
    mock_patterns = [
        'return "0x0000000000000000000000000000000000000000"',
        'return "0.01"  # Default fee',
        'amount * Decimal("0.95")',
        '# Mock 5% slippage',
        'quote.get("gas", "500000")',
        '# Default gas limit if not provided',
        '# Return a placeholder',
        '# For now, return a mock',
        'estimated_output = amount * Decimal("0.95")',
        'hardcoded',
        'placeholder - in real implementation'
    ]

    mock_checks = [
        ("app/services/axelar_service.py", "Axelar Service"),
        ("app/protocols/uniswap_adapter.py", "Uniswap Adapter"),
        ("app/protocols/zerox.py", "0x Protocol"),
    ]

    mocks_ok = []
    for filepath, desc in mock_checks:
        mocks_ok.append(check_mock_elimination(filepath, mock_patterns))

    print("")

    # Check configuration consolidation
    print("🔗 Configuration Consolidation:")
    print("-" * 30)

    config_indicators = []

    # Check if old scattered config is being replaced
    old_config_files = [
        "app/config/tokens.py",
        "app/config/chains.py"
    ]

    config_manager_usage = []

    # Check files that should now use config_manager
    files_to_check = [
        "app/protocols/zerox.py",
        "app/services/axelar_service.py"
    ]

    for filepath in files_to_check:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if "config_manager" in content:
                    print(f"✅ {os.path.basename(filepath)}: Uses config_manager")
                    config_manager_usage.append(True)
                else:
                    print(f"⚠️  {os.path.basename(filepath)}: No config_manager usage found")
                    config_manager_usage.append(False)

            except Exception as e:
                print(f"❌ Error checking {filepath}: {e}")
                config_manager_usage.append(False)

    print("")

    # Error handling check
    print("⚠️  Error Handling Validation:")
    print("-" * 30)

    error_checks = []

    for filepath in ["app/services/axelar_service.py", "app/protocols/zerox.py"]:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for proper error imports
                has_error_imports = ("ProtocolError" in content or
                                   "ValidationError" in content or
                                   "NetworkError" in content)

                if has_error_imports:
                    print(f"✅ {os.path.basename(filepath)}: Has proper error handling")
                    error_checks.append(True)
                else:
                    print(f"⚠️  {os.path.basename(filepath)}: Limited error handling")
                    error_checks.append(False)

            except Exception as e:
                print(f"❌ Error checking {filepath}: {e}")
                error_checks.append(False)

    print("")

    # Summary
    print("=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)

    files_score = sum(files_ok)
    syntax_score = sum(syntax_ok)
    mocks_score = sum(mocks_ok)
    config_score = sum(config_manager_usage)
    error_score = sum(error_checks)

    total_checks = len(files_ok) + len(syntax_ok) + len(mocks_ok) + len(config_manager_usage) + len(error_checks)
    total_passed = files_score + syntax_score + mocks_score + config_score + error_score

    print(f"File Structure:      {files_score}/{len(files_ok)} ({'✅ PASS' if files_score == len(files_ok) else '⚠️  PARTIAL'})")
    print(f"Syntax Validation:   {syntax_score}/{len(syntax_ok)} ({'✅ PASS' if syntax_score == len(syntax_ok) else '❌ FAIL'})")
    print(f"Mock Elimination:    {mocks_score}/{len(mocks_ok)} ({'✅ PASS' if mocks_score == len(mocks_ok) else '❌ FAIL'})")
    print(f"Config Manager:      {config_score}/{len(config_manager_usage)} ({'✅ PASS' if config_score == len(config_manager_usage) else '⚠️  PARTIAL'})")
    print(f"Error Handling:      {error_score}/{len(error_checks)} ({'✅ PASS' if error_score == len(error_checks) else '⚠️  PARTIAL'})")

    print(f"\nOverall Score: {total_passed}/{total_checks}")

    if total_passed >= total_checks * 0.8:  # 80% threshold
        print("\n🎉 Foundation consolidation is progressing well!")
        print("📈 Ready to continue with configuration migration")
        success = True
    else:
        print("\n⚠️  Some issues found that need attention")
        print("🔧 Review the validation output above and fix critical issues")
        success = False

    # Specific next steps
    print("\n📋 Next Steps:")
    if mocks_score < len(mocks_ok):
        print("1. 🚫 Complete mock elimination in remaining files")
    if config_score < len(config_manager_usage):
        print("2. 🔗 Migrate remaining services to use ConfigurationManager")
    if syntax_score < len(syntax_ok):
        print("3. 🔧 Fix syntax errors before proceeding")

    print("4. 📦 Install missing dependencies (aiohttp, aioredis)")
    print("5. ✅ Run full integration tests")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
