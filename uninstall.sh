#!/bin/bash
# CCG Uninstall Script for macOS/Linux
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
# Step 1: Remove MCP server registration
# ==============================================================================
write_step "Step 1: Removing MCP server registration..."

if command -v claude &> /dev/null; then
    if claude mcp remove ccg --scope user 2>/dev/null; then
        write_success "MCP server 'ccg' removed"
    else
        write_warning "MCP server 'ccg' was not registered or removal failed"
    fi
else
    write_warning "claude CLI not found, skipping MCP server removal"
fi

# ==============================================================================
# Step 2: Remove Skills
# ==============================================================================
write_step "Step 2: Removing Skills..."

SKILLS_DIR="$HOME/.claude/skills"
CCG_WORKFLOW="$SKILLS_DIR/ccg-workflow"
GEMINI_COLLAB="$SKILLS_DIR/gemini-collaboration"

if [ -d "$CCG_WORKFLOW" ]; then
    rm -rf "$CCG_WORKFLOW"
    write_success "Removed ccg-workflow skill"
else
    write_warning "ccg-workflow skill not found, skipping"
fi

if [ -d "$GEMINI_COLLAB" ]; then
    rm -rf "$GEMINI_COLLAB"
    write_success "Removed gemini-collaboration skill"
else
    write_warning "gemini-collaboration skill not found, skipping"
fi

# ==============================================================================
# Step 3: Remove CCG config from global CLAUDE.md
# ==============================================================================
write_step "Step 3: Removing CCG configuration from global CLAUDE.md..."

CLAUDE_MD_PATH="$HOME/.claude/CLAUDE.md"
CCG_MARKER="# CCG Configuration"

if [ -f "$CLAUDE_MD_PATH" ]; then
    # Check if CCG marker exists
    if grep -qF "$CCG_MARKER" "$CLAUDE_MD_PATH"; then
        # Check if file starts with the marker (CCG config is the only content)
        first_line=$(head -n 1 "$CLAUDE_MD_PATH")
        if [ "$first_line" = "$CCG_MARKER" ]; then
            # Delete the entire file
            rm "$CLAUDE_MD_PATH"
            write_success "Removed global CLAUDE.md (contained only CCG configuration)"
        else
            # Remove from marker line to end of file
            # Create temp file with content before the marker
            temp_file=$(mktemp)
            sed -e "/$CCG_MARKER/,\$d" "$CLAUDE_MD_PATH" > "$temp_file"
            # Remove trailing newline if file ends with one
            if [ -s "$temp_file" ]; then
                mv "$temp_file" "$CLAUDE_MD_PATH"
                write_success "Removed CCG configuration from global CLAUDE.md"
            else
                # If file is empty after removal, delete it
                rm -f "$temp_file"
                rm "$CLAUDE_MD_PATH"
                write_success "Removed global CLAUDE.md (now empty after removing CCG configuration)"
            fi
        fi
    else
        write_warning "CCG configuration marker not found in CLAUDE.md, skipping"
    fi
else
    write_warning "Global CLAUDE.md not found, skipping"
fi

# ==============================================================================
# Step 4: Remove config directory
# ==============================================================================
write_step "Step 4: Removing CCG configuration directory..."

CONFIG_DIR="$HOME/.ccg-mcp"

if [ -d "$CONFIG_DIR" ]; then
    # Ask for confirmation before deleting
    echo -e "${YELLOW}WARNING: This will delete your CCG configuration directory:${NC}"
    echo "  $CONFIG_DIR"
    echo -e "${YELLOW}This contains your API token and other settings.${NC}"
    read -p "Are you sure you want to delete it? (y/N): " CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        rm -rf "$CONFIG_DIR"
        write_success "Removed CCG configuration directory"
    else
        write_warning "Skipped removing CCG configuration directory"
    fi
else
    write_warning "CCG configuration directory not found, skipping"
fi

# ==============================================================================
# Step 5: Clean uv cache
# ==============================================================================
write_step "Step 5: Cleaning uv cache..."

if command -v uv &> /dev/null; then
    if uv cache clean ccg-mcp 2>/dev/null; then
        write_success "Cleaned uv cache for ccg-mcp"
    else
        write_warning "Failed to clean uv cache (non-critical)"
    fi
else
    write_warning "uv not found, skipping cache cleanup"
fi

# ==============================================================================
# Done!
# ==============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
write_success "CCG uninstall completed!"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Note: uv and claude CLI were left installed."
echo "To remove them manually:"
echo "  - uv: See https://github.com/astral-sh/uv"
echo "  - claude CLI: npm uninstall -g @anthropic-ai/claude-code"
echo ""
