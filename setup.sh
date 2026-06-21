#!/bin/bash
# CC One-Click Setup Script for macOS/Linux
# Claude + Codex 双模型协作 MCP 服务器
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

# Check codex CLI (the only reviewer this server drives)
if command -v codex &> /dev/null; then
    write_success "codex CLI is installed"
else
    write_warning "codex CLI is not installed"
    echo "The cc server reviews code via the Codex CLI. Install and log in before use:"
    echo "  https://developers.openai.com/codex/quickstart"
    echo "  codex login"
fi

# ==============================================================================
# Step 2: Register MCP server
# ==============================================================================
write_step "Step 2: Registering MCP server..."

# Check if cc is already registered by inspecting settings.json
SETTINGS_FILE="$HOME/.claude/settings.json"
MCP_REGISTERED=false
if [ -f "$SETTINGS_FILE" ] && grep -q '"cc"' "$SETTINGS_FILE" 2>/dev/null; then
    MCP_REGISTERED=true
fi

if [ "$MCP_REGISTERED" = true ]; then
    write_warning "MCP server 'cc' is already registered, skipping"
else
    if claude mcp add cc -s user --transport stdio -- uvx --from "file:$SCRIPT_DIR" cc-mcp; then
        write_success "MCP server registered"
    else
        write_error "Failed to register MCP server"
        echo "You can register manually:"
        echo "  claude mcp add cc -s user --transport stdio -- uvx --from \"file:$SCRIPT_DIR\" cc-mcp"
        exit 1
    fi
fi

# ==============================================================================
# Step 3: Install Skill + Configure CLAUDE.md
# ==============================================================================
write_step "Step 3: Installing Skill and configuring CLAUDE.md..."

# Ensure directories exist
mkdir -p "$HOME/.claude/skills"

# --- Skill ---
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

install_skill "cc-review"

# Remove skills from earlier layouts if present (codex-review = pre-rename name)
for old_skill in codex-review ccg-workflow gemini-collaboration; do
    if [ -d "$SKILLS_DIR/$old_skill" ]; then
        rm -rf "$SKILLS_DIR/$old_skill"
        write_success "Removed legacy $old_skill skill"
    fi
done

# --- CLAUDE.md ---
CLAUDE_MD_PATH="$HOME/.claude/CLAUDE.md"
CC_MARKER="# CC Configuration"
CC_CONFIG_PATH="$SCRIPT_DIR/templates/cc-global-prompt.md"

if [ ! -f "$CC_CONFIG_PATH" ]; then
    write_warning "CC global prompt template not found at $CC_CONFIG_PATH"
elif [ ! -f "$CLAUDE_MD_PATH" ]; then
    cp "$CC_CONFIG_PATH" "$CLAUDE_MD_PATH"
    write_success "Created global CLAUDE.md"
elif grep -qF "$CC_MARKER" "$CLAUDE_MD_PATH"; then
    write_success "CC configuration already in CLAUDE.md"
else
    echo "" >> "$CLAUDE_MD_PATH"
    cat "$CC_CONFIG_PATH" >> "$CLAUDE_MD_PATH"
    write_success "Appended CC configuration to CLAUDE.md"
fi

# ==============================================================================
# Done!
# ==============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
write_success "CC setup completed successfully!"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Codex uses its own CLI auth (codex login / OPENAI_API_KEY / ~/.codex/config.toml)."
echo "No local config file is needed."
echo ""
echo "Next steps:"
echo "  1. Make sure Codex is logged in:  codex login"
echo "  2. Restart Claude Code CLI"
echo "  3. Verify MCP server: claude mcp list"
echo "  4. Check the skill: /cc-review"
echo ""
