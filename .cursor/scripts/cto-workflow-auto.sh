#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# CTO WORKFLOW v7 — DUAL CRITIQUE PIPELINE
# ═══════════════════════════════════════════════════════════════════
#
# ARCHITECTURE:
#   explore
#     -> generate (reason-first)
#       -> validate (model-based, not grep)
#         -> critique-strategy  (scoring -> drives refine)
#           -> [refine once if score < threshold]
#             -> critique-adversarial  (attack surface -> shown at checkpoint)
#               -> human checkpoint    (sees plan + adversarial findings together)
#                 -> execute
#                   -> distill learnings
#
# FILES REQUIRED IN .cursor/commands/:
#   cto_pm.md                -- task generation system prompt
#   critique-strategy.md     -- scoring critique (outputs top_3_avg_priority)
#   critique-adversarial.md  -- attack surface critique (outputs score + sabotage_vectors)
#
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Dependency check ──────────────────────────────────────────────
if ! command -v jq &>/dev/null; then
    echo "jq is required. Install: brew install jq (mac) or apt install jq (linux)"
    exit 1
fi

# ── Config ────────────────────────────────────────────────────────
[[ -f ".cursor/agent-config.sh" ]] && source ".cursor/agent-config.sh"

COMMANDS_DIR="${COMMANDS_DIR:-.cursor/commands}"
MEMORY_DIR="${MEMORY_DIR:-.cursor/memory}"
TASKSPACE_DIR=".cursor/taskspace"
AI_MODEL="${AI_MODEL:-Composer 1.5}"

# Strategy score threshold: if top_3_avg_priority >= this, skip refine pass
SKIP_REFINE_THRESHOLD="${SKIP_REFINE_THRESHOLD:-8.0}"

# Adversarial score threshold: warn human prominently if below this
ADVERSARIAL_WARN_THRESHOLD="${ADVERSARIAL_WARN_THRESHOLD:-6.0}"

# ── Context intake ────────────────────────────────────────────────
if [[ -z "${1:-}" ]]; then
    echo "Usage: ./cto.sh '<context>' '<goal>'"
    echo "  Example: ./cto.sh 'fundraise' 'Raise seed round in 5 days'"
    exit 1
fi

USER_CONTEXT="$1"
GOAL_CONTEXT="${2:-}"

mkdir -p "$MEMORY_DIR" "$TASKSPACE_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TASKSPACE="$TASKSPACE_DIR/${TIMESTAMP}"
mkdir -p "$TASKSPACE"

log() { echo "[$(date +'%H:%M:%S')] $*" | tee -a "$TASKSPACE/cto.log"; }
log "Session start | Context: $USER_CONTEXT | Goal: $GOAL_CONTEXT"

# ── Context type detection ────────────────────────────────────────
# Used for display and prompt injection ONLY.
# Tier 1 enforcement is model-based. Grep cannot understand context.
detect_context_type() {
    local c; c=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    echo "$c" | grep -qE "demo|investor|presentation|pitch|showcase" && { echo "demo";      return; }
    echo "$c" | grep -qE "raise|seed|fundraise|round|funding"        && { echo "fundraise"; return; }
    echo "$c" | grep -qE "scale|performance|backend|infrastructure"   && { echo "scale";     return; }
    echo "$c" | grep -qE "feature|add|build|implement|create"         && { echo "feature";   return; }
    echo "$c" | grep -qE "fix|bug|issue|problem|error|crash"          && { echo "fix";       return; }
    echo "general"
}
CONTEXT_TYPE=$(detect_context_type "$USER_CONTEXT")
log "Context type: $CONTEXT_TYPE"

# ── File helpers ──────────────────────────────────────────────────
load_file_if_exists() {
    [[ -f "$1" ]] && cat "$1" || echo "(not found: $1)"
}

load_context_bundle() {
    echo "=== PAST LEARNINGS ==="
    load_file_if_exists "$MEMORY_DIR/learnings.md" | tail -80
    echo ""
    echo "=== PRODUCT VISION ==="
    load_file_if_exists ".cursor/product/vision.md"
    echo ""
    echo "=== CODEBASE SUMMARY ==="
    load_file_if_exists "$TASKSPACE/codebase-summary.md"
}

# ── Core model call ───────────────────────────────────────────────
# system_file: path to .md file, sent verbatim as system prompt
# user_prompt: string, the user turn content
# out_file:    where to write the model response
call_model() {
    local system_file="$1"
    local user_prompt="$2"
    local out_file="$3"

    if [[ ! -f "$system_file" ]]; then
        log "System prompt file not found: $system_file"
        return 1
    fi

    local prompt_file
    prompt_file=$(mktemp /tmp/cto-XXXXXX)

    {
        echo "SYSTEM:"
        cat "$system_file"
        echo ""
        echo "---"
        echo ""
        echo "USER:"
        printf '%s' "$user_prompt"
    } > "$prompt_file"

    cursor agent --model "${AI_MODEL}" < "$prompt_file" > "$out_file" 2>&1
    local exit_code=$?
    rm -f "$prompt_file"

    if [[ $exit_code -ne 0 || ! -s "$out_file" ]]; then
        log "Model call failed (exit $exit_code) for $(basename "$system_file")"
        return 1
    fi
    return 0
}

# ── JSON extraction ───────────────────────────────────────────────
# Strip markdown fences models add despite instructions, then jq
jq_from_output() {
    local file="$1"
    local query="$2"
    grep -v '```' "$file" 2>/dev/null | jq -r "$query" 2>/dev/null || echo ""
}

# ── Fallback JSON writers ─────────────────────────────────────────
write_strategy_fallback() {
    echo '{"top_3_avg_priority":5.0,"overall_strategy_score":5.0,"critical_issues":["Critique unavailable"],"suggestions":[],"minor_issues":[]}' > "$1"
}

write_adversarial_fallback() {
    echo '{"score":7.0,"adversarial_verdict":"Adversarial critique unavailable.","critical_issues":[],"minimum_fixes_before_execution":[],"sabotage_vectors":[],"blind_spots":[],"recommended_action":"proceed"}' > "$1"
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 0: CODEBASE EXPLORATION
# ═══════════════════════════════════════════════════════════════════
explore_codebase() {
    log "Exploring codebase..."
    local out="$TASKSPACE/codebase-summary.md"
    local prompt_file
    prompt_file=$(mktemp /tmp/cto-XXXXXX)

    {
        printf 'SYSTEM:\n'
        printf 'You are a senior software architect. Scan the codebase and produce a concise summary (under 50 lines):\n'
        printf '1. Tech stack and main libraries\n'
        printf '2. Key directories and purposes\n'
        printf '3. Main entry points\n'
        printf '4. Key files for new features\n'
        printf '5. Architecture pattern\n\n'
        printf 'One line per item. File paths only. No code snippets. Be fast.\n\n'
        printf -- '---\n\n'
        printf 'USER:\n'
        printf 'Analyze the current directory and produce the summary.\n'
    } > "$prompt_file"

    if cursor agent --model "${AI_MODEL}" < "$prompt_file" > "$out" 2>&1; then
        local lc; lc=$(wc -l < "$out" 2>/dev/null || echo 0)
        [[ "$lc" -lt 3 ]] && log "Codebase summary short ($lc lines) -- continuing"
    else
        log "Codebase exploration failed -- continuing without codebase context"
        echo "(codebase exploration unavailable)" > "$out"
    fi

    rm -f "$prompt_file"
    log "Codebase summary ready -> $out"
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 1: GENERATE (reason-first)
# ═══════════════════════════════════════════════════════════════════
generate_tasks() {
    log "Generating tasks (reason-first)..."
    local out="$TASKSPACE/tasks_raw.md"
    local ctx_bundle; ctx_bundle=$(load_context_bundle)

    # Heredoc assigned to variable only -- not piped directly, so no pipe issues
    local user_prompt
    user_prompt=$(cat <<USERPROMPT
CONTEXT: ${USER_CONTEXT}
GOAL: ${GOAL_CONTEXT}
CONTEXT TYPE: ${CONTEXT_TYPE}

${ctx_bundle}

---

STEP 0 -- REASON FIRST (required before generating any tasks)

Before producing any task, answer these questions in 3-5 sentences max each:

Q1. Who is the specific human?
Name the exact person or role this work is for. What must they say yes to, and by when?

Q2. What is the single biggest obstacle?
The one thing that -- if not fixed -- makes the goal impossible. Not the second biggest. The first.

Q3. What already exists that I can leverage?
Based on the codebase summary, what existing code, routes, or components reduce the need to build from scratch?

Q4. What is the pre-mortem failure mode?
If this plan fails, what is the most likely reason? How does the task list directly address that failure mode?

Only after answering all 4 questions, produce the TOP 3 tasks in the format from your system prompt.

IMPORTANT:
- Exactly 3 tasks. Not 4, not 5.
- Follow the output format in your system prompt precisely.
- Cut list must include at least 2 items with the filter that killed them.
USERPROMPT
)

    call_model "$COMMANDS_DIR/cto_pm.md" "$user_prompt" "$out"
    log "Tasks generated -> $out"
    echo ""
    cat "$out"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 2: MODEL-BASED VALIDATION
# Replaces grep-based Tier 1. Model understands context; grep does not.
# "investor" is valid in fundraise context. Grep fires on it regardless.
# ═══════════════════════════════════════════════════════════════════
validate_tasks() {
    local tasks_file="$1"
    log "Validating tasks (model-based)..."
    local out="$TASKSPACE/validation.json"

    local val_sys
    val_sys=$(mktemp /tmp/cto-XXXXXX)
    cat > "$val_sys" << 'VALSYS'
You are a strict task validator for a startup CTO workflow.

Determine if a task list contains any non-software tasks.

A non-software task does NOT result in code being written, modified, or deployed.
Examples: pitch decks, financial models, investor emails, market research, spreadsheets.

CONTEXT RULE:
- "investor" or "fundraise" in a task is VALID if the task builds software investors will see
  (metrics endpoint, dashboard, traction API, demo flow, public URL).
- "investor" or "fundraise" is INVALID only if the task IS non-code work:
  pitch content, financial modeling, investor outreach strategy.

Output ONLY valid JSON. First char: {. Last char: }.
Valid:   {"valid": true,  "issues": [], "verdict": "PASS"}
Invalid: {"valid": false, "issues": ["Task 2: 'Write pitch deck' is not software"], "verdict": "FAIL"}
VALSYS

    local val_user="CONTEXT TYPE: ${CONTEXT_TYPE}

TASK LIST:
$(cat "$tasks_file")

Is this task list valid? Output only JSON."

    call_model "$val_sys" "$val_user" "$out"
    local call_exit=$?
    rm -f "$val_sys"

    # Default to pass on infra failure -- don't block the workflow
    if [[ $call_exit -ne 0 ]]; then
        log "Validation model call failed -- defaulting to PASS"
        return 0
    fi

    local valid
    valid=$(jq_from_output "$out" '.valid // true')
    if [[ "$valid" == "false" ]]; then
        log "Validation failed:"
        jq_from_output "$out" '.issues[]?' | while read -r issue; do
            echo "  $issue"
        done
        return 1
    fi
    log "Validation passed"
    return 0
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 3a: SCORING CRITIQUE
# Uses critique-strategy.md. Outputs top_3_avg_priority.
# This score and only this score drives the refine decision.
# ═══════════════════════════════════════════════════════════════════
critique_strategy() {
    local tasks_file="$1"
    log "Running scoring critique..."
    local out="$TASKSPACE/critique-strategy.json"

    local user_prompt
    user_prompt=$(cat <<CPROMPT
CONTEXT TYPE: ${CONTEXT_TYPE}
GOAL: ${GOAL_CONTEXT}

TASK LIST:
$(cat "$tasks_file")

PAST LEARNINGS:
$(load_file_if_exists "$MEMORY_DIR/learnings.md" | tail -40)

Critique this task list. Output ONLY valid JSON. No markdown, no prose.
CPROMPT
)

    if ! call_model "$COMMANDS_DIR/critique-strategy.md" "$user_prompt" "$out"; then
        log "Scoring critique call failed -- using fallback score"
        write_strategy_fallback "$out"
    fi

    # Validate JSON is parseable
    if ! jq_from_output "$out" '.' | jq . >/dev/null 2>&1; then
        log "Scoring critique JSON invalid -- using fallback score"
        write_strategy_fallback "$out"
    fi

    local score
    score=$(jq_from_output "$out" '.top_3_avg_priority // 5.0')
    log "Strategy score: $score / 10"

    echo ""
    echo "  Strategy score: $score / 10"
    jq_from_output "$out" '.critical_issues[]?' | while read -r i; do echo "  CRITICAL: $i"; done
    jq_from_output "$out" '.minor_issues[]?'    | while read -r i; do echo "  MINOR:    $i"; done
    echo ""

    echo "$score"
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 3b: REFINE (max one pass)
# Only runs when strategy score < SKIP_REFINE_THRESHOLD.
# Writes to fixed path -- caller never captures stdout.
# ═══════════════════════════════════════════════════════════════════
refine_tasks() {
    local tasks_file="$1"
    local critique_file="$2"
    log "Refining tasks (one pass)..."

    local user_prompt
    user_prompt=$(cat <<RPROMPT
CONTEXT: ${USER_CONTEXT}
GOAL: ${GOAL_CONTEXT}
CONTEXT TYPE: ${CONTEXT_TYPE}

ORIGINAL TASKS:
$(cat "$tasks_file")

SCORING CRITIQUE (JSON):
$(cat "$critique_file")

PAST LEARNINGS:
$(load_file_if_exists "$MEMORY_DIR/learnings.md" | tail -40)

CODEBASE SUMMARY:
$(load_file_if_exists "$TASKSPACE/codebase-summary.md")

---

Produce a refined task list that fixes every critical issue in the critique.
Keep what scored well. Replace only what scored poorly.
Exactly 3 tasks in your system prompt format.
Do NOT introduce scope not justified by the critique.
RPROMPT
)

    call_model "$COMMANDS_DIR/cto_pm.md" "$user_prompt" "$TASKSPACE/tasks_refined.md"
    log "Refined tasks ready -> $TASKSPACE/tasks_refined.md"
    # No stdout output here -- caller references $TASKSPACE/tasks_refined.md directly
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 4: ADVERSARIAL CRITIQUE
# Uses critique-adversarial.md. Attacks the FINAL plan (after refine).
# Replaces the separate premortem step -- adversarial already has richer
# pre-mortem scenarios built into its output schema.
# ═══════════════════════════════════════════════════════════════════
critique_adversarial() {
    local tasks_file="$1"
    log "Running adversarial critique..."
    local out="$TASKSPACE/critique-adversarial.json"

    local user_prompt
    user_prompt=$(cat <<APROMPT
CONTEXT TYPE: ${CONTEXT_TYPE}
GOAL: ${GOAL_CONTEXT}

TASK LIST TO ATTACK:
$(cat "$tasks_file")

Find every way this plan fails. Output ONLY valid JSON.
APROMPT
)

    if ! call_model "$COMMANDS_DIR/critique-adversarial.md" "$user_prompt" "$out"; then
        log "Adversarial critique call failed -- using fallback"
        write_adversarial_fallback "$out"
    fi

    if ! jq_from_output "$out" '.' | jq . >/dev/null 2>&1; then
        log "Adversarial critique JSON invalid -- using fallback"
        write_adversarial_fallback "$out"
    fi

    log "Adversarial critique ready -> $out"
}

# ── Display adversarial findings ──────────────────────────────────
display_adversarial() {
    local adv="$TASKSPACE/critique-adversarial.json"
    [[ ! -f "$adv" ]] && return

    local adv_score verdict recommended
    adv_score=$(jq_from_output "$adv" '.score // "N/A"')
    verdict=$(jq_from_output "$adv" '.adversarial_verdict // ""')
    recommended=$(jq_from_output "$adv" '.recommended_action // "proceed"')

    echo ""
    echo "================================================================"
    echo "  ADVERSARIAL CRITIQUE -- Score: $adv_score / 10"
    echo "================================================================"
    echo ""
    [[ -n "$verdict" ]] && echo "Verdict: $verdict" && echo ""

    # Critical issues
    local n; n=$(jq_from_output "$adv" '.critical_issues | length' 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
        echo "CRITICAL ISSUES ($n):"
        jq_from_output "$adv" '.critical_issues[]?' | while read -r x; do echo "  * $x"; done
        echo ""
    fi

    # Sabotage vectors
    n=$(jq_from_output "$adv" '.sabotage_vectors | length' 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
        echo "SABOTAGE VECTORS ($n):"
        # Use index iteration to avoid subshell quoting issues
        local i
        for i in $(seq 0 $((n - 1))); do
            local step attack blast
            step=$(jq_from_output "$adv"  ".sabotage_vectors[$i].step")
            attack=$(jq_from_output "$adv" ".sabotage_vectors[$i].attack")
            blast=$(jq_from_output "$adv"  ".sabotage_vectors[$i].blast_radius")
            echo "  Step $step: $attack"
            echo "  Blast radius: $blast"
            echo ""
        done
    fi

    # Blind spots
    n=$(jq_from_output "$adv" '.blind_spots | length' 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
        echo "BLIND SPOTS ($n):"
        jq_from_output "$adv" '.blind_spots[]?' | while read -r x; do echo "  * $x"; done
        echo ""
    fi

    # Pre-mortem
    local pp ps
    pp=$(jq_from_output "$adv" '.pre_mortem.partial_execution // ""')
    ps=$(jq_from_output "$adv" '.pre_mortem.silent_corruption // ""')
    if [[ -n "$pp" || -n "$ps" ]]; then
        echo "PRE-MORTEM:"
        [[ -n "$pp" ]] && echo "  Partial exec:  $pp"
        [[ -n "$ps" ]] && echo "  Silent fail:   $ps"
        echo ""
    fi

    # Minimum fixes
    n=$(jq_from_output "$adv" '.minimum_fixes_before_execution | length' 2>/dev/null || echo 0)
    if [[ "$n" -gt 0 ]]; then
        echo "MINIMUM FIXES BEFORE EXECUTION ($n):"
        jq_from_output "$adv" '.minimum_fixes_before_execution[]?' | while read -r x; do echo "  [ ] $x"; done
        echo ""
    fi

    # Low score warning
    local warn
    warn=$(echo "$adv_score < $ADVERSARIAL_WARN_THRESHOLD" | bc -l 2>/dev/null || echo 0)
    if [[ "$warn" == "1" ]]; then
        echo "WARNING: Adversarial score $adv_score < threshold $ADVERSARIAL_WARN_THRESHOLD"
        echo "The adversarial critic found serious failure risks in this plan."
        echo "Consider addressing the minimum fixes above before approving."
        echo ""
    fi

    echo "Recommended action: $recommended"
    echo "================================================================"
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 5: HUMAN CHECKPOINT
# Human sees final plan immediately above adversarial findings.
# Makes the decision with full attack surface visible.
# ═══════════════════════════════════════════════════════════════════
human_checkpoint() {
    local tasks_file="$1"

    echo ""
    echo "================================================================"
    echo "  FINAL PLAN"
    echo "================================================================"
    cat "$tasks_file"

    display_adversarial

    echo ""
    echo "----------------------------------------------------------------"
    echo "You have seen the plan and the adversarial failure analysis."
    read -rp "Approve and execute? (y/n): " approve

    if [[ ! "$approve" =~ ^[Yy] ]]; then
        log "Plan rejected by human."
        read -rp "Why rejected? (press Enter to skip): " rejection_reason
        if [[ -n "$rejection_reason" ]]; then
            {
                echo ""
                echo "## REJECTED: $TIMESTAMP"
                echo "- Context: $CONTEXT_TYPE"
                echo "- Reason: $rejection_reason"
            } >> "$MEMORY_DIR/learnings.md"
        fi
        echo "Plan rejected -- session ended."
        exit 1
    fi

    log "Plan approved by human."
}

# ═══════════════════════════════════════════════════════════════════
# PHASE 6: EXECUTE
# ═══════════════════════════════════════════════════════════════════
execute_tasks() {
    local tasks_file="$1"
    log "Executing tasks..."

    local task_count
    task_count=$(grep -cE "^## (🔥|⚡) Task [0-9]" "$tasks_file" 2>/dev/null || echo 0)

    if [[ "$task_count" -eq 0 ]]; then
        log "No tasks in expected format -- executing full file"
        _execute_single_block "All Tasks" "$(cat "$tasks_file")"
        return
    fi

    local task_num=0 in_task=false task_title="" task_body=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^##\ (🔥|⚡)\ Task\ ([0-9]+)\ —\ (.*) ]]; then
            if [[ "$in_task" == true && -n "$task_title" ]]; then
                _execute_single_block "$task_title" "$task_body" || {
                    log "Task $task_num failed -- stopping"
                    return 1
                }
                if [[ $task_num -eq 1 ]]; then
                    echo ""
                    read -rp "  Task 1 done. Continue with tasks 2 and 3? (y/n): " cont
                    [[ ! "$cont" =~ ^[Yy] ]] && { log "Stopped after Task 1."; return 0; }
                fi
            fi
            task_num=$((task_num + 1))
            task_title="${BASH_REMATCH[3]}"
            task_body=""
            in_task=true
        elif [[ "$in_task" == true ]]; then
            task_body+="$line"$'\n'
        fi
    done < "$tasks_file"

    if [[ "$in_task" == true && -n "$task_title" ]]; then
        _execute_single_block "$task_title" "$task_body"
    fi
}

_execute_single_block() {
    local title="$1"
    local body="$2"

    echo ""
    echo "-----------------------------------------------------------"
    echo "  EXECUTING: $title"
    echo "-----------------------------------------------------------"
    log "Executing: $title"

    local agent_prompt
    agent_prompt=$(mktemp /tmp/cto-XXXXXX)
    {
        echo "SYSTEM:"
        echo "You are implementing a software task. Execute it completely."
        echo "Follow the existing codebase patterns."
        echo "Make reasonable decisions without asking for clarification."
        echo "When done, write: DONE: [one sentence summary of what changed]"
        echo ""
        echo "---"
        echo ""
        echo "USER:"
        echo "PROJECT: ${USER_CONTEXT}"
        echo "GOAL: ${GOAL_CONTEXT}"
        echo ""
        echo "TASK: ${title}"
        echo ""
        printf '%s' "${body}"
        echo ""
        echo "Implement this fully. No half-measures."
    } > "$agent_prompt"

    cursor agent --model "${AI_MODEL}" < "$agent_prompt"
    local ec=$?
    rm -f "$agent_prompt"

    [[ $ec -ne 0 ]] && { log "Failed: $title"; return 1; }
    log "Done: $title"
    return 0
}

# ═══════════════════════════════════════════════════════════════════
# LEARNING DISTILLATION
# Extracts from both critiques: strategy suggestions + adversarial blind spots
# These compound over time -- the longer you run this, the smarter it gets
# ═══════════════════════════════════════════════════════════════════
distill_learnings() {
    local strategy_score="$1"

    {
        echo ""
        echo "## Session: $TIMESTAMP | Type: $CONTEXT_TYPE | Strategy: $strategy_score"
        echo "Goal: $(echo "$GOAL_CONTEXT" | head -1)"
        echo ""

        if [[ -f "$TASKSPACE/critique-strategy.json" ]]; then
            local suggestions
            suggestions=$(jq_from_output "$TASKSPACE/critique-strategy.json" '.suggestions[]?' | head -3)
            if [[ -n "$suggestions" ]]; then
                echo "Strategy suggestions:"
                echo "$suggestions" | sed 's/^/  - /'
            fi
        fi

        if [[ -f "$TASKSPACE/critique-adversarial.json" ]]; then
            local adv_score
            adv_score=$(jq_from_output "$TASKSPACE/critique-adversarial.json" '.score // "N/A"')
            echo "Adversarial score: $adv_score"

            local blind_spots
            blind_spots=$(jq_from_output "$TASKSPACE/critique-adversarial.json" '.blind_spots[]?' | head -2)
            if [[ -n "$blind_spots" ]]; then
                echo "Blind spots found:"
                echo "$blind_spots" | sed 's/^/  - /'
            fi

            local fixes
            fixes=$(jq_from_output "$TASKSPACE/critique-adversarial.json" '.minimum_fixes_before_execution[]?' | head -2)
            if [[ -n "$fixes" ]]; then
                echo "Minimum fixes required:"
                echo "$fixes" | sed 's/^/  - /'
            fi
        fi

        echo ""
    } >> "$MEMORY_DIR/learnings.md"

    log "Learnings updated -> $MEMORY_DIR/learnings.md"
}

# ═══════════════════════════════════════════════════════════════════
# STARTUP CHECKS
# Fail fast before burning any LLM calls on missing files
# ═══════════════════════════════════════════════════════════════════
startup_checks() {
    local missing=0
    for f in "cto_pm.md" "critique-strategy.md" "critique-adversarial.md"; do
        if [[ ! -f "$COMMANDS_DIR/$f" ]]; then
            echo "Missing: $COMMANDS_DIR/$f"
            missing=$((missing + 1))
        fi
    done
    if [[ $missing -gt 0 ]]; then
        echo ""
        echo "Copy the required .md files to $COMMANDS_DIR/ and retry."
        exit 1
    fi
    log "Startup checks passed. All command files present."
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "+---------------------------------------------------------------+"
echo "|  CTO WORKFLOW v7 -- DUAL CRITIQUE PIPELINE                   |"
echo "|  critique-strategy (score) + critique-adversarial (attack)   |"
echo "+---------------------------------------------------------------+"
echo ""
echo "  Context: $USER_CONTEXT"
echo "  Goal:    $GOAL_CONTEXT"
echo "  Type:    $CONTEXT_TYPE"
echo ""

# Pre-flight: fail fast if any command file is missing
startup_checks

# Phase 0: Explore codebase
explore_codebase

# Phase 1: Generate with reasoning
generate_tasks

# Phase 2: Model-based validation (not grep)
if ! validate_tasks "$TASKSPACE/tasks_raw.md"; then
    log "Validation failed -- regenerating once"
    generate_tasks
    validate_tasks "$TASKSPACE/tasks_raw.md" || {
        log "Validation failed twice -- check cto_pm.md"
        exit 1
    }
fi

CURRENT_TASKS="$TASKSPACE/tasks_raw.md"

# Phase 3a: Scoring critique -- drives refine decision
echo "================================================================"
echo "  SCORING CRITIQUE (critique-strategy.md)"
echo "================================================================"
STRATEGY_SCORE=$(critique_strategy "$CURRENT_TASKS")

# Phase 3b: Refine if score below threshold
meets_threshold=$(echo "$STRATEGY_SCORE >= $SKIP_REFINE_THRESHOLD" | bc -l 2>/dev/null || echo 0)
if [[ "$meets_threshold" != "1" ]]; then
    echo "================================================================"
    echo "  REFINE (score $STRATEGY_SCORE < threshold $SKIP_REFINE_THRESHOLD)"
    echo "================================================================"
    refine_tasks "$CURRENT_TASKS" "$TASKSPACE/critique-strategy.json"
    CURRENT_TASKS="$TASKSPACE/tasks_refined.md"
    log "Using refined tasks: $CURRENT_TASKS"
else
    log "Score $STRATEGY_SCORE >= $SKIP_REFINE_THRESHOLD -- skipping refine"
fi

# Phase 4: Adversarial critique -- attacks the FINAL plan, not the draft
echo "================================================================"
echo "  ADVERSARIAL CRITIQUE (critique-adversarial.md)"
echo "================================================================"
critique_adversarial "$CURRENT_TASKS"

# Phase 5: Human checkpoint -- plan + adversarial findings side by side
human_checkpoint "$CURRENT_TASKS"

# Phase 6: Execute
execute_tasks "$CURRENT_TASKS"

# Distill learnings from both critiques into memory
distill_learnings "$STRATEGY_SCORE"

echo ""
echo "================================================================"
echo "  SESSION COMPLETE"
echo "  Taskspace:  $TASKSPACE"
echo "  Learnings:  $MEMORY_DIR/learnings.md"
echo "================================================================"
log "Session complete."