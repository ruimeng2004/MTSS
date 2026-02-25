#!/bin/bash
# Install Perl DBI dependencies for Defects4J

set -e

echo "=========================================="
echo "Installing Perl DBI Dependencies"
echo "=========================================="

# Check if cpanm is available (faster and more reliable than cpan)
if command -v cpanm &> /dev/null; then
    echo "✓ Using cpanm (faster installer)"
    cpanm --notest DBI
    cpanm --notest DBD::CSV
else
    echo "✓ Using cpan"
    # Install without tests to speed up
    cpan -T DBI
    cpan -T DBD::CSV
fi

echo ""
echo "=========================================="
echo "Verifying Installation"
echo "=========================================="

# Verify DBI
if perl -MDBI -e 'print "DBI version: $DBI::VERSION\n"' 2>/dev/null; then
    echo "✓ DBI installed successfully"
else
    echo "✗ DBI installation failed"
    exit 1
fi

# Verify DBD::CSV
if perl -MDBD::CSV -e 'print "DBD::CSV installed\n"' 2>/dev/null; then
    echo "✓ DBD::CSV installed successfully"
else
    echo "✗ DBD::CSV installation failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Testing Defects4J"
echo "=========================================="

D4J_BIN="/Users/mengrui/Desktop/D4J/defects4j/framework/bin/defects4j"

if [ -f "$D4J_BIN" ]; then
    if "$D4J_BIN" info -p Chart &> /dev/null; then
        echo "✓ Defects4J is working correctly"
    else
        echo "⚠ Defects4J test failed, checking error..."
        "$D4J_BIN" info -p Chart 2>&1 | head -10
    fi
else
    echo "⚠ Defects4J binary not found at: $D4J_BIN"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run: python check_prerequisites.py"
echo "  2. Test: python test_single_bug.py"
