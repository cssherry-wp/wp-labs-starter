# Transform change-review-findings.json into a GitHub "create review" request body.
# Args: --arg commit_id <reviewed head sha>   --arg marker "<!-- claude-autofix -->"
# Output: { commit_id, event:"COMMENT", comments:[...], body } for
#   gh api -X POST /repos/{owner}/{repo}/pulls/{n}/reviews --input -
# Only findings[] (line-anchored) become inline comments; unanchored[] + an
# auto-fixed digest go into the review body. Fixed findings carry the marker.

# A finding's human text is assembled from the change-review vocabulary:
# a bold `summary` headline, then `detail`, then a `suggestion` line. Older
# payloads used a single `body` field; fall back to it so both shapes render.
def finding_text:
  ( [ (if (.summary // "") != "" then "**\(.summary)**" else empty end),
      (if (.detail // "") != "" then .detail else empty end),
      (if (.suggestion // "") != "" then "_Suggestion:_ \(.suggestion)" else empty end) ]
    | join("\n\n") ) as $assembled
  | if $assembled != "" then $assembled else (.body // "") end;

# One-line headline for digests/lists: the summary, else the first line of body.
def headline:
  if (.summary // "") != "" then .summary else ((.body // "") | split("\n")[0]) end;

def confidence_line: "\n\n_(confidence \(.confidence))_";

# change-review's decision record: the fields a reader needs to decide whether
# to act on a finding, beyond what it is. All optional; render whichever are
# present, in the skill's canonical order, as a labelled list. Array fields
# (alternatives, interacts_with) become nested bullets / a comma list.
# Multi-line values (reproduced command output in `evidence`, typically) are
# indented so they stay inside the bullet instead of breaking the list.
def labelled($label; $value):
  if ($value // "") != ""
  then "- **\($label):** \($value | gsub("\n"; "\n  "))"
  else empty end;

def decision_block:
  ( [ labelled("Scenario"; .scenario),
      labelled("Trigger"; .trigger),
      labelled("Evidence"; .evidence),
      labelled("Origin"; .origin),
      (if ((.alternatives // []) | length) > 0
       then "- **Alternatives:**\n" + ((.alternatives) | map("  - " + .) | join("\n"))
       else empty end),
      labelled("Cost & risk of fixing"; .fix_risk),
      labelled("Caveats"; .caveats),
      (if ((.interacts_with // []) | length) > 0
       then "- **Interacts with:** " + ((.interacts_with) | join(", "))
       else empty end),
      labelled("Recommendation"; .recommendation) ]
    | join("\n") ) as $block
  | if $block != "" then "\n\n" + $block else "" end;

def comment_body:
  finding_text + decision_block + confidence_line
  + (if .status == "fixed"
     then "\n\n_Auto-fixed in the `[autofix]` commit._\n\n" + $marker
     else "" end);

def inline_comment:
  { path: .path, line: .line, side: (.side // "RIGHT"), body: comment_body }
  + (if .start_line != null
     then { start_line: .start_line, start_side: (.side // "RIGHT") }
     else {} end);

def fixed_list:
  [ (.findings // [])[] | select(.status == "fixed")
    | "- `\(.path):\(.line)` — \(headline)" ];

def unanchored_list:
  [ (.unanchored // [])[]
    | "- \(headline) _(confidence \(.confidence))_"
      + (if (.category // "") != "" then " — _\(.category)_" else "" end)
      # Unanchored items are a digest, so only the recommendation rides along
      # inline; the full record is in report_markdown above.
      + (if (.recommendation // "") != "" then " — _\(.recommendation)_" else "" end) ];

{
  commit_id: $commit_id,
  event: "COMMENT",
  comments: [ (.findings // [])[] | inline_comment ],
  body: (
    ( [ ((.report_markdown | select(. != "")) // .summary // ""),
        (if (fixed_list | length) > 0
         then "## Auto-fixed (\(fixed_list | length))\n" + (fixed_list | join("\n"))
         else "" end),
        (if (unanchored_list | length) > 0
         then "## Other findings (not line-anchored)\n" + (unanchored_list | join("\n"))
         else "" end) ]
      | map(select(. != "")) | join("\n\n") )
    + "\n\n" + $marker
  )
}
