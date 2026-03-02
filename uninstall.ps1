# CCG Uninstall Script for Windows
# This script removes Coder-Codex-Gemini MCP server and its configuration

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

# ==============================================================================
# Step 1: Remove MCP server registration
# ==============================================================================
Write-Step "Step 1: Removing MCP server registration..."

# Temporarily relax error handling for native commands in Step 1
$oldErrorActionPreference = $ErrorActionPreference
$oldNativeCommandEap = $null
$ErrorActionPreference = "Continue"
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $oldNativeCommandEap = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}

try {
    $claudeInstalled = $false
    try {
        $null = & claude @("--version") 2>&1
        $claudeInstalled = $true
    } catch {
        # claude not found
    }

    if ($claudeInstalled) {
        $null = & claude @("mcp","remove","ccg","--scope","user") 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "MCP server 'ccg' removed"
        } else {
            Write-WarningMsg "MCP server 'ccg' was not registered or removal failed"
        }
    } else {
        Write-WarningMsg "claude CLI not found, skipping MCP server removal"
    }
} finally {
    $ErrorActionPreference = $oldErrorActionPreference
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $PSNativeCommandUseErrorActionPreference = $oldNativeCommandEap
    }
}

# ==============================================================================
# Step 2: Remove Skills
# ==============================================================================
Write-Step "Step 2: Removing Skills..."

$skillsDir = "$env:USERPROFILE\.claude\skills"
$ccgWorkflow = "$skillsDir\ccg-workflow"
$geminiCollab = "$skillsDir\gemini-collaboration"

if (Test-Path $ccgWorkflow) {
    Remove-Item -Recurse -Force $ccgWorkflow
    Write-Success "Removed ccg-workflow skill"
} else {
    Write-WarningMsg "ccg-workflow skill not found, skipping"
}

if (Test-Path $geminiCollab) {
    Remove-Item -Recurse -Force $geminiCollab
    Write-Success "Removed gemini-collaboration skill"
} else {
    Write-WarningMsg "gemini-collaboration skill not found, skipping"
}

# ==============================================================================
# Step 3: Remove CCG config from global CLAUDE.md
# ==============================================================================
Write-Step "Step 3: Removing CCG configuration from global CLAUDE.md..."

$claudeMdPath = "$env:USERPROFILE\.claude\CLAUDE.md"
$ccgMarker = "# CCG Configuration"

if (Test-Path $claudeMdPath) {
    try {
        $content = Get-Content $claudeMdPath -Raw -Encoding UTF8

        # Check if CCG marker exists
        if ($content -match [regex]::Escape($ccgMarker)) {
            $lines = Get-Content $claudeMdPath -Encoding UTF8
            $firstLine = $lines[0]

            if ($firstLine -eq $ccgMarker) {
                # Delete the entire file
                Remove-Item $claudeMdPath
                Write-Success "Removed global CLAUDE.md (contained only CCG configuration)"
            } else {
                # Remove from marker line to end of file
                $newContent = ""
                $markerFound = $false

                foreach ($line in $lines) {
                    if (-not $markerFound) {
                        if ($line -eq $ccgMarker) {
                            $markerFound = $true
                            break
                        }
                        $newContent += $line + "`r`n"
                    }
                }

                # Remove trailing newline
                if ($newContent.Length -gt 0) {
                    $newContent = $newContent.TrimEnd("`r`n")
                }

                if ([string]::IsNullOrWhiteSpace($newContent)) {
                    # File is empty after removal, delete it
                    Remove-Item $claudeMdPath
                    Write-Success "Removed global CLAUDE.md (now empty after removing CCG configuration)"
                } else {
                    # Write the modified content back
                    [System.IO.File]::WriteAllText($claudeMdPath, $newContent, [System.Text.UTF8Encoding]::new($false))
                    Write-Success "Removed CCG configuration from global CLAUDE.md"
                }
            }
        } else {
            Write-WarningMsg "CCG configuration marker not found in CLAUDE.md, skipping"
        }
    } catch {
        Write-ErrorMsg "Failed to modify CLAUDE.md: $_"
    }
} else {
    Write-WarningMsg "Global CLAUDE.md not found, skipping"
}

# ==============================================================================
# Step 4: Remove config directory
# ==============================================================================
Write-Step "Step 4: Removing CCG configuration directory..."

$configDir = "$env:USERPROFILE\.ccg-mcp"

if (Test-Path $configDir) {
    Write-Host ""
    Write-Host "WARNING: This will delete your CCG configuration directory:" -ForegroundColor Yellow
    Write-Host "  $configDir" -ForegroundColor Yellow
    Write-Host "This contains your API token and other settings." -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure you want to delete it? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Remove-Item -Recurse -Force $configDir
        Write-Success "Removed CCG configuration directory"
    } else {
        Write-WarningMsg "Skipped removing CCG configuration directory"
    }
} else {
    Write-WarningMsg "CCG configuration directory not found, skipping"
}

# ==============================================================================
# Step 5: Clean uv cache
# ==============================================================================
Write-Step "Step 5: Cleaning uv cache..."

$uvInstalled = $false
try {
    $null = uv --version 2>&1
    $uvInstalled = $true
} catch {}

if ($uvInstalled) {
    try {
        $null = & uv @("cache","clean","ccg-mcp") 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Cleaned uv cache for ccg-mcp"
        } else {
            Write-WarningMsg "Failed to clean uv cache (non-critical)"
        }
    } catch {
        Write-WarningMsg "Failed to clean uv cache (non-critical)"
    }
} else {
    Write-WarningMsg "uv not found, skipping cache cleanup"
}

# ==============================================================================
# Done!
# ==============================================================================
Write-Host "`n============================================================" -ForegroundColor Green
Write-Success "CCG uninstall completed!"
Write-Host "============================================================`n" -ForegroundColor Green

Write-Host "Note: uv and claude CLI were left installed." -ForegroundColor Cyan
Write-Host "To remove them manually:" -ForegroundColor Cyan
Write-Host "  - uv: See https://github.com/astral-sh/uv" -ForegroundColor White
Write-Host "  - claude CLI: npm uninstall -g @anthropic-ai/claude-code" -ForegroundColor White
Write-Host ""
