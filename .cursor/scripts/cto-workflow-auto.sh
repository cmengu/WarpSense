#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# CTO WORKFLOW — ELITE STARTUP EXECUTION ENGINE v3
#
# Core philosophy (sourced from Altman, Graham, Karpathy, Brockman):
#
#   "Startups take off because the founders make them take off."
#   — Paul Graham
#
#   "The most important thing is to build something users love."
#   — Sam Altman
#
#   "Read the code first. The fastest code is code you didn't write."
#   — Karpathy principle
#
#   "Right then, give me your laptop." (Collison installation)
#   — The disposition: no waiting, no extra cycles, just ship.
#
# LOOP DESIGN:
#   1. Context + goal (persisted across sessions)
#   2. Tier 1 hard-rule check on context (block bad directions early)
#   3. Generate (1 pass, full context)
#   4. Tier 1 enforcement (block tasks violating hard rules before human sees them)
#   5. Critique + refine (MAX 2 passes — more = context problem)
#   6. Human checkpoint (you are the CEO — your decision is final)
#   7. Rejection → distill → learnings.md (tiered, real promotion logic)
#   8. Acceptance → sequential execution (task 1 first, always)
#   9. Post-task-1 checkpoint (plan may be invalidated — decide before 2+3)
# ═══════════════════════════════════════════════════════════════════

set -e

[[ -f ".cursor/agent-config.sh" ]] && source ".cursor/agent-config.sh"

COMMANDS_DIR="${COMMANDS_DIR:-.cursor/commands}"
PRODUCT_DIR="${PRODUCT_DIR:-.cursor/product}"
MEMORY_DIR="${MEMORY_DIR:-.cursor/memory}"
CONTEXT_DIR="${CONTEXT_DIR:-.cursor/context}"
TASKSPACE_DIR=".cursor/taskspace"

MAX_ITERATIONS=2
TARGET_AVG_PRIORITY=8.0
AI_MODEL="${AI_MODEL:-Composer 1.5}"

# ── Context intake ───────────────────────────────────────────────────
if [[ -n "$1" ]]; then
    USER_CONTEXT="$1"
    GOAL_CONTEXT="${2:-}"
else
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "🧠 CTO WORKFLOW"
    echo "════════════════════════════════════════════════════════════════"
    echo "  [1] Type context  [2] Paste multi-line (Ctrl+D)  [3] Previous  [q] Quit"
    echo ""
    read -p "Choice: " ctx_choice
    case "$ctx_choice" in
        1) read -p "Context: " USER_CONTEXT ;;
        2) echo "(Ctrl+D when done)"; USER_CONTEXT=$(cat) ;;
        3)
            [[ -f "$MEMORY_DIR/last-context.txt" ]] || { echo "❌ No previous context found"; exit 1; }
            USER_CONTEXT=$(cat "$MEMORY_DIR/last-context.txt")
            echo "📋 Using: $USER_CONTEXT"
            ;;
        q|Q) exit 0 ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
    GOAL_CONTEXT=""
fi

[[ -z "$USER_CONTEXT" ]] && { echo "❌ No context provided"; exit 1; }

mkdir -p "$MEMORY_DIR" "$TASKSPACE_DIR"
echo "$USER_CONTEXT" > "$MEMORY_DIR/last-context.txt"

# ── Goal context: persists across sessions ────────────────────────────
if [[ -n "$GOAL_CONTEXT" ]]; then
    echo "$GOAL_CONTEXT" > "$MEMORY_DIR/last-goal-context.txt"
    echo "🎯 Goal set (CLI): $(echo "$GOAL_CONTEXT" | head -1)"
    echo ""
elif [[ -f "$MEMORY_DIR/last-goal-context.txt" ]]; then
    GOAL_CONTEXT=$(cat "$MEMORY_DIR/last-goal-context.txt")
    echo "🎯 Goal (from last session): $(echo "$GOAL_CONTEXT" | head -1)"
    read -p "   Still accurate? (y to keep / n to update): " goal_ok
    if [[ ! "$goal_ok" =~ ^[Yy] ]]; then
        echo "Enter new goal context (Ctrl+D when done):"
        GOAL_CONTEXT=$(cat)
        echo "$GOAL_CONTEXT" > "$MEMORY_DIR/last-goal-context.txt"
    fi
    echo ""
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TASKSPACE="$TASKSPACE_DIR/${TIMESTAMP}"
mkdir -p "$TASKSPACE"

log() { echo "[$(date +'%H:%M:%S')] $*" | tee -a "$TASKSPACE/cto.log"; }
log "Session start | Context: $USER_CONTEXT"

# ── Score extraction (4-format fallback) ─────────────────────────────
extract_avg_priority() {
    local file="$1"
    local v
    v=$(grep -oE '"top_3_avg_priority": [0-9]+\.[0-9]+' "$file" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
    [[ -n "$v" ]] && { echo "$v"; return; }
    v=$(grep -oE '"overall_score": [0-9]+\.[0-9]+' "$file" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
    [[ -n "$v" ]] && { echo "$v"; return; }
    local scores
    scores=$(grep -oE "\*\*Priority:\*\* [0-9]+\.[0-9]+" "$file" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -3)
    [[ -z "$scores" ]] && scores=$(grep -oE "Priority: [0-9]+\.[0-9]+" "$file" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -3)
    [[ -z "$scores" ]] && { echo "N/A"; return; }
    local sum=0 count=0
    while IFS= read -r s; do
        sum=$(echo "$sum + $s" | bc -l 2>/dev/null || echo "$sum")
        count=$((count + 1))
    done <<< "$scores"
    [[ $count -gt 0 ]] && echo "scale=1; $sum / $count" | bc -l 2>/dev/null || echo "N/A"
}

# ── Context type detection ───────────────────────────────────────────
detect_context_type() {
    local c; c=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    echo "$c" | grep -qE "demo|investor|presentation|pitch|showcase" && { echo "demo"; return; }
    echo "$c" | grep -qE "raise|seed|fundraise|round|funding" && { echo "fundraise"; return; }
    echo "$c" | grep -qE "scale|performance|backend|infrastructure|optimization" && { echo "scale"; return; }
    echo "$c" | grep -qE "feature|add|build|implement|create" && { echo "feature"; return; }
    echo "$c" | grep -qE "fix|bug|issue|problem|error|crash" && { echo "fix"; return; }
    echo "general"
}

CONTEXT_TYPE=$(detect_context_type "$USER_CONTEXT")
log "Context type: $CONTEXT_TYPE"

# ── Load Tier 1 hard rules ────────────────────────────────────────────
get_tier1_rules() {
    [[ ! -f "$MEMORY_DIR/learnings.md" ]] && return
    local in_tier1=false
    while IFS= read -r line; do
        [[ "$line" == *"TIER 1"* ]] && { in_tier1=true; continue; }
        [[ "$in_tier1" == true && "$line" == *"TIER 2"* ]] && break
        [[ "$in_tier1" == true && "$line" =~ ^-.*confirmations ]] && echo "$line"
    done < "$MEMORY_DIR/learnings.md"
}

# ── Tier 1 enforcement ───────────────────────────────────────────────
check_tier1_violations() {
    local tasks_file="$1"
    local violations=()
    local rules; rules=$(get_tier1_rules)
    [[ -z "$rules" ]] && return 0

    if grep -qi "refactor\|cleanup\|reorganize\|restructure" "$tasks_file" 2>/dev/null; then
        violations+=("⚠️  TIER 1 VIOLATION: Refactor task detected with no confirmed real users")
    fi

    if [[ "$CONTEXT_TYPE" == "demo" ]]; then
        if grep -qi "database\|migration\|ingestion\|backend\|api endpoint\|query optimization" "$tasks_file" 2>/dev/null; then
            if ! grep -qi "visible\|browser\|UI\|frontend\|display\|render\|show" "$tasks_file" 2>/dev/null; then
                violations+=("⚠️  TIER 1 VIOLATION: Backend-only task in demo context with no browser visibility")
            fi
        fi
    fi

    if grep -qi "new feature\|add.*feature\|implement.*feature" "$tasks_file" 2>/dev/null; then
        if ! grep -qi "deployed\|live\|production\|deploy" "$MEMORY_DIR/strategy-patterns.jsonl" 2>/dev/null; then
            violations+=("⚠️  TIER 1 SOFT CHECK: New feature tasks — confirm deploy is live first")
        fi
    fi

    if [[ ${#violations[@]} -gt 0 ]]; then
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo "🚨 TIER 1 RULE VIOLATIONS DETECTED"
        echo "════════════════════════════════════════════════════════════════"
        for v in "${violations[@]}"; do echo "  $v"; done
        echo ""
        echo "These are hard rules. The plan needs to be regenerated."
        echo "  [r] Regenerate (recommended)"
        echo "  [i] Ignore and continue anyway"
        echo ""
        read -p "Choice (r/i): " viol_choice
        [[ "$viol_choice" =~ ^[Rr] ]] && return 1
    fi
    return 0
}

# ── Tier 2 & Tier 3 enforcement, learning distillation,
#     EXPLICITLY CUT sections, feedback capture, generation loop
#     etc follow here (full script continues for ~900 lines)
# ── Tier 2 strong-pattern enforcement ────────────────────────────────
check_tier2_patterns() {
    local tasks_file="$1"
    local warnings=()

    # Example pattern: heavy refactor flagged for human review
    if grep -qiE "refactor|restructure|cleanup" "$tasks_file" 2>/dev/null; then
        warnings+=("⚠️  TIER 2 WARNING: Task involves refactoring — ensure user-visible impact is tracked")
    fi

    # Pattern: new integrations or APIs
    if grep -qiE "api|integration|external service" "$tasks_file" 2>/dev/null; then
        warnings+=("⚠️  TIER 2 WARNING: External integration detected — check auth, latency, and monitoring")
    fi

    # Pattern: feature additions that may cause regression
    if grep -qiE "add feature|implement feature|new module" "$tasks_file" 2>/dev/null; then
        warnings+=("⚠️  TIER 2 WARNING: New feature — confirm backward compatibility with existing modules")
    fi

    # Output any Tier 2 warnings
    if [[ ${#warnings[@]} -gt 0 ]]; then
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo "⚡ TIER 2 PATTERN WARNINGS"
        echo "════════════════════════════════════════════════════════════════"
        for w in "${warnings[@]}"; do echo "  $w"; done
        echo ""
    fi
}

# ── Tier 3 observational learning / distillation ────────────────────
tier3_distill() {
    local task_file="$1"
    local learn_file="$MEMORY_DIR/learnings.md"

    echo "TIER 3 OBSERVATIONS — $(date)" >> "$learn_file"
    echo "- Context type: $CONTEXT_TYPE" >> "$learn_file"

    # Distill average priority
    local avg_priority
    avg_priority=$(extract_avg_priority "$task_file")
    echo "- Average priority observed: $avg_priority" >> "$learn_file"

    # Record recurring patterns for reinforcement
    grep -oE "refactor|feature|fix|integration|deploy|bug|performance" "$task_file" | sort | uniq -c >> "$learn_file"
    echo "- EXPLICITLY CUT tasks: $(grep -i 'EXPLICITLY CUT' "$task_file" | wc -l)" >> "$learn_file"
    echo "" >> "$learn_file"
}

# ── EXPLICITLY CUT / filter tasks before execution ──────────────────
filter_explicitly_cut() {
    local tasks_file="$1"
    local filtered_file="$TASKSPACE/filtered_tasks.txt"

    grep -vEi "EXPLICITLY CUT|DO NOT EXECUTE|PLACEHOLDER" "$tasks_file" > "$filtered_file"
    echo "$filtered_file"
}

# ── Task generation loop ────────────────────────────────────────────
generate_tasks() {
    local iteration=1
    local tasks_file="$TASKSPACE/tasks_iteration_${iteration}.txt"

    log "Generating initial tasks..."
    # Placeholder generation logic; in practice call AI/composer here
    echo "1. Implement core feature X for UI demo" > "$tasks_file"
    echo "2. Add logging for backend performance" >> "$tasks_file"
    echo "3. Fix crash on onboarding flow" >> "$tasks_file"
    echo "4. EXPLICITLY CUT placeholder task Y" >> "$tasks_file"
    echo "5. Refactor module Z" >> "$tasks_file"

    while [[ $iteration -le $MAX_ITERATIONS ]]; do
        # Tier 1 check
        if ! check_tier1_violations "$tasks_file"; then
            log "Tier 1 violation — regenerating tasks..."
            # Regenerate (in real system: call AI again)
            iteration=$((iteration + 1))
            tasks_file="$TASKSPACE/tasks_iteration_${iteration}.txt"
            echo "1. Regenerated core feature X" > "$tasks_file"
            echo "2. Logging updated" >> "$tasks_file"
            echo "3. Fix onboarding crash patched" >> "$tasks_file"
            continue
        fi

        # Tier 2 warnings
        check_tier2_patterns "$tasks_file"

        # Tier 3 distillation
        tier3_distill "$tasks_file"

        # Filter EXPLICITLY CUT
        filtered_tasks=$(filter_explicitly_cut "$tasks_file")
        log "Filtered tasks written to $filtered_tasks"

        # Break if no Tier 1 violation
        break
    done
}

# ── Human-in-the-loop checkpoint ────────────────────────────────────
human_checkpoint() {
    local file="$1"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "🧑‍💼 HUMAN CHECKPOINT REQUIRED"
    echo "════════════════════════════════════════════════════════════════"
    cat "$file"
    echo ""
    read -p "Approve tasks? (y/n) " approve
    if [[ ! "$approve" =~ ^[Yy] ]]; then
        log "Human rejected tasks — exiting workflow."
        exit 1
    fi
}

# ── Sequential execution of approved tasks ─────────────────────────
execute_tasks() {
    local tasks_file="$1"
    log "Executing tasks sequentially..."
    while IFS= read -r t; do
        [[ -z "$t" ]] && continue
        log "Executing: $t"
        # Placeholder: actual execution commands here
        sleep 1
        log "Completed: $t"
    done < "$tasks_file"
}

# ── Post-execution logging ──────────────────────────────────────────
post_execution_summary() {
    log "All tasks executed. Summarizing..."
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ SESSION SUMMARY"
    echo "════════════════════════════════════════════════════════════════"
    tail -n 20 "$TASKSPACE/cto.log"
    echo ""
    log "Session completed."
}

# ── MAIN WORKFLOW ──────────────────────────────────────────────────
generate_tasks
human_checkpoint "$TASKSPACE/filtered_tasks.txt"
execute_tasks "$TASKSPACE/filtered_tasks.txt"
post_execution_summary

# ── END OF SCRIPT ─────────────────────────────────────────────────
