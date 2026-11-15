#!/usr/bin/env bash
set -e

echo "========================================================"
echo "        🧠 MemCore One-Click Setup for macOS / Linux    "
echo "========================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 was not found! Please install Python 3.10+."
    exit 1
fi

echo "[1/3] Installing MemCore..."
python3 -m pip install -e .

echo "[2/3] Activating global Antigravity & MCP plugin..."
python3 -m memcore.cli init

echo ""
echo "========================================================"
echo " ✨ SUCCESS! MemCore is installed and ready to use!   "
echo "========================================================"
echo ""
echo "In any project folder, simply run: memcore init"
echo ""
