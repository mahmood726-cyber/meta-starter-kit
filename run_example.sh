#!/usr/bin/env bash
# Run this (Mac/Linux) to build the example meta-analysis and open it.
# Needs Python 3 installed.
cd "$(dirname "$0")" || exit 1
echo "Building the example meta-analysis..."
if ! python3 build.py configs/example_finerenone_ckd.json; then
  echo
  echo "Could not run. Is Python 3 installed?  Try:  python3 --version"
  exit 1
fi
echo
echo "Opening the result..."
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open output/example_finerenone_ckd.html
elif command -v open >/dev/null 2>&1; then
  open output/example_finerenone_ckd.html
else
  echo "Open this file in a browser: output/example_finerenone_ckd.html"
fi
echo
echo "To make your own: copy a file in configs/, edit the trial numbers,"
echo "then run:  python3 build.py configs/your_file.json"
