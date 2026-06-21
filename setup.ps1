# CC One-Click Setup Script for Windows
# Claude + Codex 双模型协作 MCP 服务器

param(
    [switch]$WhatIf,
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host @"
CC One-Click Setup Script for Windows

Usage: .\setup.ps1 [-WhatIf] [-Help]

Options:
  -WhatIf    Dry-run mode. Show what would be done without making changes.
  -Help      Show this help message.

Examples:
  .\setup.ps1           # Run the setup
  .\setup.ps1 -WhatIf   # Preview what would be done
"@
    exit 0
}

$DryRun = $WhatIf.IsPresent

# Force UTF-8 encoding for file operations
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[*] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-DryRun {
    param([string]$Message)
    Write-Host "[DRY-RUN] $Message" -ForegroundColor Magenta
}

# ==============================================================================
# Dry-run mode banner
# ==============================================================================
if ($DryRun) {
    Write-Host "`n============================================================" -ForegroundColor Magenta
    Write-Host "  DRY-RUN MODE - No changes will be made" -ForegroundColor Magenta
    Write-Host "============================================================`n" -ForegroundColor Magenta
}

# ==============================================================================
# Step 1: Check dependencies
# ==============================================================================
Write-Step "Step 1: Checking dependencies..."

# Helper function to refresh PATH by merging registry PATH with current session PATH
function Refresh-PathFromRegistry {
    $registryPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $currentPath = $env:Path
    $currentPaths = $currentPath -split ';' | Where-Object { $_ -ne '' }
    $registryPaths = $registryPath -split ';' | Where-Object { $_ -ne '' }
    $newPaths = $registryPaths | Where-Object { $_ -notin $currentPaths }
    if ($newPaths) {
        $env:Path = $currentPath + ";" + ($newPaths -join ';')
    }
}

# Check uv
$uvInstalled = $false
try {
    $null = uv --version 2>&1
    $uvInstalled = $true
    Write-Success "uv is installed"
} catch {
    Refresh-PathFromRegistry
    try {
        $null = uv --version 2>&1
        $uvInstalled = $true
        Write-Success "uv is installed"
    } catch {
        if ($DryRun) {
            Write-WarningMsg "uv is not installed"
            Write-DryRun "Would install uv automatically"
        } else {
            Write-WarningMsg "uv is not installed, installing automatically..."
            try {
                powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
                Refresh-PathFromRegistry
                $null = uv --version 2>&1
                $uvInstalled = $true
                Write-Success "uv installed successfully"
            } catch {
                Write-ErrorMsg "Failed to install uv automatically"
                Write-Host "Please install uv manually: https://github.com/astral-sh/uv" -ForegroundColor Yellow
                exit 1
            }
        }
    }
}

# Check claude CLI
$claudeInstalled = $false
try {
    $null = claude --version 2>&1
    $claudeInstalled = $true
    Write-Success "claude CLI is installed"
} catch {
    Refresh-PathFromRegistry
    try {
        $null = claude --version 2>&1
        $claudeInstalled = $true
        Write-Success "claude CLI is installed"
    } catch {
        if ($DryRun) {
            Write-WarningMsg "claude CLI is not installed"
            Write-DryRun "Would require claude CLI to be installed before running"
        } else {
            Write-ErrorMsg "claude CLI is not installed"
            Write-Host "Please install Claude Code CLI first: https://docs.anthropic.com/en/docs/claude-code" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "If you have already installed claude CLI, please check:" -ForegroundColor Yellow
            Write-Host "  1. Restart your terminal to refresh PATH" -ForegroundColor White
            Write-Host "  2. Ensure claude is in your PATH: where.exe claude" -ForegroundColor White
            Write-Host "  3. For npm install: npm install -g @anthropic-ai/claude-code" -ForegroundColor White
            exit 1
        }
    }
}

# Check codex CLI (the only reviewer this server drives)
try {
    $null = codex --version 2>&1
    Write-Success "codex CLI is installed"
} catch {
    Refresh-PathFromRegistry
    try {
        $null = codex --version 2>&1
        Write-Success "codex CLI is installed"
    } catch {
        Write-WarningMsg "codex CLI is not installed"
        Write-Host "The cc server reviews code via the Codex CLI. Install and log in before use:" -ForegroundColor Yellow
        Write-Host "  https://developers.openai.com/codex/quickstart" -ForegroundColor White
        Write-Host "  codex login" -ForegroundColor White
    }
}

# ==============================================================================
# Step 2: Install project dependencies
# ==============================================================================
Write-Step "Step 2: Installing project dependencies..."

if ($DryRun) {
    Write-DryRun "Would run: uv sync"
    Write-Success "Project dependencies would be installed"
} else {
    uv sync
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to install dependencies"
        exit 1
    }
    Write-Success "Project dependencies installed"
}

# ==============================================================================
# Step 3: Generate MCP server configuration
# ==============================================================================
Write-Step "Step 3: Generating MCP server configuration..."

$projectDir = $PSScriptRoot

# Detect uvx path
$uvxPath = $null
try {
    $uvxPath = (Get-Command uvx -ErrorAction Stop).Source
} catch {
    Refresh-PathFromRegistry
    try {
        $uvxPath = (Get-Command uvx -ErrorAction Stop).Source
    } catch {}
}

if (-not $uvxPath) {
    Write-WarningMsg "uvx not found in PATH, using 'uvx' as command"
    $uvxPath = "uvx"
}

# Build MCP config JSON
$mcpConfig = [PSCustomObject]@{
    args = @("--from", "file:$projectDir", "cc-mcp")
    command = $uvxPath
    cwd = $projectDir
    type = "stdio"
}

$mcpJson = $mcpConfig | ConvertTo-Json -Depth 5

if ($DryRun) {
    Write-DryRun "Would generate MCP configuration"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MCP Server Configuration (add to settings.json manually)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Add the following to mcpServers.cc in:" -ForegroundColor Yellow
Write-Host "  $env:USERPROFILE\.claude\settings.json" -ForegroundColor White
Write-Host ""
Write-Host $mcpJson -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Success "MCP configuration generated"

# ==============================================================================
# Step 4: Install Skill
# ==============================================================================
Write-Step "Step 4: Installing Skill..."

$skillsDir = "$env:USERPROFILE\.claude\skills"
$ccReviewSource = Join-Path $PSScriptRoot "skills\cc-review"

if ($DryRun) {
    if (!(Test-Path $skillsDir)) {
        Write-DryRun "Would create directory: $skillsDir"
    }
    if (Test-Path $ccReviewSource) {
        Write-DryRun "Would copy: $ccReviewSource -> $skillsDir\cc-review"
        Write-Success "cc-review skill would be installed"
    } else {
        Write-WarningMsg "cc-review skill not found, would skip"
    }
} else {
    try {
        if (!(Test-Path $skillsDir)) {
            New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
            Write-Success "Created skills directory: $skillsDir"
        }

        if (Test-Path $ccReviewSource) {
            $dest = "$skillsDir\cc-review"
            if (Test-Path $dest) {
                Remove-Item -Recurse -Force $dest
            }
            Copy-Item -Recurse $ccReviewSource $dest
            Write-Success "Installed cc-review skill"
        } else {
            Write-WarningMsg "cc-review skill not found, skipping"
        }

        # Remove skills from earlier layouts if present (codex-review = pre-rename name)
        foreach ($oldSkill in @("codex-review", "ccg-workflow", "gemini-collaboration")) {
            $oldPath = "$skillsDir\$oldSkill"
            if (Test-Path $oldPath) {
                Remove-Item -Recurse -Force $oldPath
                Write-Success "Removed legacy $oldSkill skill"
            }
        }
    } catch {
        Write-ErrorMsg "Failed to install skill"
        exit 1
    }
}

# ==============================================================================
# Step 5: Configure global CLAUDE.md
# ==============================================================================
Write-Step "Step 5: Configuring global CLAUDE.md..."

$claudeMdPath = "$env:USERPROFILE\.claude\CLAUDE.md"
$ccMarker = "# CC Configuration"

# Read CC config from external file to avoid encoding issues
$ccConfigPath = Join-Path $PSScriptRoot "templates\cc-global-prompt.md"

if ($DryRun) {
    if (!(Test-Path $claudeMdPath)) {
        if (Test-Path $ccConfigPath) {
            Write-DryRun "Would create: $claudeMdPath (from template)"
            Write-Success "Global CLAUDE.md would be created"
        } else {
            Write-WarningMsg "CC global prompt template not found at $ccConfigPath"
        }
    } else {
        $content = Get-Content $claudeMdPath -Raw -Encoding UTF8
        if ($content -match [regex]::Escape($ccMarker)) {
            Write-WarningMsg "CC configuration already exists in CLAUDE.md, would skip"
        } else {
            if (Test-Path $ccConfigPath) {
                Write-DryRun "Would append CC configuration to: $claudeMdPath"
                Write-Success "CC configuration would be appended to CLAUDE.md"
            } else {
                Write-WarningMsg "CC global prompt template not found at $ccConfigPath"
            }
        }
    }
} else {
    try {
        if (!(Test-Path $claudeMdPath)) {
            if (Test-Path $ccConfigPath) {
                Copy-Item $ccConfigPath $claudeMdPath
                Write-Success "Created global CLAUDE.md"
            } else {
                Write-WarningMsg "CC global prompt template not found at $ccConfigPath"
                Write-WarningMsg "Please manually copy the CC configuration to $claudeMdPath"
            }
        } else {
            $content = Get-Content $claudeMdPath -Raw -Encoding UTF8
            if ($content -match [regex]::Escape($ccMarker)) {
                Write-WarningMsg "CC configuration already exists in CLAUDE.md, skipping"
            } else {
                if (Test-Path $ccConfigPath) {
                    $ccContent = Get-Content $ccConfigPath -Raw -Encoding UTF8
                    Add-Content -Path $claudeMdPath -Value "`n$ccContent" -Encoding UTF8
                    Write-Success "Appended CC configuration to CLAUDE.md"
                } else {
                    Write-WarningMsg "CC global prompt template not found at $ccConfigPath"
                    Write-WarningMsg "Please manually copy the CC configuration to $claudeMdPath"
                }
            }
        }
    } catch {
        Write-ErrorMsg "Failed to configure global CLAUDE.md: $_"
        exit 1
    }
}

# ==============================================================================
# Done!
# ==============================================================================
if ($DryRun) {
    Write-Host "`n============================================================" -ForegroundColor Magenta
    Write-Host "  DRY-RUN COMPLETED - No changes were made" -ForegroundColor Magenta
    Write-Host "============================================================`n" -ForegroundColor Magenta
    Write-Host "Run without -WhatIf to apply changes:" -ForegroundColor Cyan
    Write-Host "  .\setup.ps1" -ForegroundColor White
} else {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Success "CC setup completed successfully!"
    Write-Host "============================================================`n" -ForegroundColor Green

    Write-Host "Codex uses its own CLI auth (codex login / OPENAI_API_KEY / ~/.codex/config.toml)." -ForegroundColor Cyan
    Write-Host "No local config file is needed." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Make sure Codex is logged in: codex login" -ForegroundColor White
    Write-Host "  2. Restart Claude Code CLI" -ForegroundColor White
    Write-Host "  3. Verify MCP server: claude mcp list" -ForegroundColor White
    Write-Host "  4. Check the skill: /cc-review" -ForegroundColor White
}
Write-Host ""
