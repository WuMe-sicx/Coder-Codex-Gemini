#!/bin/bash
# CCG One-Click Setup Script for macOS/Linux
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Helper functions
write_step() {
    echo -e "\n${CYAN}[*] $1${NC}"
}

write_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

write_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

write_warning() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# ==============================================================================
# Step 1: Check dependencies
# ==============================================================================
write_step "Step 1: Checking dependencies..."

# Check and install uv
if command -v uv &> /dev/null; then
    write_success "uv is installed"
else
    write_warning "uv is not installed, installing automatically..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        export PATH="$HOME/.local/bin:$PATH"
        write_success "uv installed successfully"
    else
        write_error "Failed to install uv automatically"
        echo "Please install uv manually: https://github.com/astral-sh/uv"
        exit 1
    fi
fi

# Check claude CLI
if command -v claude &> /dev/null; then
    write_success "claude CLI is installed"
else
    write_error "claude CLI is not installed"
    echo "Please install Claude Code CLI first: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

# ==============================================================================
# Step 2: Register MCP server
# ==============================================================================
write_step "Step 2: Registering MCP server..."

# Check if ccg is already registered by inspecting settings.json
SETTINGS_FILE="$HOME/.claude/settings.json"
MCP_REGISTERED=false
if [ -f "$SETTINGS_FILE" ] && grep -q '"ccg"' "$SETTINGS_FILE" 2>/dev/null; then
    MCP_REGISTERED=true
fi

if [ "$MCP_REGISTERED" = true ]; then
    write_warning "MCP server 'ccg' is already registered, skipping"
else
    if claude mcp add ccg -s user --transport stdio -- uvx --from "file:$SCRIPT_DIR" ccg-mcp; then
        write_success "MCP server registered"
    else
        write_error "Failed to register MCP server"
        echo "You can register manually:"
        echo "  claude mcp add ccg -s user --transport stdio -- uvx --from \"file:$SCRIPT_DIR\" ccg-mcp"
        exit 1
    fi
fi

# ==============================================================================
# Step 3: Install Skills + Configure CLAUDE.md
# ==============================================================================
write_step "Step 3: Installing Skills and configuring CLAUDE.md..."

# Ensure directories exist
mkdir -p "$HOME/.claude/skills"

# --- Skills ---
SKILLS_DIR="$HOME/.claude/skills"

install_skill() {
    local name="$1"
    local source="$SCRIPT_DIR/skills/$name"
    local dest="$SKILLS_DIR/$name"

    if [ ! -d "$source" ]; then
        write_warning "$name skill source not found, skipping"
        return
    fi

    # Skip if already installed and identical
    if [ -d "$dest" ] && diff -rq "$source" "$dest" &>/dev/null; then
        write_success "$name skill is up to date"
        return
    fi

    rm -rf "$dest"
    cp -r "$source" "$dest"
    write_success "Installed $name skill"
}

install_skill "ccg-workflow"
install_skill "gemini-collaboration"

# --- CLAUDE.md ---
CLAUDE_MD_PATH="$HOME/.claude/CLAUDE.md"
CCG_MARKER="# CCG Configuration"
CCG_CONFIG_PATH="$SCRIPT_DIR/templates/ccg-global-prompt.md"

if [ ! -f "$CCG_CONFIG_PATH" ]; then
    write_warning "CCG global prompt template not found at $CCG_CONFIG_PATH"
elif [ ! -f "$CLAUDE_MD_PATH" ]; then
    cp "$CCG_CONFIG_PATH" "$CLAUDE_MD_PATH"
    write_success "Created global CLAUDE.md"
elif grep -qF "$CCG_MARKER" "$CLAUDE_MD_PATH"; then
    write_success "CCG configuration already in CLAUDE.md"
else
    echo "" >> "$CLAUDE_MD_PATH"
    cat "$CCG_CONFIG_PATH" >> "$CLAUDE_MD_PATH"
    write_success "Appended CCG configuration to CLAUDE.md"
fi

# ==============================================================================
# Step 4: Configure Coder
# ==============================================================================
write_step "Step 4: Configuring Coder..."

CONFIG_DIR="$HOME/.ccg-mcp"
CONFIG_PATH="$CONFIG_DIR/config.toml"
mkdir -p "$CONFIG_DIR"

# Check if config already exists
if [ -f "$CONFIG_PATH" ]; then
    write_warning "Config file already exists at $CONFIG_PATH"
    read -p "Overwrite? (y/N): " OVERWRITE
    if [ "$OVERWRITE" != "y" ] && [ "$OVERWRITE" != "Y" ]; then
        write_warning "Skipping Coder configuration"
        echo ""
        echo -e "${GREEN}============================================================${NC}"
        write_success "CCG setup completed successfully!"
        echo -e "${GREEN}============================================================${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Restart Claude Code CLI"
        echo "  2. Verify MCP server: claude mcp list"
        echo "  3. Check available skills: /ccg-workflow"
        echo ""
        exit 0
    fi
fi

# Support non-interactive mode via environment variables
API_TOKEN="${CCG_API_TOKEN:-}"
BASE_URL="${CCG_BASE_URL:-}"
MODEL="${CCG_MODEL:-}"

# Interactive prompts only for missing values
if [ -z "$API_TOKEN" ]; then
    read -s -p "Enter your API Token: " API_TOKEN
    echo
    if [ -z "$API_TOKEN" ]; then
        write_error "API Token is required"
        exit 1
    fi
fi

if [ -z "$BASE_URL" ]; then
    read -p "Enter Base URL (default: https://open.bigmodel.cn/api/anthropic): " BASE_URL
    if [ -z "$BASE_URL" ]; then
        BASE_URL="https://open.bigmodel.cn/api/anthropic"
    fi
fi

if [ -z "$MODEL" ]; then
    read -p "Enter Model (e.g. glm-4.7): " MODEL
    MODEL=$(echo "$MODEL" | xargs)
    if [ -z "$MODEL" ]; then
        write_error "Model is required"
        exit 1
    fi
fi

# Escape special characters for TOML string values (backslash and double quote)
SAFE_API_TOKEN=$(printf '%s' "$API_TOKEN" | sed 's/\\/\\\\/g; s/"/\\"/g')
SAFE_BASE_URL=$(printf '%s' "$BASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')
SAFE_MODEL=$(printf '%s' "$MODEL" | sed 's/\\/\\\\/g; s/"/\\"/g')

# Generate config.toml
cat > "$CONFIG_PATH" << EOF
[coder]
api_token = "$SAFE_API_TOKEN"
base_url = "$SAFE_BASE_URL"
model = "$SAFE_MODEL"

[coder.env]
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
EOF

chmod 600 "$CONFIG_PATH"
write_success "Coder configuration saved to $CONFIG_PATH"

# ==============================================================================
# Done!
# ==============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
write_success "CCG setup completed successfully!"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code CLI"
echo "  2. Verify MCP server: claude mcp list"
echo "  3. Check available skills: /ccg-workflow"
echo ""
