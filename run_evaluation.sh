#!/bin/bash
# D4J Fix Evaluation Runner
# This script ensures the correct Perl environment is used

# Use Homebrew Perl (which has the required modules installed)
export PATH="/opt/homebrew/bin:$PATH"

# Run the evaluation
python -m evaluation.cli "$@"
