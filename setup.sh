#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup
main() {
    print_header "K3s Home Lab Setup Script"
    
    # Check macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        exit 1
    fi
    print_success "Running on macOS"
    
    # Check Homebrew
    print_header "Checking Homebrew"
    if ! command_exists brew; then
        print_error "Homebrew not found. Please install it first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    print_success "Homebrew is installed"
    
    # Install/update required tools
    print_header "Installing/Updating Required Tools"
    
    local tools=("lima" "terraform" "ansible" "socket_vmnet")
    for tool in "${tools[@]}"; do
        if command_exists "$tool" || brew list "$tool" &>/dev/null; then
            print_success "$tool is already installed"
        else
            print_info "Installing $tool..."
            brew install "$tool"
            print_success "$tool installed"
        fi
    done
    
    # Start socket_vmnet service
    print_header "Configuring socket_vmnet"
    
    if sudo brew services list | grep -q "socket_vmnet.*started"; then
        print_success "socket_vmnet service is running"
    else
        print_info "Starting socket_vmnet service..."
        sudo brew services start socket_vmnet
        sleep 2
        print_success "socket_vmnet service started"
    fi
    
    # Copy socket_vmnet binary to expected location
    print_header "Setting up socket_vmnet Binary"
    
    local socket_version=$(ls /opt/homebrew/Cellar/socket_vmnet/ 2>/dev/null | head -1)
    if [ -z "$socket_version" ]; then
        print_error "socket_vmnet not found in Homebrew cellar"
        exit 1
    fi
    
    local socket_source="/opt/homebrew/Cellar/socket_vmnet/$socket_version/bin/socket_vmnet"
    local socket_dest="/opt/socket_vmnet/bin/socket_vmnet"
    
    if [ ! -f "$socket_dest" ] || ! cmp -s "$socket_source" "$socket_dest"; then
        print_info "Copying socket_vmnet binary..."
        sudo mkdir -p /opt/socket_vmnet/bin
        sudo cp "$socket_source" "$socket_dest"
        print_success "socket_vmnet binary copied to $socket_dest"
    else
        print_success "socket_vmnet binary already in place"
    fi
    
    # Configure Lima sudoers
    print_header "Configuring Lima Sudoers"
    
    if [ ! -f "/private/etc/sudoers.d/lima" ]; then
        print_info "Setting up Lima sudoers..."
        limactl sudoers > /tmp/etc_sudoers.d_lima
        sudo install -o root /tmp/etc_sudoers.d_lima "/private/etc/sudoers.d/lima"
        rm /tmp/etc_sudoers.d_lima
        print_success "Lima sudoers configured"
    else
        print_success "Lima sudoers already configured"
    fi
    
    # Make scripts executable
    print_header "Setting up Scripts"
    
    chmod +x "$SCRIPT_DIR/lima/scripts/create-vms.sh"
    chmod +x "$SCRIPT_DIR/lima/scripts/destroy-vms.sh"
    print_success "Lima scripts are executable"
    
    # Print summary
    print_header "Setup Complete!"
    
    echo -e "${GREEN}All prerequisites are installed and configured.${NC}\n"
    echo "Next steps:"
    echo "1. Review the SETUP.md file for detailed instructions"
    echo "2. Create VMs:  cd terraform && terraform init && terraform apply"
    echo "3. Install K3s: cd ../ansible && ansible-playbook -i inventory.yml playbooks/k3s-install.yml"
    echo ""
    echo "For troubleshooting, see TROUBLESHOOTING.md"
    echo ""
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run main function
main "$@"
