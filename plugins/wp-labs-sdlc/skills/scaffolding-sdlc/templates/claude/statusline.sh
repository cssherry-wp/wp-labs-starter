#!/usr/bin/env bash
# ~/.claude/statusline.sh
# Line 1: /full/path [branch] | ±N | N% bar (+$subagent, best-effort) | ponytail | model | sid8 | cfg | sdlc vX.Y.Z [(installed vN)]
# Line 2: "first user msg" → "last user msg"  (if transcript available)
# SDLC_SOURCE_VERSION must match plugins/wp-labs-sdlc/.claude-plugin/plugin.json's
# "version" at the time this file was last generated/copied from that template.
SDLC_SOURCE_VERSION="0.19.8"
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

# Config dir (needed below to locate the installed PRICING table)
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

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

import re, glob

# (input, output, cache_write, cache_read) $/MTok — pulled from the repo's
# own summarize_ai_usage.py PRICING table (installed plugin cache) so this
# stays in sync with it; falls back to its "_default" row if not found.
PRICING = {'_default': (3.0, 15.0, 3.75, 0.3)}
try:
    src = glob.glob(sys.argv[2] + '/plugins/cache/*/wp-labs-sdlc/*/skills/summarize-ai-usage/scripts/summarize_ai_usage.py')
    if src:
        text = open(sorted(src)[-1]).read()
        block = re.search(r'PRICING:.*?=\s*\{(.*?)\n\}', text, re.S).group(1)
        for k, a, b, c, d_ in re.findall(r'"([^"]+)":\s*\(([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\)', block):
            PRICING[k] = (float(a), float(b), float(c), float(d_))
except Exception:
    pass

def blended_rate(key):
    inp, out, _, _ = PRICING[key]
    return (inp + out) / 2  # no input/output split available per subagent, so approximate

first_msg = ''; last_msg = ''; subagent_cost = 0.0; subagent_unknown_tok = 0
agent_model = {}
try:
    with open(sys.argv[1]) as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                d = None
            if isinstance(d, dict):
                tur = d.get('toolUseResult')
                if isinstance(tur, dict) and tur.get('agentId') and tur.get('resolvedModel'):
                    agent_model[tur['agentId']] = tur['resolvedModel']
                msg = d.get('message') or d
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    s = txt(msg.get('content', '')).split('\n')[0][:120]
                    if s and not s.startswith('<'):
                        if not first_msg: first_msg = s
                        last_msg = s
            for tid, tok in re.findall(r'<task-id>([\w-]+)</task-id>.*?<subagent_tokens>(\d+)</subagent_tokens>', line, re.S):
                model = agent_model.get(tid)
                key = next((k for k in PRICING if k != '_default' and k in (model or '')), None)
                if key:
                    subagent_cost += int(tok) / 1_000_000 * blended_rate(key)
                else:
                    subagent_unknown_tok += int(tok)  # unrecognized model — show as tokens, not $
except Exception: pass
print(first_msg)
print(last_msg)
print(f'{subagent_cost:.4f}')
print(subagent_unknown_tok)
PY
  _td=$(python3 "$_py" "$transcript_path" "$cfg" 2>/dev/null) || true
  rm -f "$_py"
  first_msg=$(echo "${_td:-}" | awk 'NR==1')
  last_msg=$(echo "${_td:-}"  | awk 'NR==2')
  subagent_cost=$(echo "${_td:-}" | awk 'NR==3')
  subagent_unknown_tok=$(echo "${_td:-}" | awk 'NR==4')
fi
subagent_cost=${subagent_cost:-0}
subagent_unknown_tok=${subagent_unknown_tok:-0}

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

# Best-effort subagent $ cost, converted from tokens using this repo's own
# summarize_ai_usage.py PRICING table (not an official Claude Code API —
# derived from <subagent_tokens> tags in transcript task-notification text).
# Tokens from a model PRICING doesn't recognize (e.g. a free model) are
# shown as a raw token count instead of guessing a paid rate for them.
subagent_str=''
awk "BEGIN{exit !($subagent_cost > 0)}" && subagent_str="+\$$(printf '%.2f' "$subagent_cost")"
if [[ "${subagent_unknown_tok:-0}" -gt 0 ]]; then
  if   (( subagent_unknown_tok >= 1000000 )); then unk_str="+$(( subagent_unknown_tok / 1000000 )).$(( (subagent_unknown_tok / 100000) % 10 ))Mtok"
  elif (( subagent_unknown_tok >= 1000 ));    then unk_str="+$(( subagent_unknown_tok / 1000 )).$(( (subagent_unknown_tok / 100) % 10 ))ktok"
  else                                             unk_str="+${subagent_unknown_tok}tok"
  fi
  subagent_str="${subagent_str}${subagent_str:+ }${unk_str}"
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
