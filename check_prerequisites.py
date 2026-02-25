#!/usr/bin/env python3
"""Check all prerequisites for the D4J Fix Evaluation System."""

import subprocess
import sys
from pathlib import Path

def check_defects4j():
    """Check if Defects4J is installed and working."""
    print("=" * 60)
    print("Checking Defects4J Installation")
    print("=" * 60)
    
    d4j_path = Path("/Users/mengrui/Desktop/D4J/defects4j")
    d4j_bin = d4j_path / "framework" / "bin" / "defects4j"
    
    if not d4j_bin.exists():
        print(f"❌ Defects4J not found at: {d4j_bin}")
        return False
    
    print(f"✓ Defects4J binary found: {d4j_bin}")
    
    # Test defects4j command
    try:
        result = subprocess.run(
            [str(d4j_bin), "info", "-p", "Chart"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "Can't locate DBI.pm" in result.stderr:
            print("❌ Perl DBI module not installed")
            print("\nTo fix this issue, install Perl DBI:")
            print("  cpan DBI")
            print("  cpan DBD::CSV")
            return False
        elif result.returncode == 0:
            print("✓ Defects4J is working correctly")
            return True
        else:
            print(f"❌ Defects4J error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Defects4J: {e}")
        return False

def check_perl_modules():
    """Check if required Perl modules are installed."""
    print("\n" + "=" * 60)
    print("Checking Perl Modules")
    print("=" * 60)
    
    modules = ["DBI", "DBD::CSV"]
    all_ok = True
    
    for module in modules:
        try:
            result = subprocess.run(
                ["perl", "-M" + module, "-e", "1"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ {module} is installed")
            else:
                print(f"❌ {module} is NOT installed")
                all_ok = False
        except Exception as e:
            print(f"❌ Error checking {module}: {e}")
            all_ok = False
    
    return all_ok

def check_java():
    """Check if Java is installed."""
    print("\n" + "=" * 60)
    print("Checking Java")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version = result.stderr.split('\n')[0]
            print(f"✓ Java is installed: {version}")
            return True
        else:
            print("❌ Java not found")
            return False
    except Exception as e:
        print(f"❌ Error checking Java: {e}")
        return False

def check_git():
    """Check if git is installed."""
    print("\n" + "=" * 60)
    print("Checking Git")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✓ Git is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Git not found")
            return False
    except Exception as e:
        print(f"❌ Error checking Git: {e}")
        return False

def check_evaluation_system():
    """Check if evaluation system files exist."""
    print("\n" + "=" * 60)
    print("Checking Evaluation System")
    print("=" * 60)
    
    required_files = [
        "evaluation/core/evaluator.py",
        "evaluation/core/input_handler.py",
        "evaluation/core/output_parser.py",
        "evaluation/core/patch_normalizer.py",
        "evaluation/core/patch_applicator.py",
        "evaluation/core/test_executor.py",
        "evaluation/core/environment_manager.py",
    ]
    
    all_ok = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path} NOT FOUND")
            all_ok = False
    
    return all_ok

def main():
    """Run all prerequisite checks."""
    print("D4J Fix Evaluation System - Prerequisites Check")
    print()
    
    checks = [
        ("Java", check_java),
        ("Git", check_git),
        ("Perl Modules", check_perl_modules),
        ("Defects4J", check_defects4j),
        ("Evaluation System", check_evaluation_system),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Check '{name}' raised exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if not all_passed:
        print("\n" + "=" * 60)
        print("Action Required")
        print("=" * 60)
        print("\nTo install missing Perl modules:")
        print("  cpan DBI")
        print("  cpan DBD::CSV")
        print("\nOr using cpanm (if installed):")
        print("  cpanm DBI DBD::CSV")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
