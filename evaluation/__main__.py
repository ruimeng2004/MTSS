"""Entry point for running evaluation as a module.

This allows running the evaluation system with:
    python -m evaluation [args]
"""

from evaluation.cli import main

if __name__ == '__main__':
    main()
