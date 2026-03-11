#!/bin/bash
# Test script for agentic-report endpoint
# Usage: ./test_agentic.sh path/to/your/file.xlsm

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-excel-file>"
    echo "Example: $0 ~/Downloads/GIR_TopSide_INS_Program_2025.xlsm"
    exit 1
fi

FILE_PATH="$1"

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

echo "Uploading $FILE_PATH to agentic-report endpoint..."
echo ""

curl -X POST "http://localhost:8000/agentic-report" \
  -F "database=@$FILE_PATH" \
  -H "Accept: application/json" \
  | python3 -m json.tool

echo ""
echo "Done!"

