#!/bin/bash
# 一键清理内存 (drop_caches) v1.2
# 支持 Linux drop_caches / macOS purge
# Usage: bash cleanup.sh [--level 1|2|3] [--threshold <pct>] [--dry-run] [--json]

set -euo pipefail

# ============================================================
# 参数解析
# ============================================================
LEVEL=3
THRESHOLD=0
DRY_RUN=false
JSON=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --level)    LEVEL="$2"; shift 2 ;;
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --json)     JSON=true; shift ;;
    -h|--help)
      echo "Usage: cleanup.sh [--level 1|2|3] [--threshold <pct>] [--dry-run] [--json]"
      echo "  --level     清理级别: 1=page cache, 2=dentries+inodes, 3=全部(默认)"
      echo "  --threshold 内存使用率低于此值时跳过清理 (0-100)"
      echo "  --dry-run   仅显示状态，不执行清理"
      echo "  --json      JSON 格式输出"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

OS=$(uname -s)
VERSION="1.2.0"

# ============================================================
# 权限预检
# ============================================================
check_privileges() {
  if [[ "$OS" == "Linux" ]]; then
    if [[ "$EUID" -ne 0 ]] && ! command -v sudo &>/dev/null; then
      if $JSON; then
        echo '{"error":"需要 root 或 sudo 权限","ok":false}'
      else
        echo "❌ 需要 root 或 sudo 权限才能执行 drop_caches"
      fi
      exit 1
    fi
  fi
}

# ============================================================
# 内存信息
# ============================================================
get_mem_info_linux() {
  # total used available free (MB)
  free -m | awk '/^Mem:/ {printf "%d %d %d %d", $2, $3, $7, $4}'
}

get_mem_pct_linux() {
  free -m | awk '/^Mem:/ {if($2>0) printf "%d", ($2-$7)*100/$2; else print 0}'
}

get_mem_info_macos() {
  local total_bytes page_size free_pages speculative_pages
  total_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  page_size=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096)
  free_pages=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
  speculative_pages=$(vm_stat 2>/dev/null | awk '/Pages speculative/ {gsub(/\./,"",$3); print $3}')
  free_pages=${free_pages:-0}
  speculative_pages=${speculative_pages:-0}
  local total_mb=$((total_bytes / 1024 / 1024))
  local avail_mb=$(( (free_pages + speculative_pages) * page_size / 1024 / 1024 ))
  local used_mb=$((total_mb - avail_mb))
  local free_mb=$avail_mb
  printf "%d %d %d %d" "$total_mb" "$used_mb" "$avail_mb" "$free_mb"
}

get_mem_pct_macos() {
  local total_bytes page_size free_pages speculative_pages
  total_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  page_size=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096)
  free_pages=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,"",$3); print $3}')
  speculative_pages=$(vm_stat 2>/dev/null | awk '/Pages speculative/ {gsub(/\./,"",$3); print $3}')
  free_pages=${free_pages:-0}
  speculative_pages=${speculative_pages:-0}
  local total_mb=$((total_bytes / 1024 / 1024))
  local avail_mb=$(( (free_pages + speculative_pages) * page_size / 1024 / 1024 ))
  if (( total_mb > 0 )); then
    echo $(( (total_mb - avail_mb) * 100 / total_mb ))
  else
    echo 0
  fi
}

get_mem_info() {
  if [[ "$OS" == "Linux" ]]; then
    get_mem_info_linux
  else
    get_mem_info_macos
  fi
}

get_mem_pct() {
  if [[ "$OS" == "Linux" ]]; then
    get_mem_pct_linux
  else
    get_mem_pct_macos
  fi
}

# ============================================================
# 输出函数
# ============================================================
print_status() {
  local label="$1" total="$2" used="$3" avail="$4" free="$5"
  if $JSON; then
    return  # JSON 模式最后统一输出
  fi
  echo "📊 ${label}："
  echo "   总量: ${total}MB | 已用: ${used}MB | 可用: ${avail}MB | 空闲: ${free}MB"
}

# ============================================================
# 主流程
# ============================================================

# 权限预检
check_privileges

# 清理前状态
read -r total_before used_before avail_before free_before <<< $(get_mem_info)
mem_pct_before=$(get_mem_pct)

# 阈值检查
if (( THRESHOLD > 0 )) && (( mem_pct_before < THRESHOLD )); then
  msg="内存使用率 ${mem_pct_before}% 低于阈值 ${THRESHOLD}%，无需清理"
  if $JSON; then
    echo "{\"skipped\":true,\"reason\":\"below_threshold\",\"used_pct\":$mem_pct_before,\"threshold\":$THRESHOLD,\"ok\":true}"
  else
    echo "⚡ Drop Caches Cleanup v${VERSION}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "ℹ️  ${msg}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  fi
  exit 0
fi

if ! $JSON; then
  echo "⚡ Drop Caches Cleanup v${VERSION}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🖥️  平台: $OS | 清理级别: level $LEVEL"
  print_status "清理前" "$total_before" "$used_before" "$avail_before" "$free_before"
fi

# Dry-run 模式
if $DRY_RUN; then
  if $JSON; then
    echo "{\"dry_run\":true,\"before\":{\"total\":$total_before,\"used\":$used_before,\"available\":$avail_before,\"free\":$free_before},\"used_pct\":$mem_pct_before,\"ok\":true}"
  else
    echo ""
    echo "🔍 Dry-run 模式，不执行清理"
    echo "   当前内存使用率: ${mem_pct_before}%"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  fi
  exit 0
fi

# 执行清理
if [[ "$OS" == "Linux" ]]; then
  if ! $JSON; then echo ""; echo "🧹 正在清理 (level $LEVEL)..."; fi
  sync
  if [[ "$EUID" -eq 0 ]]; then
    echo "$LEVEL" > /proc/sys/vm/drop_caches
  else
    echo "$LEVEL" | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
  fi
elif [[ "$OS" == "Darwin" ]]; then
  if ! $JSON; then echo ""; echo "🧹 正在清理 (macOS purge)..."; fi
  if command -v purge &>/dev/null; then
    if [[ "$EUID" -eq 0 ]]; then
      purge
    else
      sudo purge 2>/dev/null || purge
    fi
  else
    if $JSON; then
      echo '{"error":"purge 命令不可用，请安装 Xcode CLI tools: xcode-select --install","ok":false}'
    else
      echo "❌ purge 命令不可用，请安装: xcode-select --install"
    fi
    exit 1
  fi
else
  if $JSON; then
    echo "{\"error\":\"不支持的平台: $OS\",\"ok\":false}"
  else
    echo "❌ 不支持的平台: $OS"
  fi
  exit 1
fi

# 等待系统更新
sleep 1

# 清理后状态
read -r total_after used_after avail_after free_after <<< $(get_mem_info)
mem_pct_after=$(get_mem_pct)

if ! $JSON; then
  echo ""
  print_status "清理后" "$total_after" "$used_after" "$avail_after" "$free_after"
fi

# 计算释放量（用 available 差值，更准确）
freed_avail=$((avail_after - avail_before))

# 评估结果
assessment="ok"
if (( mem_pct_after >= 90 )); then
  assessment="critical"
elif (( mem_pct_after >= 70 )); then
  assessment="warning"
fi

if $JSON; then
  cat <<EOF
{"before":{"total":$total_before,"used":$used_before,"available":$avail_before,"free":$free_before},"after":{"total":$total_after,"used":$used_after,"available":$avail_after,"free":$free_after},"freed_mb":$freed_avail,"used_pct_before":$mem_pct_before,"used_pct_after":$mem_pct_after,"assessment":"$assessment","ok":true}
EOF
else
  echo ""
  if (( freed_avail > 0 )); then
    echo "🎉 成功释放 ${freed_avail}MB 可用内存！"
  elif (( freed_avail < 0 )); then
    echo "ℹ️  内存使用略有增加（系统活动），总体正常"
  else
    echo "ℹ️  内存已是最优状态，无额外释放"
  fi

  # 评估
  if [[ "$assessment" == "critical" ]]; then
    echo "🔴 内存使用率仍高达 ${mem_pct_after}%，建议扩容或检查内存泄漏"
  elif [[ "$assessment" == "warning" ]]; then
    echo "⚠️  内存使用率 ${mem_pct_after}%，仍偏高"
  else
    echo "✅ 内存状态良好 (${mem_pct_after}%)"
  fi

  echo ""
  echo "💡 如需定时清理，可配置 cron："
  echo "   0 */6 * * * /path/to/cleanup.sh --threshold 70"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
