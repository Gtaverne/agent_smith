#!/bin/bash
# setup.sh

# Exit on error
set -e

echo "Setting up Agent Smith..."

# Install Python 3.12 if not present
if ! command -v python3.12 &> /dev/null; then
    echo "Installing Python 3.12..."
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with Python 3.12..."
    python3.12 -m venv venv
else
    echo "Updating existing virtual environment..."
    rm -rf venv
    python3.12 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install pip and uv
echo "Installing pip and uv..."
python -m pip install --upgrade pip
python -m pip install uv

# Install dependencies using uv
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Create systemd service file if it doesn't exist
if [ ! -f "/etc/systemd/system/agent-smith.service" ]; then
    echo "Creating systemd service file..."
    sudo bash -c "cat > /etc/systemd/system/agent-smith.service << EOF
[Unit]
Description=Agent Smith Discord Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$PWD/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$PWD/.env

[Install]
WantedBy=multi-user.target
EOF"

    # Enable the service to start on boot
    sudo systemctl enable agent-smith.service
fi

# Reload systemd to recognize changes
sudo systemctl daemon-reload

echo "Setup complete! Service is ready to be started."
echo "To start the service: sudo systemctl start agent-smith.service"
echo "To check status: sudo systemctl status agent-smith.service"
echo "To view logs: sudo journalctl -u agent-smith.service -f"