#!/bin/bash
# setup.sh

# Exit on error
set -e

echo "Setting up Agent Smith..."

if ! command -v pyenv &> /dev/null; then
    echo "Installing pyenv and Python 3.12..."
    # Install build dependencies
    sudo apt-get update
    sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git

    # Install pyenv
    curl https://pyenv.run | bash
    
    # Set up environment variables for current session
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
    
    # Add pyenv to .profile for persistence
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
    echo 'eval "$(pyenv init --path)"' >> ~/.profile
    echo 'eval "$(pyenv init -)"' >> ~/.profile
    
    # Install Python 3.12
    pyenv install 3.12.0
    pyenv global 3.12.0
else
    echo "pyenv already installed, checking Python version..."
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
    
    if ! pyenv versions | grep -q 3.12; then
        echo "Installing Python 3.12..."
        pyenv install 3.12.0
        pyenv global 3.12.0
    fi
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with Python 3.12..."
    python -m venv venv
else
    echo "Updating existing virtual environment..."
    rm -rf venv
    python -m venv venv
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