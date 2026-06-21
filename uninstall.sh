#!/bin/bash
# CC Uninstall Script for macOS/Linux
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

# Use Python to directly modify ~/.claude/settings.json.
# Also clean up the legacy "ccg" entry from the old 4-model layout.
python3 -c "
import json
import os

settings_path = os.path.expanduser('~/.claude/settings.json')

if not os.path.exists(settings_path):
    print('[WARN] MCP server was not registered')
    exit(0)

try:
    with open(settings_path, 'r') as f:
        content = f.read().strip()
        if not content:
            print('[WARN] MCP server was not registered')
            exit(0)
        settings = json.loads(content)
except (json.JSONDecodeError, ValueError):
    print('[WARN] settings.json is corrupt, skipping MCP removal')
    exit(0)

servers = settings.get('mcpServers', {})
removed = []
for name in ('cc', 'ccg'):
    if name in servers:
        del servers[name]
        removed.append(name)

if not removed:
    print('[WARN] MCP server \"cc\" was not registered')
    exit(0)

if not servers:
    del settings['mcpServers']

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

print('[OK] MCP server(s) removed: ' + ', '.join(removed))
" || write_warning "MCP server 'cc' was not registered"

# ==============================================================================
# Step 2: Remove Skills
# ==============================================================================
write_step "Step 2: Removing Skills..."

SKILLS_DIR="$HOME/.claude/skills"

# codex-review is the current skill; ccg-workflow / gemini-collaboration are legacy.
for skill in codex-review ccg-workflow gemini-collaboration; do
    if [ -d "$SKILLS_DIR/$skill" ]; then
        rm -rf "$SKILLS_DIR/$skill"
        write_success "Removed $skill skill"
    else
        write_warning "$skill skill not found, skipping"
    fi
done

# ==============================================================================
# Step 3: Remove CC config from global CLAUDE.md
# ==============================================================================
write_step "Step 3: Removing CC configuration from global CLAUDE.md..."

CLAUDE_MD_PATH="$HOME/.claude/CLAUDE.md"

# Support both the new "# CC Configuration" marker and the legacy "# CCG Configuration".
remove_marker() {
    local marker="$1"
    if grep -qF "$marker" "$CLAUDE_MD_PATH"; then
        first_line=$(head -n 1 "$CLAUDE_MD_PATH")
        if [ "$first_line" = "$marker" ]; then
            rm "$CLAUDE_MD_PATH"
            write_success "Removed global CLAUDE.md (contained only CC configuration)"
        else
            temp_file=$(mktemp)
            sed -e "/$marker/,\$d" "$CLAUDE_MD_PATH" > "$temp_file"
            if [ -s "$temp_file" ]; then
                mv "$temp_file" "$CLAUDE_MD_PATH"
                write_success "Removed CC configuration from global CLAUDE.md"
            else
                rm -f "$temp_file"
                rm "$CLAUDE_MD_PATH"
                write_success "Removed global CLAUDE.md (empty after removal)"
            fi
        fi
        return 0
    fi
    return 1
}

if [ -f "$CLAUDE_MD_PATH" ]; then
    if ! remove_marker "# CC Configuration" && ! remove_marker "# CCG Configuration"; then
        write_warning "CC configuration marker not found in CLAUDE.md, skipping"
    fi
else
    write_warning "Global CLAUDE.md not found, skipping"
fi

# ==============================================================================
# Step 4: Remove legacy config directory (old 4-model layout)
# ==============================================================================
write_step "Step 4: Removing legacy configuration directory..."

CONFIG_DIR="$HOME/.ccg-mcp"

if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}WARNING: This will delete the legacy configuration directory:${NC}"
    echo "  $CONFIG_DIR"
    echo -e "${YELLOW}It may contain an old API token.${NC}"
    read -p "Delete it? (y/N): " CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        rm -rf "$CONFIG_DIR"
        write_success "Removed legacy configuration directory"
    else
        write_warning "Skipped removing legacy configuration directory"
    fi
else
    write_warning "No legacy configuration directory found, skipping"
fi

# ==============================================================================
# Step 5: Clean uv cache
# ==============================================================================
write_step "Step 5: Cleaning uv cache..."

if command -v uv &> /dev/null; then
    uv cache clean cc-mcp 2>/dev/null && write_success "Cleaned uv cache for cc-mcp" || write_warning "Failed to clean uv cache (non-critical)"
    uv cache clean ccg-mcp 2>/dev/null || true
else
    write_warning "uv not found, skipping cache cleanup"
fi

# ==============================================================================
# Done!
# ==============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
write_success "CC uninstall completed!"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Note: uv, claude CLI and codex CLI were left installed."
echo ""
