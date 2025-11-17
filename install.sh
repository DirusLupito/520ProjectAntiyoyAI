#!/bin/bash
# Installation script for Antiyoy AI project
# Sets up virtual environment and installs all dependencies

set -e  # Exit on error

echo "=========================================="
echo "Antiyoy AI Project Installation"
echo "=========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo ""
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install the package in development mode
echo ""
echo "Installing project package..."
pip install -e .

# Install requirements
if [ -f "requirements.txt" ]; then
    echo ""
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the AlphaZero training:"
echo "  cd alpha-zero"
echo "  python main.py"
echo ""
echo "To run with auto-restart on crash:"
echo "  cd alpha-zero"
echo "  python run_training.py"
echo ""
