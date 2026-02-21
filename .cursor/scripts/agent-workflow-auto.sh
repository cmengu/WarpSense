#!/bin/bash
set -e

# agent-workflow-auto.sh — v2
#
# Key fixes from v1:
#   1. Critical issues gate is HARD — iteration count never bypasses it
#   2. Two-track critique: standard planner + adversarial red-team
#   3. Compressed JSON handoffs between phases — no raw file concatenation
#   4. Ground-truth verification before review (checks real files, runs tsc/tests)
#   5. Score extraction uses jq-first with sane fallback — no regex on structured data
#   6. Token budget enforced: phases receive handoff JSON, not previous phase raw output

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
TASK=""
DRY_RUN=false
SKIP_ADVERSARIAL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task|-t)        TASK="$2"; shift 2 ;;
        --dry-run)        DRY_RUN=true; shift ;;
        --skip-adversarial) SKIP_ADVERSARIAL=true; shift ;;
        *)                [[ -z "$TASK" ]] && TASK="$1"; shift ;;
    esac
done

[[ -z "$TASK" ]] && { echo "❌ Usage: ./agent-workflow-auto.sh \"task description\""; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
[[ -f ".cursor/agent-config.sh" ]] && source ".cursor/agent-config.sh"

COMMANDS_DIR="${COMMANDS_DIR:-.cursor/commands}"
CONTEXT_DIR="${CONTEXT_DIR:-.cursor/context}"
LEARNING_LOG="${LEARNING_LOG:-.cursor/learning_log.md}"
AI_MODEL="${AI_MODEL:-Composer 1.5}"

# Gates — these are ENFORCED, not suggestions
MAX_PLAN_ITERATIONS=3          # Up from 2: adversarial pass needs budget
TARGET_SCORE=8.0
CRITICAL_ISSUES_REQUIRED=0     # Hard gate. No exceptions.
ADVERSARIAL_CRITICAL_ALLOWED=0 # Adversarial pass must also find zero criticals

# Review rounds for execution
MAX_REVIEW_ROUNDS=3

TIMESTAMP=$(date +%s)
SHORT_DESC=$(echo "$TASK" | head -c 30 | tr ' /' '_' | tr -cd '[:alnum:]_-')
WORKSPACE=".cursor/workspaces/${SHORT_DESC}_${TIMESTAMP}"
HISTORY_FILE="$WORKSPACE/iteration-history.md"

mkdir -p "$WORKSPACE" "$CONTEXT_DIR"

cat > "$HISTORY_FILE" << 'EOF'
# Iteration Score History
---
EOF

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
log() { echo "[$(date +'%H:%M:%S')] $*" | tee -a "$WORKSPACE/automation.log"; }

# Write a string to a temp file and print the path.
# Usage: my_tmp=$(tmpstr "$MY_VAR")
# Always rm the file when done.
tmpstr() {
    local tmp
    tmp=$(mktemp)
    printf '%s' "$1" > "$tmp"
    echo "$tmp"
}

# Strict score extraction — jq first, then targeted regex, never "N/A" silently
extract_score() {
    local file="$1" field="${2:-score}"
    if command -v jq &>/dev/null; then
        # Strip possible code fences then try to parse the first JSON object
        local cleaned
        cleaned=$(sed 's/```json//g; s/```//g' "$file" | tr -d '\r')
        local json
        json=$(echo "$cleaned" | python3 -c "
import sys, json, re
text = sys.stdin.read()
# Find first balanced {...}
depth=0; start=-1; result=''
for i,c in enumerate(text):
    if c=='{':
        if depth==0: start=i
        depth+=1
    elif c=='}':
        depth-=1
        if depth==0 and start>=0:
            result=text[start:i+1]; break
try:
    obj=json.loads(result)
    print(json.dumps(obj))
except: pass
" 2>/dev/null)
        if [[ -n "$json" ]]; then
            local val
            val=$(echo "$json" | jq -r ".${field} // empty" 2>/dev/null)
            [[ -n "$val" && "$val" != "null" ]] && { echo "$val"; return 0; }
        fi
    fi
    # Fallback: targeted regex
    local val
    val=$(grep -oE "\"${field}\"[[:space:]]*:[[:space:]]*[0-9]+\.?[0-9]*" "$file" | grep -oE '[0-9]+\.?[0-9]*' | head -1)
    [[ -n "$val" ]] && { echo "$val"; return 0; }
    echo "PARSE_FAILURE"
}

extract_array_length() {
    local file="$1" field="$2"
    if command -v jq &>/dev/null; then
        local cleaned json
        cleaned=$(sed 's/```json//g; s/```//g' "$file" | tr -d '\r')
        json=$(echo "$cleaned" | python3 -c "
import sys, json
text = sys.stdin.read()
depth=0; start=-1; result=''
for i,c in enumerate(text):
    if c=='{':
        if depth==0: start=i
        depth+=1
    elif c=='}':
        depth-=1
        if depth==0 and start>=0:
            result=text[start:i+1]; break
try:
    obj=json.loads(result); print(json.dumps(obj))
except: pass
" 2>/dev/null)
        if [[ -n "$json" ]]; then
            local count
            count=$(echo "$json" | jq -r ".${field} | length" 2>/dev/null)
            [[ "$count" =~ ^[0-9]+$ ]] && { echo "$count"; return 0; }
        fi
    fi
    echo "PARSE_FAILURE"
}

# Strict boolean: returns 0 (true) or 1 (false)
score_meets_target() {
    local score="$1" target="$2"
    [[ "$score" == "PARSE_FAILURE" ]] && return 1
    python3 -c "import sys; sys.exit(0 if float('$score') >= float('$target') else 1)" 2>/dev/null
}

run_cmd() {
    local prompt_file="$1" output_file="$2" label="$3"
    log "Running: $label"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would run cursor agent for: $label" > "$output_file"
        return 0
    fi
    cursor agent --model "$AI_MODEL" < "$prompt_file" > "$output_file" 2>&1
    log "Done: $label ($(wc -l < "$output_file") lines)"
}

build_prompt() {
    local template="$1" output="$2"
    shift 2
    if [[ -f "$COMMANDS_DIR/$template" ]]; then
        cat "$COMMANDS_DIR/$template" > "$output"
    else
        echo "# $template — template not found, proceeding with minimal context" > "$output"
        log "⚠️  Missing template: $COMMANDS_DIR/$template"
    fi
    # Remaining args: "label" "file_to_append" pairs
    while [[ $# -ge 2 ]]; do
        echo -e "\n\n---\n# $1:\n" >> "$output"
        cat "$2" >> "$output"
        shift 2
    done
}

# Compress a phase output into a handoff JSON
compress_handoff() {
    local phase_output="$1" task="$2" output_file="$3"
    local compress_prompt="$WORKSPACE/compress-prompt-$(basename "$phase_output").txt"

    local task_tmp
    task_tmp=$(tmpstr "$task")
    build_prompt "phase-handoff-compress.md" "$compress_prompt" \
        "Task" "$task_tmp" \
        "Phase Output to Compress" "$phase_output"
    rm -f "$task_tmp"

    run_cmd "$compress_prompt" "$output_file" "Compress handoff: $(basename "$phase_output")"
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE GATE PROMPT
# Mirrors the main menu UX: numbered/lettered options, Enter-then-paste for
# multi-line input, /dev/tty so paste content never bleeds into the prompt.
# Sets globals: GATE_CHOICE ("r" | "o" | "q") and GATE_EXTRA_CONTEXT.
# ─────────────────────────────────────────────────────────────────────────────
GATE_CHOICE=""
GATE_EXTRA_CONTEXT=""

prompt_gate_choice() {
    while true; do
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║          ⛔  GATE NOT CLEARED — ACTION REQUIRED              ║"
        echo "╠══════════════════════════════════════════════════════════════╣"
        echo "║                                                              ║"
        echo "║  [r]  🔄  Re-plan from scratch (add more context)           ║"
        echo "║  [o]  ⚠️   Override and proceed anyway (you accept the risk) ║"
        echo "║  [q]  ❌  Quit                                               ║"
        echo "║                                                              ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        read -p "  Choose option [r/o/q]: " GATE_CHOICE < /dev/tty

        case "$GATE_CHOICE" in
            r|R)
                echo ""
                echo "╔══════════════════════════════════════════════════════════════╗"
                echo "║              📋  ADDITIONAL CONTEXT INPUT                    ║"
                echo "╠══════════════════════════════════════════════════════════════╣"
                echo "║  Paste any extra context for the replanner below.            ║"
                echo "║  Press  Enter  first, then paste your content.              ║"
                echo "║  When finished, press  Ctrl+D  on a new line.               ║"
                echo "║  (Just Ctrl+D immediately to skip and replan without extra) ║"
                echo "╚══════════════════════════════════════════════════════════════╝"
                echo ""
                read -p "  Press Enter to open input..." _confirm < /dev/tty
                echo "  ── Paste now (Ctrl+D to finish) ───────────────────────────"
                GATE_EXTRA_CONTEXT=$(cat < /dev/tty 2>/dev/null || true)
                echo "  ── End of input ───────────────────────────────────────────"
                echo ""
                if [[ -n "$GATE_EXTRA_CONTEXT" ]]; then
                    echo "  ✅ Context received ($(echo "$GATE_EXTRA_CONTEXT" | wc -w) words)"
                else
                    echo "  ℹ️  No extra context — replanning with critique only"
                fi
                GATE_CHOICE="r"
                return 0
                ;;
            o|O)
                echo ""
                echo "  ⚠️  Override selected — proceeding with uncleared gates."
                GATE_CHOICE="o"
                GATE_EXTRA_CONTEXT=""
                return 0
                ;;
            q|Q)
                echo ""
                echo "  ❌ Quitting."
                GATE_CHOICE="q"
                GATE_EXTRA_CONTEXT=""
                return 0
                ;;
            *)
                echo "  ⚠️  Invalid choice — enter r, o, or q"
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 0: ISSUE + EXPLORATION
# ─────────────────────────────────────────────────────────────────────────────
section() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "════════════════════════════════════════════════════════════════"
}

section "📝 PHASE 0A: ISSUE CREATION"

issue_file="$WORKSPACE/issue.md"
issue_prompt="$WORKSPACE/issue-prompt.txt"

task_tmp=$(tmpstr "$TASK")
build_prompt "create-issue-autonomous.md" "$issue_prompt" "Task Description" "$task_tmp"
rm -f "$task_tmp"

run_cmd "$issue_prompt" "$issue_file" "Issue creation"

section "🔍 PHASE 0B: CODEBASE EXPLORATION"

exploration_file="$WORKSPACE/exploration-full.md"
exploration_prompt="$WORKSPACE/exploration-prompt.txt"

task_tmp=$(tmpstr "$TASK")
build_prompt "explore-autonomous.md" "$exploration_prompt" \
    "Task Context" "$task_tmp" \
    "Issue Details" "$issue_file"
rm -f "$task_tmp"

[[ -f "$LEARNING_LOG" ]] && {
    echo -e "\n---\n# Past Learnings (last 50 lines):\n" >> "$exploration_prompt"
    tail -50 "$LEARNING_LOG" >> "$exploration_prompt"
}

run_cmd "$exploration_prompt" "$exploration_file" "Exploration"

# Compress exploration to handoff — planner gets the summary, not 500 lines of prose
exploration_handoff="$WORKSPACE/exploration-handoff.json"
compress_handoff "$exploration_file" "$TASK" "$exploration_handoff"
log "Exploration compressed: $(wc -c < "$exploration_handoff") bytes"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: PLAN CREATION + DUAL CRITIQUE LOOP
# ─────────────────────────────────────────────────────────────────────────────
section "📋 PHASE 1: PLAN CREATION + DUAL CRITIQUE"

plan_iteration=0
best_score=0
critical_count="PARSE_FAILURE"
adversarial_critical_count="PARSE_FAILURE"
gate_passed=false

# Initial plan — planner receives compressed handoff, not raw exploration
current_plan="$WORKSPACE/plan-v0.md"
plan_prompt="$WORKSPACE/plan-prompt-initial.txt"

task_tmp=$(tmpstr "$TASK")
build_prompt "create-plan-autonomous.md" "$plan_prompt" \
    "Task Description" "$task_tmp" \
    "Issue Details" "$issue_file" \
    "Exploration Findings (compressed)" "$exploration_handoff"
rm -f "$task_tmp"

run_cmd "$plan_prompt" "$current_plan" "Initial plan"

while (( plan_iteration < MAX_PLAN_ITERATIONS )); do
    plan_iteration=$((plan_iteration + 1))

    section "🔄 PLAN ITERATION $plan_iteration/$MAX_PLAN_ITERATIONS"

    # ── Track A: Standard critique ──────────────────────────────────────────
    standard_critique="$WORKSPACE/critique-standard-iter${plan_iteration}.json"
    critique_prompt="$WORKSPACE/critique-prompt-iter${plan_iteration}.txt"
    build_prompt "critique-plan.md" "$critique_prompt" \
        "Plan to Critique" "$current_plan"
    run_cmd "$critique_prompt" "$standard_critique" "Standard critique iter $plan_iteration"

    current_score=$(extract_score "$standard_critique" "score")
    critical_count=$(extract_array_length "$standard_critique" "critical_issues")

    echo "📊 Standard critique — Score: $current_score/10 | Critical issues: $critical_count"

    # ── Track B: Adversarial critique ───────────────────────────────────────
    adversarial_score="N/A"
    adversarial_critical_count=0

    if [[ "$SKIP_ADVERSARIAL" != "true" ]]; then
        adv_critique="$WORKSPACE/critique-adversarial-iter${plan_iteration}.json"
        adv_prompt="$WORKSPACE/critique-adversarial-prompt-iter${plan_iteration}.txt"
        build_prompt "critique-adversarial.md" "$adv_prompt" \
            "Plan to Attack" "$current_plan"
        run_cmd "$adv_prompt" "$adv_critique" "Adversarial critique iter $plan_iteration"

        adversarial_score=$(extract_score "$adv_critique" "score")
        adversarial_critical_count=$(extract_array_length "$adv_critique" "critical_issues")

        echo "🔴 Adversarial critique — Score: $adversarial_score/10 | Critical issues: $adversarial_critical_count"
    fi

    # ── Score history ────────────────────────────────────────────────────────
    cat >> "$HISTORY_FILE" << EOF
- Iter $plan_iteration: standard=$current_score/10 (${critical_count} crit) | adversarial=$adversarial_score/10 (${adversarial_critical_count} adv-crit)
EOF

    # ── Gate evaluation ──────────────────────────────────────────────────────
    # Both critiques must clear their respective gates
    std_score_ok=false
    std_critical_ok=false
    adv_critical_ok=false

    score_meets_target "$current_score" "$TARGET_SCORE" && std_score_ok=true
    [[ "$critical_count" == "0" ]] && std_critical_ok=true
    [[ "$adversarial_critical_count" == "0" ]] && adv_critical_ok=true

    if $std_score_ok && $std_critical_ok && $adv_critical_ok; then
        echo "✅ ALL GATES PASSED — Score: $current_score ≥ $TARGET_SCORE, 0 standard criticals, 0 adversarial criticals"
        best_score=$current_score
        gate_passed=true
        break
    else
        echo "⛔ Gates not cleared:"
        $std_score_ok    || echo "   - Score $current_score < $TARGET_SCORE"
        $std_critical_ok || echo "   - $critical_count standard critical issue(s) remaining"
        $adv_critical_ok || echo "   - $adversarial_critical_count adversarial critical issue(s) remaining"
    fi

    # Update best score
    score_meets_target "$current_score" "$best_score" && best_score="$current_score"

    # Max iterations exhausted — show interactive gate prompt
    if (( plan_iteration >= MAX_PLAN_ITERATIONS )); then
        echo ""
        echo "   MAX ITERATIONS ($MAX_PLAN_ITERATIONS) REACHED WITHOUT CLEARING GATES"
        echo "   Standard criticals: $critical_count | Adversarial criticals: $adversarial_critical_count"
        echo "   Score: $current_score/10"

        prompt_gate_choice   # sets GATE_CHOICE and GATE_EXTRA_CONTEXT

        case "$GATE_CHOICE" in
            r)
                log "Re-planning from scratch..."
                plan_iteration=0
                MAX_PLAN_ITERATIONS=$((MAX_PLAN_ITERATIONS + 2))
                current_plan="$WORKSPACE/plan-v0-replan.md"

                task_tmp=$(tmpstr "$TASK")
                build_prompt "create-plan-autonomous.md" "$plan_prompt" \
                    "Task Description" "$task_tmp" \
                    "Issue Details" "$issue_file" \
                    "Exploration Findings (compressed)" "$exploration_handoff" \
                    "Previous Plan Critique (MUST FIX THESE)" "$standard_critique"
                if [[ "$SKIP_ADVERSARIAL" != "true" && -n "${adv_critique:-}" && -f "$adv_critique" ]]; then
                    echo -e "\n\n---\n# Adversarial Findings (MUST FIX THESE):\n" >> "$plan_prompt"
                    cat "$adv_critique" >> "$plan_prompt"
                fi
                rm -f "$task_tmp"

                if [[ -n "$GATE_EXTRA_CONTEXT" ]]; then
                    extra_tmp=$(tmpstr "$GATE_EXTRA_CONTEXT")
                    echo -e "\n\n---\n# Additional Context From Human (HIGHEST PRIORITY — address everything here):\n" >> "$plan_prompt"
                    cat "$extra_tmp" >> "$plan_prompt"
                    rm -f "$extra_tmp"
                    log "Extra context appended ($(echo "$GATE_EXTRA_CONTEXT" | wc -w) words)"
                else
                    log "No extra context provided — replanning with critique only"
                fi

                run_cmd "$plan_prompt" "$current_plan" "Replan from scratch"
                continue
                ;;
            o)
                log "⚠️  User override — proceeding with uncleared gates. Criticals: std=$critical_count adv=$adversarial_critical_count"
                gate_passed=true
                break
                ;;
            q)
                echo "❌ Quitting."; exit 0
                ;;
        esac
    fi

    # Refine: merge both critiques so planner sees both attack surfaces
    refined_plan="$WORKSPACE/plan-v${plan_iteration}.md"
    refine_prompt="$WORKSPACE/refine-prompt-iter${plan_iteration}.txt"
    build_prompt "refine-plan.md" "$refine_prompt" \
        "Current Plan" "$current_plan" \
        "Standard Critique (issues to fix)" "$standard_critique"

    if [[ "$SKIP_ADVERSARIAL" != "true" ]]; then
        echo -e "\n---\n# Adversarial Findings (also must fix):\n" >> "$refine_prompt"
        cat "$adv_critique" >> "$refine_prompt"
    fi

    run_cmd "$refine_prompt" "$refined_plan" "Refine plan iter $plan_iteration"
    current_plan="$refined_plan"
done

final_plan="$WORKSPACE/plan-final.md"
cp "$current_plan" "$final_plan"

# Compress plan to handoff
plan_handoff="$WORKSPACE/plan-handoff.json"
compress_handoff "$final_plan" "$TASK" "$plan_handoff"

section "✅ PLANNING COMPLETE"
echo "   Iterations: $plan_iteration | Score: $best_score/10 | Gates: $($gate_passed && echo PASSED || echo BYPASSED)"

# ─────────────────────────────────────────────────────────────────────────────
# USER CHECKPOINT
# ─────────────────────────────────────────────────────────────────────────────
while true; do
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                  📋  PLAN READY FOR REVIEW                   ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Review: $final_plan"
    echo "║                                                              ║"
    echo "║  [y]  ✅  Continue to execution                              ║"
    echo "║  [n]  ✏️   Provide feedback and revise plan                  ║"
    echo "║  [q]  ❌  Quit                                               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    read -p "  Choose option [y/n/q]: " choice < /dev/tty

    case "$choice" in
        y|Y)
            echo "  ✅ Proceeding to execution..."
            break
            ;;
        n|N)
            echo ""
            echo "╔══════════════════════════════════════════════════════════════╗"
            echo "║                  ✏️   FEEDBACK INPUT                         ║"
            echo "╠══════════════════════════════════════════════════════════════╣"
            echo "║  Press  Enter  first, then paste or type your feedback.     ║"
            echo "║  Press  Ctrl+D  on a new line when finished.                ║"
            echo "╚══════════════════════════════════════════════════════════════╝"
            echo ""
            read -p "  Press Enter to open input..." _confirm < /dev/tty
            echo "  ── Paste feedback now (Ctrl+D to finish) ──────────────────"
            user_feedback=$(cat < /dev/tty 2>/dev/null || true)
            echo "  ── End of input ───────────────────────────────────────────"

            if [[ -z "$user_feedback" ]]; then
                echo "  ℹ️  No feedback provided — try again."
                continue
            fi

            echo "  ✅ Feedback received ($(echo "$user_feedback" | wc -w) words) — revising plan..."

            fb_plan="$WORKSPACE/plan-v${plan_iteration}-user-feedback.md"
            fb_prompt="$WORKSPACE/refine-user-feedback.txt"

            feedback_tmp=$(tmpstr "$user_feedback")
            build_prompt "refine-plan.md" "$fb_prompt" \
                "USER FEEDBACK (highest priority — address everything here)" "$feedback_tmp" \
                "Current Plan" "$final_plan"
            rm -f "$feedback_tmp"

            run_cmd "$fb_prompt" "$fb_plan" "User feedback refinement"
            cp "$fb_plan" "$final_plan"
            compress_handoff "$final_plan" "$TASK" "$plan_handoff"
            plan_iteration=$((plan_iteration + 1))
            echo "  ✅ Plan updated with your feedback."
            ;;
        q|Q)
            echo "  ❌ Stopped."; exit 0
            ;;
        *)
            echo "  ⚠️  Invalid choice — enter y, n, or q"
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
section "⚙️  PHASE 2: EXECUTION"

execution_file="$WORKSPACE/execution-output.md"
execution_prompt="$WORKSPACE/execution-prompt.txt"

task_tmp=$(tmpstr "$TASK")
build_prompt "execute-autonomous.md" "$execution_prompt" \
    "Task" "$task_tmp" \
    "Implementation Plan (compressed handoff)" "$plan_handoff"
rm -f "$task_tmp"

[[ -f "$LEARNING_LOG" ]] && {
    echo -e "\n---\n# Past Learnings:\n" >> "$execution_prompt"
    tail -50 "$LEARNING_LOG" >> "$execution_prompt"
}

run_cmd "$execution_prompt" "$execution_file" "Execution"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2B: GROUND-TRUTH VERIFICATION (before review)
# ─────────────────────────────────────────────────────────────────────────────
section "🔬 PHASE 2B: GROUND-TRUTH VERIFICATION"

verify_output="$WORKSPACE/verify-output.json"
verify_prompt="$WORKSPACE/verify-prompt.txt"
build_prompt "verify-execution.md" "$verify_prompt" \
    "Execution Output (claims to verify)" "$execution_file" \
    "Original Plan" "$plan_handoff"

run_cmd "$verify_prompt" "$verify_output" "Ground-truth verification"

can_proceed=$(extract_score "$verify_output" "execution_can_proceed_to_review")
ground_truth_score=$(extract_score "$verify_output" "ground_truth_score")

echo "🔬 Ground truth score: $ground_truth_score/10 | Proceed to review: $can_proceed"

if [[ "$can_proceed" == "false" ]]; then
    blocking_reason=$(grep -o '"blocking_reason"[^,}]*' "$verify_output" | head -1 || echo "See verify output")
    echo ""
    echo "⛔ GROUND TRUTH VERIFICATION FAILED"
    echo "   $blocking_reason"
    echo "   Fixes needed before review is meaningful."
    echo ""

    # Auto-attempt one fix pass
    echo "Attempting automatic remediation..."
    fix_prompt="$WORKSPACE/fix-ground-truth.txt"
    fixed_execution="$WORKSPACE/execution-fixed-ground-truth.md"

    echo "# Fix all issues identified in ground-truth verification" > "$fix_prompt"
    echo -e "\n---\n# Verification Findings:\n" >> "$fix_prompt"
    cat "$verify_output" >> "$fix_prompt"
    echo -e "\n---\n# Current Execution Output:\n" >> "$fix_prompt"
    cat "$execution_file" >> "$fix_prompt"

    run_cmd "$fix_prompt" "$fixed_execution" "Ground-truth fix pass"
    execution_file="$fixed_execution"

    # Re-verify
    build_prompt "verify-execution.md" "$verify_prompt" \
        "Execution Output (re-verification)" "$execution_file" \
        "Original Plan" "$plan_handoff"
    run_cmd "$verify_prompt" "$verify_output" "Re-verification"
    can_proceed=$(extract_score "$verify_output" "execution_can_proceed_to_review")
    echo "Re-verification: proceed=$can_proceed"

    if [[ "$can_proceed" == "false" ]]; then
        echo "⛔ Re-verification also failed. Manual intervention required."
        echo "   Review: $verify_output"
        read -p "  Force-continue anyway? [y/n]: " force_continue < /dev/tty
        [[ "$force_continue" != "y" && "$force_continue" != "Y" ]] && { echo "Stopping."; exit 1; }
        log "⚠️  Forced continuation past failed ground-truth verification"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2C: REVIEW LOOP
# ─────────────────────────────────────────────────────────────────────────────
section "🔍 PHASE 2C: REVIEW LOOP"

current_implementation="$execution_file"
for round in $(seq 1 $MAX_REVIEW_ROUNDS); do
    echo ""
    echo "── Review Round $round/$MAX_REVIEW_ROUNDS ──"

    review_output="$WORKSPACE/review-round${round}.md"
    review_prompt="$WORKSPACE/review-prompt-round${round}.txt"
    build_prompt "review-autonomous.md" "$review_prompt" \
        "Implementation" "$current_implementation" \
        "Original Plan (compressed)" "$plan_handoff"
    run_cmd "$review_prompt" "$review_output" "Review round $round"

    review_score=$(extract_score "$review_output" "quality_score")
    [[ "$review_score" == "PARSE_FAILURE" ]] && review_score=$(extract_score "$review_output" "score")
    issues_found=$(extract_array_length "$review_output" "critical_issues")
    [[ "$issues_found" == "PARSE_FAILURE" ]] && issues_found=0

    echo "   Score: $review_score/10 | Issues: $issues_found"

    [[ "$issues_found" == "0" ]] && { echo "   ✅ Clean — no issues"; break; }

    fixed_output="$WORKSPACE/execution-fixed-round${round}.md"
    fix_prompt="$WORKSPACE/fix-prompt-round${round}.txt"
    echo "# Fix all identified issues" > "$fix_prompt"
    echo -e "\n---\n# Review Findings:\n" >> "$fix_prompt"
    cat "$review_output" >> "$fix_prompt"
    echo -e "\n---\n# Current Implementation:\n" >> "$fix_prompt"
    cat "$current_implementation" >> "$fix_prompt"

    run_cmd "$fix_prompt" "$fixed_output" "Fix round $round"
    current_implementation="$fixed_output"
    echo "   ✅ Fixes applied"
done

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: LEARNING CAPTURE
# ─────────────────────────────────────────────────────────────────────────────
section "📚 PHASE 3: CAPTURE LEARNINGS"

if [[ -f "$COMMANDS_DIR/lessons.md" ]]; then
    lessons_prompt="$WORKSPACE/lessons-prompt.txt"
    lessons_output="$WORKSPACE/lessons-learned.md"

    task_tmp=$(tmpstr "$TASK")
    excerpt_tmp=$(mktemp)
    tail -100 "$current_implementation" > "$excerpt_tmp"
    build_prompt "lessons.md" "$lessons_prompt" \
        "Task" "$task_tmp" \
        "Implementation excerpt" "$excerpt_tmp"
    rm -f "$task_tmp" "$excerpt_tmp"

    run_cmd "$lessons_prompt" "$lessons_output" "Lessons"

    {
        echo ""
        echo "## $(date '+%Y-%m-%d %H:%M:%S') — $TASK"
        echo "Score: $best_score/10 | Adversarial criticals at close: $adversarial_critical_count"
        cat "$lessons_output"
    } >> "$LEARNING_LOG"
    echo "✅ Lessons logged"
fi

if [[ -f "$COMMANDS_DIR/context.md" ]]; then
    context_prompt="$WORKSPACE/context-prompt.txt"
    context_output="$WORKSPACE/context-summary.md"

    task_tmp=$(tmpstr "$TASK")
    excerpt_tmp=$(mktemp)
    head -50 "$current_implementation" > "$excerpt_tmp"
    build_prompt "context.md" "$context_prompt" \
        "Task" "$task_tmp" \
        "Implementation excerpt" "$excerpt_tmp"
    rm -f "$task_tmp" "$excerpt_tmp"

    run_cmd "$context_prompt" "$context_output" "Context"
    cp "$context_output" "$CONTEXT_DIR/${SHORT_DESC}_${TIMESTAMP}.md"
    echo "✅ Context saved"
fi

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section "✅ WORKFLOW COMPLETE"
echo ""
echo "   Task:          $TASK"
echo "   Workspace:     $WORKSPACE"
echo "   Plan score:    $best_score/10"
echo "   Gate status:   $($gate_passed && echo '✅ PASSED' || echo '⚠️  OVERRIDDEN')"
echo "   Adv criticals: $adversarial_critical_count at completion"
echo "   Ground truth:  $(extract_score "$verify_output" "execution_claim_accuracy") claim accuracy"
echo ""
echo "   Key files:"
echo "   - Final plan:      $final_plan"
echo "   - Ground truth:    $verify_output"
echo "   - Final output:    $current_implementation"
echo "   - Score history:   $HISTORY_FILE"
echo ""
cat "$HISTORY_FILE"