#!/bin/bash
# setup.sh

# Exit on error
set -e

echo "Setting up Agent Smith..."

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install uv if not installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

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