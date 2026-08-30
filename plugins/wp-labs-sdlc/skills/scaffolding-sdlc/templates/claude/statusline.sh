#!/usr/bin/env bash
# ~/.claude/statusline.sh
# Line 1: /full/path [branch] | ±N | N% bar (+subagent tok, best-effort) | ponytail | model | sid8 | cfg | sdlc vX.Y.Z [(installed vN)]
# Line 2: "first user msg" → "last user msg"  (if transcript available)
# SDLC_SOURCE_VERSION must match plugins/wp-labs-sdlc/.claude-plugin/plugin.json's
# "version" at the time this file was last generated/copied from that template.
SDLC_SOURCE_VERSION="0.19.4"
set -uo pipefail

R=$'\033[0m'   CY=$'\033[36m'  GR=$'\033[32m'
YL=$'\033[33m' RD=$'\033[31m'  DM=$'\033[38;5;245m'

# Parse stdin JSON from Claude Code statusLine hook
_raw=$(cat)
_parsed=$(echo "$_raw" | python3 -c "
import json, os, sys
try:
    d = json.load(sys.stdin)
    tp = d.get('transcript_path', '')
    sid = os.path.splitext(os.path.basename(tp))[0][:8] if tp else ''
    m = d.get('model', '')
    if isinstance(m, dict): m = m.get('id', '') or m.get('display_name', '')
    cw = d.get('context_window', {})
    pct = cw.get('used_percentage', 0) if isinstance(cw, dict) else 0
    cost = d.get('cost', {})
    usd = cost.get('total_cost_usd', 0) if isinstance(cost, dict) else 0
    ms  = int(cost.get('total_duration_ms', 0)) if isinstance(cost, dict) else 0
    s = ms // 1000
    if s < 60:      dur = f'{s}s'
    elif s < 3600:  dur = f'{s//60}m'
    elif s < 86400: h,r=divmod(s,3600); dur=f'{h}h{r//60}m' if r//60 else f'{h}h'
    else:           dv,r=divmod(s,86400); h=r//3600; dur=f'{dv}d{h}h' if h else f'{dv}d'
    print(m); print(tp); print(sid); print(pct)
    print(f'\${usd:.2f}'); print(dur)
except Exception:
    print(''); print(''); print(''); print(0); print(''); print('')
" 2>/dev/null || printf '\n\n\n0\n\n')
model=$(echo "$_parsed"           | awk 'NR==1')
transcript_path=$(echo "$_parsed" | awk 'NR==2')
session_id=$(echo "$_parsed"      | awk 'NR==3')
token_pct=$(echo "$_parsed"       | awk 'NR==4')
cost_str=$(echo "$_parsed"        | awk 'NR==5')
dur_str=$(echo "$_parsed"         | awk 'NR==6')
token_pct=${token_pct:-0}

# Read first/last user messages from transcript
first_msg=''; last_msg=''
if [[ -f "${transcript_path:-}" ]]; then
  _py=$(mktemp)
  cat > "$_py" << 'PY'
import json, sys

def txt(content):
    if isinstance(content, str): return content.strip()
    if isinstance(content, list):
        return ' '.join(b.get('text','') for b in content if b.get('type')=='text').strip()
    return ''

import re

first_msg = ''; last_msg = ''; subagent_tok = 0
try:
    with open(sys.argv[1]) as f:
        for line in f:
            for m in re.finditer(r'<subagent_tokens>(\d+)</subagent_tokens>', line):
                subagent_tok += int(m.group(1))
            try:
                d = json.loads(line)
                msg = d.get('message') or d
                if msg.get('role') == 'user':
                    s = txt(msg.get('content', '')).split('\n')[0][:120]
                    if s and not s.startswith('<'):
                        if not first_msg: first_msg = s
                        last_msg = s
            except Exception: pass
except Exception: pass
print(first_msg)
print(last_msg)
print(subagent_tok)
PY
  _td=$(python3 "$_py" "$transcript_path" 2>/dev/null) || true
  rm -f "$_py"
  first_msg=$(echo "${_td:-}" | awk 'NR==1')
  last_msg=$(echo "${_td:-}"  | awk 'NR==2')
  subagent_tok=$(echo "${_td:-}" | awk 'NR==3')
fi
subagent_tok=${subagent_tok:-0}

# Render 10-char token bar
bar_filled=$(( token_pct / 10 ))
bar_half=$(( (token_pct % 10) >= 5 ? 1 : 0 ))
bar_empty=$(( 10 - bar_filled - bar_half ))
bar=''
for (( i=0; i<bar_filled; i++ )); do bar+='█'; done
(( bar_half )) && bar+='▄' || true
for (( i=0; i<bar_empty; i++ )); do bar+='░'; done
if   (( token_pct >= 90 )); then bar_c=$RD
elif (( token_pct >= 70 )); then bar_c=$YL
else bar_c=$GR; fi

# Best-effort subagent token count, parsed from <subagent_tokens> tags in
# task-notification text embedded in the transcript (not an official API;
# no per-subagent-model pricing is available, so this stays a token count).
subagent_str=''
if [[ "${subagent_tok:-0}" -gt 0 ]]; then
  if   (( subagent_tok >= 1000000 )); then subagent_str="+$(( subagent_tok / 1000000 )).$(( (subagent_tok / 100000) % 10 ))Mtok"
  elif (( subagent_tok >= 1000 ));    then subagent_str="+$(( subagent_tok / 1000 )).$(( (subagent_tok / 100) % 10 ))ktok"
  else                                     subagent_str="+${subagent_tok}tok"
  fi
fi

# Git context
git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
branch=$(git branch --show-current 2>/dev/null || true)
sync=''
if [[ -n "$branch" ]]; then
  ah=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo 0)
  bh=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo 0)
  [[ "${ah:-0}" -gt 0 || "${bh:-0}" -gt 0 ]] && sync="+${ah:-0}-${bh:-0}"
  read -r _files _ins _del <<<"$(git diff --numstat HEAD 2>/dev/null | awk '{f++; i+=$1; d+=$2} END{print f+0, i+0, d+0}')"
  [[ "${_ins:-0}" -gt 0 || "${_del:-0}" -gt 0 ]] && sync+="${sync:+ }(~${_files:-0}f +${_ins:-0}/-${_del:-0}L)"
fi

# Ponytail mode
# Config dir
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

_pt=$(ls -d "$cfg"/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh 2>/dev/null | sort -V | tail -1 || true)
pt=$([[ -f "${_pt:-}" ]] && bash "$_pt" 2>/dev/null || true)

# wp-labs-sdlc plugin version (installed hooks/CLAUDE.md/dashboard come from this)
_sdlc_dir=$(ls -d "$cfg"/plugins/cache/*/wp-labs-sdlc/*/ 2>/dev/null | sort -V | tail -1 || true)
sdlc_ver=$(basename "${_sdlc_dir%/}" 2>/dev/null || true)

# --- Line 1 ---
out="${CY}${git_root:+${git_root/#$HOME/~}}${branch:+ [$branch]}${R}"
[[ -n "$sync" ]] && out+=" | ${YL}${sync}${R}"
out+=" | ${bar_c}${token_pct}% ${bar}${R}${cost_str:+ ${DM}${cost_str}${subagent_str:+ ${subagent_str}}${R}}${dur_str:+ ${DM}${dur_str}${R}}"
[[ -n "$pt" ]] && out+=" | ${YL}${pt}${R}"
out+=" | ${model:-${DM}(new)${R}}"
[[ -n "$session_id" ]] && out+=" | ${DM}${session_id}${R}"
out+=" | ${DM}${cfg/$HOME/~}${R}"
out+=" | ${DM}sdlc v${SDLC_SOURCE_VERSION}${R}"
[[ -n "$sdlc_ver" && "$sdlc_ver" != "$SDLC_SOURCE_VERSION" ]] && out+=" ${YL}(installed v${sdlc_ver})${R}"
echo "$out"

# --- Line 2: first → last user message, or hint when session has no messages yet ---
if [[ -n "$first_msg" || -n "$last_msg" ]]; then
  cols=$(tput cols 2>/dev/null || echo 120)
  if [[ "$first_msg" == "$last_msg" ]]; then
    msg_line="\"${first_msg}\""
  else
    half=$(( (cols - 6) / 2 ))
    f="${first_msg:0:$half}"; l="${last_msg:0:$half}"
    [[ "${#first_msg}" -gt $half ]] && f+='…'
    [[ "${#last_msg}"  -gt $half ]] && l+='…'
    msg_line="\"${f}\" → \"${l}\""
  fi
  echo "${DM}${msg_line}${R}"
else
  echo "${DM}(new session)${R}"
fi
