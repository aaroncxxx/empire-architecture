#!/usr/bin/env bash
# System Self-Check — OpenClaw / MiClaw / Hermes 通用
# Usage: bash selfcheck.sh [--brief] [--json] [--fix] [--platform <name>]

set -euo pipefail

# ============================================================
# 参数解析
# ============================================================
BRIEF=false
JSON=false
FIX=false
PLATFORM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brief)    BRIEF=true; shift ;;
    --json)     JSON=true; shift ;;
    --fix)      FIX=true; shift ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    *)          echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ============================================================
# 计数器
# ============================================================
PASS=0
WARN=0
FAIL=0

# ============================================================
# 工具函数
# ============================================================
result() {
  local status="$1" module="$2" detail="$3"
  case "$status" in
    pass) PASS=$((PASS + 1)) ;;
    warn) WARN=$((WARN + 1)) ;;
    fail) FAIL=$((FAIL + 1)) ;;
  esac
  if $BRIEF && [[ "$status" == "pass" ]]; then return; fi
  local icon
  case "$status" in
    pass) icon="✅" ;;
    warn) icon="⚠️" ;;
    fail) icon="❌" ;;
  esac
  if $JSON; then
    echo "{\"status\":\"$status\",\"module\":\"$module\",\"detail\":\"$detail\"}"
  else
    printf "  %-4s %-10s %s\n" "$icon" "[$module]" "$detail"
  fi
}

# ============================================================
# 平台检测
# ============================================================
detect_platform() {
  if [[ -n "$PLATFORM" ]]; then
    echo "$PLATFORM"
    return
  fi
  if command -v openclaw &>/dev/null; then
    echo "openclaw"
  elif command -v miclaw &>/dev/null; then
    echo "miclaw"
  elif command -v hermes &>/dev/null; then
    echo "hermes"
  else
    echo "unknown"
  fi
}

DETECTED_PLATFORM=$(detect_platform)
OS=$(uname -s)

# ============================================================
# 通用检查
# ============================================================

# --- System ---
check_system() {
  local kernel cpus arch hostname_str
  kernel=$(uname -r)
  cpus=$(nproc 2>/dev/null || echo "?")
  arch=$(uname -m)
  hostname_str=$(hostname -s 2>/dev/null || echo "?")
  result pass "System" "$OS $kernel | $cpus cores | $arch | $hostname_str"
}

# --- Memory ---
check_memory() {
  if [[ "$OS" == "Linux" ]]; then
    local total available pct
    total=$(free -m | awk '/Mem:/ {print $2}')
    available=$(free -m | awk '/Mem:/ {print $7}')
    pct=$((available * 100 / total))
    local detail="${total}M total / ${available}M available (${pct}%)"
    if (( pct <10 )); then
      result fail "Memory" "$detail — CRITICAL"
    elif (( pct <30 )); then
      result warn "Memory" "$detail — LOW"
    else
      result pass "Memory" "$detail"
    fi
  else
    # macOS: parse vm_stat for available memory
    local page_size free_pages active_pages speculative_pages total_bytes avail_bytes total_mb avail_mb pct
    page_size=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096)
    total_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    total_mb=$((total_bytes / 1024 / 1024))
    # vm_stat outputs pages; "Pages free" + "Pages speculative" ≈ available
    free_pages=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
    speculative_pages=$(vm_stat 2>/dev/null | awk '/Pages speculative/ {gsub(/\./,"",$3); print $3}')
    free_pages=${free_pages:-0}
    speculative_pages=${speculative_pages:-0}
    avail_bytes=$(( (free_pages + speculative_pages) * page_size ))
    avail_mb=$((avail_bytes / 1024 / 1024))
    if (( total_mb > 0 )); then
      pct=$((avail_mb * 100 / total_mb))
    else
      pct=100
    fi
    local detail="${total_mb}M total / ${avail_mb}M available (${pct}%)"
    if (( pct < 10 )); then
      result fail "Memory" "$detail — CRITICAL"
    elif (( pct < 30 )); then
      result warn "Memory" "$detail — LOW"
    else
      result pass "Memory" "$detail"
    fi
  fi
}

# --- Disk ---
check_disk() {
  local total used avail pct
  read -r total used avail pct <<< $(df -h / | awk 'NR==2 {print $2, $3, $4, $5}')
  local pct_num=${pct%\%}
  local detail="$total total / $avail available (${pct_num}% used)"
  if (( 100 - pct_num <10 )); then
    result fail "Disk" "$detail — CRITICAL"
  elif (( 100 - pct_num <30 )); then
    result warn "Disk" "$detail — LOW"
  else
    result pass "Disk" "$detail"
  fi
}

# --- Runtime ---
check_runtime() {
  local py_ver node_ver
  py_ver=$(python3 --version 2>&1 | awk '{print $2}')
  node_ver=$(node --version 2>&1 || echo "not found")
  result pass "Runtime" "Python $py_ver | Node $node_ver"
}

# --- Core Dependencies ---
check_deps() {
  local missing=""
  local found=""

  if command -v ffmpeg &>/dev/null; then
    local ff_ver=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    found+="ffmpeg $ff_ver | "
  else
    missing+="ffmpeg "
  fi

  if command -v jq &>/dev/null; then
    found+="jq ✅ | "
  else
    missing+="jq "
  fi

  if command -v curl &>/dev/null; then
    found+="curl ✅ | "
  else
    missing+="curl "
  fi

  if command -v git &>/dev/null; then
    found+="git ✅"
  else
    missing+="git"
  fi

  if [[ -n "$missing" ]]; then
    result fail "Deps" "${found} | MISSING: $missing"
  else
    result pass "Deps" "$found"
  fi
}

# --- Network ---
check_network() {
  local urls=("github.com" "api.xiaomimimo.com" "clawhub.ai")
  for url in "${urls[@]}"; do
    local code latency_s start_s end_s
    start_s=$(date +%s 2>/dev/null || echo 0)
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://$url" --connect-timeout 5 --max-time 10 2>/dev/null || true)
    code=$(echo "$code" | tr -d '[:space:]')
    code=${code:-000}
    end_s=$(date +%s 2>/dev/null || echo 0)
    latency_s=$(( end_s - start_s ))

    if [[ "$code" == "000" ]]; then
      result fail "Network" "$url — TIMEOUT"
    elif (( latency_s > 3 )); then
      result warn "Network" "$url — $code (${latency_s}s) SLOW"
    else
      result pass "Network" "$url — $code (${latency_s}s)"
    fi
  done
}


# --- OpenClaw ---
check_openclaw() {
  if command -v openclaw &>/dev/null; then
    local oc_ver=$(openclaw --version 2>&1 | head -1)
    # Check latest version from npm registry
    local latest_ver=""
    if command -v curl &>/dev/null; then
      latest_ver=$(curl -s --connect-timeout 5 --max-time 10 \
        "https://registry.npmjs.org/openclaw/latest" 2>/dev/null \
        | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    fi
    if [[ -n "$latest_ver" && "$oc_ver" != *"$latest_ver"* ]]; then
      result warn "Platform" "OpenClaw $oc_ver (latest: $latest_ver)"
    else
      result pass "Platform" "OpenClaw $oc_ver"
    fi

    # Gateway
    local gw_status=$(openclaw gateway status 2>&1 || echo "unknown")
    if echo "$gw_status" | grep -qi "running\|active\|ok"; then
      result pass "Gateway" "Running"
    else
      result warn "Gateway" "Status: $gw_status"
    fi

    # Config
    if [[ -f ~/.openclaw/openclaw.json ]]; then
      result pass "Config" "~/.openclaw/openclaw.json exists"
    else
      result fail "Config" "~/.openclaw/openclaw.json NOT FOUND"
    fi
  else
    result fail "Platform" "openclaw command not found"
  fi
}

# --- Skills ---
check_skills() {
  local skill_dir=""
  # Try to get skills dir from openclaw config
  if command -v openclaw &>/dev/null; then
    skill_dir=$(openclaw config get skills.dir 2>/dev/null || echo "")
  fi
  # Fallback to default
  if [[ -z "$skill_dir" ]]; then
    skill_dir="${HOME}/.openclaw/skills"
  fi
  # Handle relative path
  if [[ "$skill_dir" != /* ]]; then
    skill_dir="${HOME}/.openclaw/$skill_dir"
  fi
  if [[ -d "$skill_dir" ]]; then
    local count=$(ls -d "$skill_dir"/*/ 2>/dev/null | wc -l)
    result pass "Skills" "$count installed ($skill_dir)"
  else
    result warn "Skills" "Directory not found: $skill_dir"
  fi
}

# --- API Keys ---
check_api_keys() {
  local key_status=""

  if [[ -n "${MIMO_API_KEY:-}" ]]; then
    key_status+="MIMO_API_KEY ✅ | "
  else
    key_status+="MIMO_API_KEY ❌ | "
  fi

  # Check ClawHub token (in config or env)
  local clawhub_ok=false
  if [[ -n "${CLAWHUB_TOKEN:-}" ]]; then
    clawhub_ok=true
  elif [[ -f ~/.config/clawhub/config.json ]]; then
    clawhub_ok=true
  elif command -v npx &>/dev/null; then
    local whoami=$(timeout 10 npx clawhub@latest whoami 2>/dev/null || echo "")
    if [[ -n "$whoami" && "$whoami" != *"not logged"* ]]; then
      clawhub_ok=true
    fi
  fi

  if $clawhub_ok; then
    key_status+="ClawHub ✅"
  else
    key_status+="ClawHub ❌"
  fi

  # Check for any missing
  if [[ -z "${MIMO_API_KEY:-}" ]] || ! $clawhub_ok; then
    result warn "API Keys" "$key_status"
  else
    result pass "API Keys" "$key_status"
  fi
}

# ============================================================
# Platform-specific checks (placeholder)
# ============================================================
check_platform_specific() {
  case "$DETECTED_PLATFORM" in
    openclaw)
      check_openclaw
      check_skills
      check_api_keys
      ;;
    miclaw)
      result pass "Platform" "MiClaw detected (checks TODO)"
      ;;
    hermes)
      result pass "Platform" "Hermes detected (checks TODO)"
      ;;
    *)
      result warn "Platform" "Unknown — skipping platform checks"
      ;;
  esac
}

# ============================================================
# Auto-fix
# ============================================================
do_fix() {
  echo ""
  echo "🔧 Auto-fix mode"
  echo "━━━━━━━━━━━━━━━━"

  # Fix missing edge-tts
  if ! python3 -c "import edge_tts" 2>/dev/null; then
    echo "  Installing edge-tts..."
    pip3 install --break-system-packages edge-tts 2>/dev/null && echo "  ✅ edge-tts installed" || echo "  ❌ edge-tts install failed"
  fi

  # Fix missing jq
  if ! command -v jq &>/dev/null; then
    echo "  Installing jq..."
    apt-get install -y jq 2>/dev/null && echo "  ✅ jq installed" || echo "  ❌ jq install failed (apt may be unreachable)"
  fi

  echo ""
}

# ============================================================
# Main
# ============================================================

if ! $JSON; then
  echo ""
  echo "⚡ System Self-Check Report — ${DETECTED_PLATFORM^}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

check_system
check_memory
check_disk
check_runtime
check_deps
check_network
check_platform_specific

if $FIX; then
  do_fix
fi

if ! $JSON; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if $BRIEF && (( WARN == 0 )) && (( FAIL == 0 )); then
    echo "  All clear ✅"
  else
    echo "  Summary: $PASS passed | $WARN warnings | $FAIL failed"
  fi
  echo ""
fi

# Exit code: 0 = all clear, 1 = has failures, 2 = has warnings
if (( FAIL > 0 )); then exit 1; fi
if (( WARN > 0 )); then exit 2; fi
exit 0
