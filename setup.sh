#!/bin/bash

echo "Setting up Whisper CLI..."

# Install system dependencies for PyAudio (Ubuntu/Debian)
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Make the script executable
chmod +x whisper_cli.py

echo "Setup complete! Run './whisper_cli.py' to start the application."