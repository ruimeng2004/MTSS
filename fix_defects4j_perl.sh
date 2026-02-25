#!/bin/bash
# Fix Defects4J to use Homebrew Perl with DBI modules

set -e

D4J_DIR="/Users/mengrui/Desktop/D4J/defects4j"
HOMEBREW_PERL="/opt/homebrew/bin/perl"

echo "=========================================="
echo "Fixing Defects4J Perl Configuration"
echo "=========================================="

# Check if Homebrew Perl has DBI
echo "Checking Homebrew Perl modules..."
if ! $HOMEBREW_PERL -MDBI -e 'print "DBI OK\n"' 2>/dev/null; then
    echo "✗ DBI not found in Homebrew Perl"
    exit 1
fi

if ! $HOMEBREW_PERL -MDBD::CSV -e 'print "DBD::CSV OK\n"' 2>/dev/null; then
    echo "✗ DBD::CSV not found in Homebrew Perl"
    exit 1
fi

echo "✓ Homebrew Perl has required modules"

# Find all Perl scripts in Defects4J
echo ""
echo "Updating Defects4J Perl scripts..."

# Backup and update main defects4j script
if [ -f "$D4J_DIR/framework/bin/defects4j" ]; then
    # Create backup if not exists
    if [ ! -f "$D4J_DIR/framework/bin/defects4j.bak" ]; then
        cp "$D4J_DIR/framework/bin/defects4j" "$D4J_DIR/framework/bin/defects4j.bak"
        echo "✓ Backed up defects4j script"
    fi
    
    # Update shebang
    sed -i '' "1s|.*|#!$HOMEBREW_PERL|" "$D4J_DIR/framework/bin/defects4j"
    echo "✓ Updated defects4j shebang"
fi

# Update all Perl scripts in bin/d4j/
if [ -d "$D4J_DIR/framework/bin/d4j" ]; then
    for script in "$D4J_DIR/framework/bin/d4j"/*; do
        if [ -f "$script" ] && head -1 "$script" | grep -q "perl"; then
            # Backup
            if [ ! -f "$script.bak" ]; then
                cp "$script" "$script.bak"
            fi
            # Update shebang
            sed -i '' "1s|.*|#!$HOMEBREW_PERL|" "$script"
        fi
    done
    echo "✓ Updated d4j/* scripts"
fi

echo ""
echo "=========================================="
echo "Testing Defects4J"
echo "=========================================="

# Test defects4j command
if "$D4J_DIR/framework/bin/defects4j" info -p Chart > /dev/null 2>&1; then
    echo "✓ Defects4J is working correctly!"
    echo ""
    "$D4J_DIR/framework/bin/defects4j" info -p Chart | head -5
else
    echo "✗ Defects4J test failed"
    "$D4J_DIR/framework/bin/defects4j" info -p Chart 2>&1 | head -20
    exit 1
fi

echo ""
echo "=========================================="
echo "Success!"
echo "=========================================="
echo ""
echo "Defects4J is now using: $HOMEBREW_PERL"
echo ""
echo "Next steps:"
echo "  1. Run: python check_prerequisites.py"
echo "  2. Test: python test_single_bug.py"
