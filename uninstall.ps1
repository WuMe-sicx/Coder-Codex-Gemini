# CC Uninstall Script for Windows
# Removes the cc MCP server, the cc-review skill, and any legacy layout.

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
# Step 1: Remove MCP server registration (current "cc" and legacy "ccg")
# ==============================================================================
Write-Step "Step 1: Removing MCP server registration..."

$settingsPath = "$env:USERPROFILE\.claude\settings.json"

if (!(Test-Path $settingsPath)) {
    Write-WarningMsg "MCP server was not registered"
} else {
    try {
        $raw = Get-Content $settingsPath -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) {
            Write-WarningMsg "MCP server was not registered"
        } else {
            $settings = $raw | ConvertFrom-Json
            $removed = @()

            if ($settings.PSObject.Properties.Name -contains "mcpServers") {
                foreach ($name in @("cc", "ccg")) {
                    if ($settings.mcpServers.PSObject.Properties.Name -contains $name) {
                        $settings.mcpServers.PSObject.Properties.Remove($name)
                        $removed += $name
                    }
                }
                if ($settings.mcpServers.PSObject.Properties.Count -eq 0) {
                    $settings.PSObject.Properties.Remove('mcpServers')
                }
            }

            if ($removed.Count -eq 0) {
                Write-WarningMsg "MCP server 'cc' was not registered"
            } else {
                $jsonOutput = $settings | ConvertTo-Json -Depth 10
                [System.IO.File]::WriteAllText($settingsPath, $jsonOutput, [System.Text.UTF8Encoding]::new($false))
                Write-Success ("MCP server(s) removed: " + ($removed -join ", "))
            }
        }
    } catch {
        Write-WarningMsg "settings.json is corrupt, skipping MCP removal"
    }
}

# ==============================================================================
# Step 2: Remove Skills (current cc-review + legacy skills)
# ==============================================================================
Write-Step "Step 2: Removing Skills..."

$skillsDir = "$env:USERPROFILE\.claude\skills"

foreach ($skill in @("cc-review", "codex-review", "ccg-workflow", "gemini-collaboration")) {
    $path = "$skillsDir\$skill"
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
        Write-Success "Removed $skill skill"
    } else {
        Write-WarningMsg "$skill skill not found, skipping"
    }
}

# ==============================================================================
# Step 3: Remove CC config from global CLAUDE.md (new + legacy marker)
# ==============================================================================
Write-Step "Step 3: Removing CC configuration from global CLAUDE.md..."

$claudeMdPath = "$env:USERPROFILE\.claude\CLAUDE.md"

function Remove-Marker {
    param([string]$Marker)

    $content = Get-Content $claudeMdPath -Raw -Encoding UTF8
    if (-not ($content -match [regex]::Escape($Marker))) {
        return $false
    }

    $lines = Get-Content $claudeMdPath -Encoding UTF8
    if ($lines[0] -eq $Marker) {
        Remove-Item $claudeMdPath
        Write-Success "Removed global CLAUDE.md (contained only CC configuration)"
        return $true
    }

    $newContent = ""
    foreach ($line in $lines) {
        if ($line -eq $Marker) { break }
        $newContent += $line + "`r`n"
    }
    $newContent = $newContent.TrimEnd("`r`n")

    if ([string]::IsNullOrWhiteSpace($newContent)) {
        Remove-Item $claudeMdPath
        Write-Success "Removed global CLAUDE.md (empty after removal)"
    } else {
        [System.IO.File]::WriteAllText($claudeMdPath, $newContent, [System.Text.UTF8Encoding]::new($false))
        Write-Success "Removed CC configuration from global CLAUDE.md"
    }
    return $true
}

if (Test-Path $claudeMdPath) {
    try {
        if (-not (Remove-Marker "# CC Configuration") -and -not (Remove-Marker "# CCG Configuration")) {
            Write-WarningMsg "CC configuration marker not found in CLAUDE.md, skipping"
        }
    } catch {
        Write-ErrorMsg "Failed to modify CLAUDE.md: $_"
    }
} else {
    Write-WarningMsg "Global CLAUDE.md not found, skipping"
}

# ==============================================================================
# Step 4: Remove legacy config directory (old 4-model layout)
# ==============================================================================
Write-Step "Step 4: Removing legacy configuration directory..."

$configDir = "$env:USERPROFILE\.ccg-mcp"

if (Test-Path $configDir) {
    Write-Host ""
    Write-Host "WARNING: This will delete the legacy configuration directory:" -ForegroundColor Yellow
    Write-Host "  $configDir" -ForegroundColor Yellow
    Write-Host "It may contain an old API token." -ForegroundColor Yellow
    $confirm = Read-Host "Delete it? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Remove-Item -Recurse -Force $configDir
        Write-Success "Removed legacy configuration directory"
    } else {
        Write-WarningMsg "Skipped removing legacy configuration directory"
    }
} else {
    Write-WarningMsg "No legacy configuration directory found, skipping"
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
        $null = & uv @("cache","clean","cc-mcp") 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Cleaned uv cache for cc-mcp"
        } else {
            Write-WarningMsg "Failed to clean uv cache (non-critical)"
        }
        $null = & uv @("cache","clean","ccg-mcp") 2>&1
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
Write-Success "CC uninstall completed!"
Write-Host "============================================================`n" -ForegroundColor Green

Write-Host "Note: uv, claude CLI and codex CLI were left installed." -ForegroundColor Cyan
Write-Host ""
