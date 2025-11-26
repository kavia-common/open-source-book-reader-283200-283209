#!/bin/bash
cd /home/kavia/workspace/code-generation/open-source-book-reader-283200-283209/kindle_clone_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

