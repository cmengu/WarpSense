#!/bin/bash
set -e

TASK="${1:?Error: Provide task description}"

# Load configuration
if [[ -f ".cursor/agent-config.sh" ]]; then
    source ".cursor/agent-config.sh"
fi

# Setup directories
COMMANDS_DIR="${COMMANDS_DIR:-.cursor/commands}"
CONTEXT_DIR="${CONTEXT_DIR:-.cursor/context}"
LEARNING_LOG="${LEARNING_LOG:-.cursor/learning_log.md}"

# Create workspace
TIMESTAMP=$(date +%s)
SHORT_DESC=$(echo "$TASK" | head -c 30 | tr ' /' '_' | tr -cd '[:alnum:]_-')
WORKSPACE=".cursor/workspaces/${SHORT_DESC}_${TIMESTAMP}"
HISTORY_FILE="$WORKSPACE/iteration-history.md"

mkdir -p "$WORKSPACE"
mkdir -p "$CONTEXT_DIR"
mkdir -p "$(dirname "$CONTEXT_DIR")" 2>/dev/null || true

# Initialize iteration history (LIGHTWEIGHT - only scores)
cat > "$HISTORY_FILE" << 'EOF'
# Iteration Score History

This tracks score progression only (not full context to save tokens).

---

EOF

# Logging
log() {
    echo "[$(date +'%H:%M:%S')] $*" | tee -a "$WORKSPACE/automation.log"
}

# Extract score with robust JSON parsing
extract_score() {
    local file="$1"
    local pattern="${2:-score}"
    
    if command -v jq &> /dev/null; then
        local json=$(sed 's/```json//g; s/```//g' "$file" | sed -n '/^{/,/^}/p' | tr -d '\n')
        
        if [[ -n "$json" ]]; then
            local score=$(echo "$json" | jq -r ".${pattern} // empty" 2>/dev/null)
            if [[ -n "$score" && "$score" != "null" ]]; then
                echo "$score"
                return 0
            fi
        fi
    fi
    
    local score=$(grep -oE "\"${pattern}\"[[:space:]]*:[[:space:]]*[0-9]+\.?[0-9]*" "$file" | \
                  grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [[ -n "$score" ]]; then
        echo "$score"
        return 0
    fi
    
    score=$(grep -iE "(${pattern}|quality)[[:space:]]*[:-][[:space:]]*[0-9]+\.?[0-9]*" "$file" | \
            grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [[ -n "$score" ]]; then
        echo "$score"
        return 0
    fi
    
    score=$(grep -oE '[0-9]+\.?[0-9]*/10' "$file" | \
            grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [[ -n "$score" ]]; then
        echo "$score"
        return 0
    fi
    
    echo "N/A"
}

# Extract issues
extract_issues() {
    local file="$1"
    local issue_type="$2"
    
    if command -v jq &> /dev/null; then
        local json=$(sed 's/```json//g; s/```//g' "$file" | sed -n '/^{/,/^}/p' | tr -d '\n')
        
        if [[ -n "$json" ]]; then
            local result=$(echo "$json" | jq -r ".${issue_type}[]? // empty" 2>/dev/null | paste -sd ", " -)
            if [[ -n "$result" ]]; then
                echo "$result"
                return 0
            fi
            
            local count=$(echo "$json" | jq -r ".${issue_type} // empty" 2>/dev/null)
            if [[ -n "$count" && "$count" != "null" && "$count" =~ ^[0-9]+$ ]]; then
                echo "$count"
                return 0
            fi
        fi
    fi
    
    local result=$(sed -n "s/.*\"${issue_type}\"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p" "$file" | head -1)
    if [[ -n "$result" ]]; then
        echo "$result"
        return 0
    fi
    
    echo "none"
}

# Multi-line feedback collection
collect_feedback() {
    local prompt_msg="$1"
    
    echo ""
    echo "════════════════════════════════════════"
    echo "📝 $prompt_msg"
    echo "════════════════════════════════════════"
    echo "Enter your feedback (press Ctrl+D when done):"
    echo ""
    
    local feedback=$(cat)
    echo "$feedback"
}

log "Starting token-optimized autonomous workflow..."
log "Task: $TASK"

# ═══════════════════════════════════════════════════════════════════
# PHASE 0: ISSUE CREATION & CODEBASE EXPLORATION (FULLY AUTOMATED)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📝 PHASE 0: ISSUE CREATION (AUTOMATED)"
echo "════════════════════════════════════════════════════════════════"

log "Phase 0: Creating issue..."

issue_file="$WORKSPACE/issue.md"
issue_prompt="$WORKSPACE/issue-prompt.txt"

if [[ -f "$COMMANDS_DIR/create-issue-autonomous.md" ]]; then
    log "Using create-issue-autonomous.md"
    cat "$COMMANDS_DIR/create-issue-autonomous.md" > "$issue_prompt"
else
    cat > "$issue_prompt" << 'EOF'
# Create GitHub Issue

Create a detailed GitHub issue for the task.

Include:
1. Title (under 80 chars)
2. Problem Statement
3. Current Behavior
4. Desired Behavior
5. Acceptance Criteria (checkbox list)
6. Technical Notes

Output in markdown format.
EOF
fi

echo -e "\n\n---\n# Task Description:\n$TASK\n" >> "$issue_prompt"

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$issue_prompt" > "$issue_file" 2>&1

issue_lines=$(wc -l < "$issue_file")
echo "✅ Issue Created: $issue_lines lines"

# ────────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🔍 PHASE 0: CODEBASE EXPLORATION (AUTOMATED)"
echo "════════════════════════════════════════════════════════════════"

log "Phase 0: Exploring codebase..."

exploration_file="$WORKSPACE/exploration-full.md"
exploration_prompt="$WORKSPACE/exploration-prompt.txt"

if [[ -f "$COMMANDS_DIR/explore-autonomous.md" ]]; then
    log "Using explore-autonomous.md"
    cat "$COMMANDS_DIR/explore-autonomous.md" > "$exploration_prompt"
else
    cat > "$exploration_prompt" << 'EOF'
# Codebase Exploration

Explore the codebase to understand current implementation.

Find:
1. Relevant files and their purposes
2. Current architecture and patterns
3. Tech stack and libraries
4. Integration points for changes
5. Potential challenges

Provide structured report with file paths and code examples.
EOF
fi

echo -e "\n\n---\n# Task Context:\n$TASK\n" >> "$exploration_prompt"
echo -e "\n---\n# Issue Details:\n" >> "$exploration_prompt"
cat "$issue_file" >> "$exploration_prompt"

if [[ -f "$LEARNING_LOG" ]]; then
    echo -e "\n---\n# Past Learnings (for reference):\n" >> "$exploration_prompt"
    tail -50 "$LEARNING_LOG" >> "$exploration_prompt"
fi

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$exploration_prompt" > "$exploration_file" 2>&1

exploration_lines=$(wc -l < "$exploration_file")
echo "✅ Exploration Complete: $exploration_lines lines"

# ════════════════════════════════════════════════════════════════════
# TOKEN OPTIMIZATION: COMPRESS EXPLORATION TO SUMMARY
# ════════════════════════════════════════════════════════════════════

echo ""
echo "💾 TOKEN OPTIMIZATION: Compressing exploration..."

exploration_summary="$WORKSPACE/exploration-summary.md"
summary_prompt="$WORKSPACE/summary-prompt.txt"

cat > "$summary_prompt" << 'EOF'
# Compress Exploration to Key Facts

Your task: Compress the exploration report to ~30 lines of KEY FACTS ONLY.

## What to Keep:
1. File paths with one-line descriptions
2. Critical architecture decisions
3. Key dependencies/libraries
4. Integration points
5. Major risks

## What to Drop:
- Long code examples (keep file paths only)
- Verbose explanations
- Redundant information
- Historical context

## Format:
```
## Key Files
- path/to/file.tsx - brief description
- path/to/other.ts - brief description

## Architecture
- Uses X for Y
- Pattern: Z

## Risks
- Risk 1
- Risk 2
```

Keep it under 40 lines. Be extremely concise.

---

# Full Exploration to Compress:

EOF

cat "$exploration_file" >> "$summary_prompt"

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$summary_prompt" > "$exploration_summary" 2>&1

summary_lines=$(wc -l < "$exploration_summary")
original_size=$(wc -c < "$exploration_file")
summary_size=$(wc -c < "$exploration_summary")
reduction=$((100 - (summary_size * 100 / original_size)))

echo "✅ Compressed: $exploration_lines lines → $summary_lines lines ($reduction% smaller)"
log "Token savings: Exploration compressed from $original_size to $summary_size bytes"

# ═══════════════════════════════════════════════════════════════════
# PHASE 1: PLAN CREATION & INTELLIGENT REFINEMENT LOOP (AUTOMATED)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📋 PHASE 1: PLAN CREATION & REFINEMENT (TOKEN-OPTIMIZED)"
echo "════════════════════════════════════════════════════════════════"

log "Phase 1: Creating initial plan..."

MAX_PLAN_ITERATIONS=5
TARGET_SCORE=9.0
plan_iteration=0
best_score=0
no_improvement_count=0
current_plan="$WORKSPACE/plan-v0.md"
score_history=()

# ═══════════════════════════════════════════════════════════════════
# STEP 1: INITIAL PLAN CREATION (with summary, not full exploration)
# ═══════════════════════════════════════════════════════════════════

plan_prompt="$WORKSPACE/plan-prompt-initial.txt"

if [[ -f "$COMMANDS_DIR/create-plan-autonomous.md" ]]; then
    log "Using create-plan-autonomous.md"
    cat "$COMMANDS_DIR/create-plan-autonomous.md" > "$plan_prompt"
else
    cat > "$plan_prompt" << 'EOF'
# Create Implementation Plan

Create a detailed implementation plan with:
1. Clear, numbered steps
2. Specific code examples
3. Verification criteria
4. Dependencies and prerequisites
5. Error handling
6. Time estimates

Output in markdown format.
EOF
fi

echo -e "\n\n---\n# Task Description:\n$TASK\n" >> "$plan_prompt"
echo -e "\n---\n# Issue Details:\n" >> "$plan_prompt"
cat "$issue_file" >> "$plan_prompt"
echo -e "\n---\n# Codebase Key Facts (Compressed):\n" >> "$plan_prompt"
cat "$exploration_summary" >> "$plan_prompt"  # ← TOKEN SAVINGS: Use summary not full

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$plan_prompt" > "$current_plan" 2>&1

line_count=$(wc -l < "$current_plan")
echo "✅ Initial Plan: $line_count lines"

# ═══════════════════════════════════════════════════════════════════
# REFINEMENT LOOP - TOKEN OPTIMIZED
# ═══════════════════════════════════════════════════════════════════

previous_plan=""  # Track last plan for regression comparison only

while (( plan_iteration < MAX_PLAN_ITERATIONS )); do
    plan_iteration=$((plan_iteration + 1))
    
    echo ""
    echo "════════════════════════════════════════"
    echo "🔄 REFINEMENT ITERATION $plan_iteration/$MAX_PLAN_ITERATIONS"
    echo "════════════════════════════════════════"
    
    # ───────────────────────────────────────────────────────────────
    # CRITIQUE - MINIMAL CONTEXT
    # ───────────────────────────────────────────────────────────────
    
    log "Critiquing plan (iteration $plan_iteration)..."
    
    critique_file="$WORKSPACE/plan-critique-iter${plan_iteration}.json"
    critique_prompt="$WORKSPACE/critique-prompt-iter${plan_iteration}.txt"
    
    if [[ -f "$COMMANDS_DIR/critique-plan.md" ]]; then
        cat "$COMMANDS_DIR/critique-plan.md" > "$critique_prompt"
    else
        cat > "$critique_prompt" << 'EOF'
# Plan Quality Analysis

Analyze and score this plan (0-10).

Output JSON:
{
  "score": 7.5,
  "critical_issues": [],
  "minor_issues": [],
  "strengths": [],
  "reasoning": "",
  "improvement_priority": []
}

Then provide detailed analysis.
EOF
    fi
    
    # TOKEN OPTIMIZATION: Only send score history (not full iteration details)
    echo -e "\n\n---\n# Score History:\n" >> "$critique_prompt"
    for i in "${!score_history[@]}"; do
        echo "- Iteration $((i+1)): ${score_history[$i]}/10" >> "$critique_prompt"
    done
    
    # TOKEN OPTIMIZATION: Only send current plan (not all previous versions)
    echo -e "\n---\n# Plan to Critique:\n" >> "$critique_prompt"
    cat "$current_plan" >> "$critique_prompt"
    
    cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$critique_prompt" > "$critique_file" 2>&1
    
    current_score=$(extract_score "$critique_file" "score")
    critical_issues=$(extract_issues "$critique_file" "critical_issues")
    minor_issues=$(extract_issues "$critique_file" "minor_issues")
    
    echo "📊 Critique Score: $current_score/10 (Best: $best_score/10)"
    echo "🔍 Critical Issues: $critical_issues"
    
    # Update lightweight history (scores only)
    cat >> "$HISTORY_FILE" << EOF
- Iteration $plan_iteration: $current_score/10 (Critical: $critical_issues, Minor: $minor_issues)
EOF
    
    # ───────────────────────────────────────────────────────────────
    # SCORE REGRESSION DETECTION - WITH COMPARISON
    # ───────────────────────────────────────────────────────────────
    
    score_history+=("$current_score")
    regression_analysis=""
    
    if [[ "$current_score" != "N/A" && "$best_score" != "0" ]]; then
        score_decreased=$(echo "$current_score < $best_score" | bc -l 2>/dev/null || echo 0)
        
        if (( score_decreased )); then
            echo "⚠️  SCORE REGRESSION DETECTED: $best_score → $current_score"
            
            log "Triggering self-correction for score regression..."
            
            regression_analysis="$WORKSPACE/regression-analysis-iter${plan_iteration}.md"
            regression_prompt="$WORKSPACE/regression-prompt-iter${plan_iteration}.txt"
            
            cat > "$regression_prompt" << EOF
# Score Regression Self-Analysis

**CRITICAL**: The plan score has DECREASED from $best_score/10 to $current_score/10.

## Your Task:
1. Analyze WHY the score decreased
2. Identify what changes made things worse
3. Determine how to recover the best elements
4. Create a recovery strategy

## Score History:
EOF
            
            for i in "${!score_history[@]}"; do
                echo "- Iteration $((i+1)): ${score_history[$i]}/10" >> "$regression_prompt"
            done
            
            cat >> "$regression_prompt" << 'EOF'

## Instructions:
- Compare current plan with previous iteration
- Identify specific changes that caused regression
- List strengths that were lost
- Propose concrete fixes

Output analysis in JSON + detailed explanation.

EOF
            
            echo -e "\n---\n# Current Plan (Lower Score):\n" >> "$regression_prompt"
            cat "$current_plan" >> "$regression_prompt"
            
            # Only include previous plan for comparison (not all history)
            if [[ -n "$previous_plan" ]]; then
                echo -e "\n---\n# Previous Plan (Higher Score):\n" >> "$regression_prompt"
                echo "$previous_plan" >> "$regression_prompt"
            fi
            
            echo -e "\n---\n# Latest Critique:\n" >> "$regression_prompt"
            cat "$critique_file" >> "$regression_prompt"
            
            cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$regression_prompt" > "$regression_analysis" 2>&1
            
            echo "🔍 Regression analysis complete"
            
            cat >> "$HISTORY_FILE" << EOF
  ⚠️  REGRESSION: $best_score → $current_score
EOF
        fi
    fi
    
    # ───────────────────────────────────────────────────────────────
    # CHECK STOPPING CONDITIONS
    # ───────────────────────────────────────────────────────────────
    
    if [[ "$current_score" != "N/A" ]]; then
        score_achieved=$(echo "$current_score >= $TARGET_SCORE" | bc -l 2>/dev/null || echo 0)
        
        if (( score_achieved )); then
            echo "✅ Target score achieved! ($current_score >= $TARGET_SCORE)"
            break
        fi
        
        score_improved=$(echo "$current_score > $best_score" | bc -l 2>/dev/null || echo 0)
        
        if (( score_improved )); then
            best_score=$current_score
            no_improvement_count=0
        else
            no_improvement_count=$((no_improvement_count + 1))
            echo "⚠️  No improvement for $no_improvement_count iteration(s)"
            
            if (( no_improvement_count >= 3 )); then
                echo "🛑 Stopping: Plateau detected (3 iterations without improvement)"
                break
            fi
        fi
    fi
    
    # ───────────────────────────────────────────────────────────────
    # REFINE - MINIMAL CONTEXT
    # ───────────────────────────────────────────────────────────────
    
    log "Refining plan..."
    
    # Save current plan as previous for next regression check
    previous_plan=$(cat "$current_plan")
    
    refined_plan="$WORKSPACE/plan-v${plan_iteration}.md"
    refine_prompt="$WORKSPACE/refine-prompt-iter${plan_iteration}.txt"
    
    if [[ -f "$COMMANDS_DIR/refine-plan.md" ]]; then
        cat "$COMMANDS_DIR/refine-plan.md" > "$refine_prompt"
    else
        cat > "$refine_prompt" << 'EOF'
# Refine Plan

Fix all critical issues. Preserve strengths.

Output the COMPLETE refined plan in markdown.
EOF
    fi
    
    # TOKEN OPTIMIZATION: Only send what's needed
    echo -e "\n\n---\n# Score Progression:\n${score_history[*]}\n" >> "$refine_prompt"
    echo -e "\n---\n# Current Plan:\n" >> "$refine_prompt"
    cat "$current_plan" >> "$refine_prompt"
    echo -e "\n---\n# Latest Critique (TODO List):\n" >> "$refine_prompt"
    cat "$critique_file" >> "$refine_prompt"
    
    # Only add regression analysis if it exists
    if [[ -f "$regression_analysis" ]]; then
        echo -e "\n---\n# REGRESSION ANALYSIS (MUST ADDRESS):\n" >> "$refine_prompt"
        cat "$regression_analysis" >> "$refine_prompt"
    fi
    
    cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$refine_prompt" > "$refined_plan" 2>&1
    
    refined_lines=$(wc -l < "$refined_plan")
    echo "📄 Refined Plan: $refined_lines lines"
    
    current_plan="$refined_plan"
    line_count=$refined_lines
done

final_plan="$WORKSPACE/plan-final.md"
cp "$current_plan" "$final_plan"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ PLAN REFINEMENT COMPLETE (TOKEN-OPTIMIZED)"
echo "════════════════════════════════════════════════════════════════"
echo "📊 Iterations: $plan_iteration"
echo "📊 Final Score: $best_score/10"
echo "📊 Score Progression: ${score_history[*]}"
echo "════════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════
# USER DECISION POINT: Continue or provide feedback
# ═══════════════════════════════════════════════════════════════════

while true; do
    echo ""
    echo "════════════════════════════════════════"
    echo "⏸️  CHECKPOINT: Plan Ready"
    echo "════════════════════════════════════════"
    echo "📄 Plan location: $final_plan"
    echo "📊 Final score: $best_score/10"
    echo ""
    echo "Options:"
    echo "  [y] Continue to execution ✅"
    echo "  [n] Provide feedback and refine again 🔄"
    echo "  [q] Quit ❌"
    echo ""
    read -p "Your choice (y/n/q): " choice
    
    case "$choice" in
        y|Y)
            echo "✅ Proceeding to execution..."
            break
            ;;
        n|N)
            user_feedback=$(collect_feedback "PROVIDE REFINEMENT FEEDBACK")
            
            if [[ -n "$user_feedback" ]]; then
                echo ""
                echo "🔄 Restarting refinement with your feedback..."
                
                plan_iteration=$((plan_iteration + 1))
                refined_plan="$WORKSPACE/plan-v${plan_iteration}.md"
                refine_prompt="$WORKSPACE/refine-prompt-iter${plan_iteration}.txt"
                
                if [[ -f "$COMMANDS_DIR/refine-plan.md" ]]; then
                    cat "$COMMANDS_DIR/refine-plan.md" > "$refine_prompt"
                else
                    cat > "$refine_prompt" << 'EOF'
# Refine Plan

Fix all issues. Preserve strengths.

Output the COMPLETE refined plan in markdown.
EOF
                fi
                
                # TOKEN OPTIMIZATION: Minimal context + user feedback
                echo -e "\n\n---\n# USER FEEDBACK (CRITICAL):\n$user_feedback\n" >> "$refine_prompt"
                echo -e "\n---\n# Score History:\n${score_history[*]}\n" >> "$refine_prompt"
                echo -e "\n---\n# Current Plan:\n" >> "$refine_prompt"
                cat "$final_plan" >> "$refine_prompt"
                
                cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$refine_prompt" > "$refined_plan" 2>&1
                
                refined_lines=$(wc -l < "$refined_plan")
                echo "✅ Plan refined with your feedback: $refined_lines lines"
                
                cp "$refined_plan" "$final_plan"
                
                # Quick critique
                critique_file="$WORKSPACE/plan-critique-iter${plan_iteration}.json"
                critique_prompt="$WORKSPACE/critique-prompt-iter${plan_iteration}.txt"
                
                if [[ -f "$COMMANDS_DIR/critique-plan.md" ]]; then
                    cat "$COMMANDS_DIR/critique-plan.md" > "$critique_prompt"
                fi
                
                echo -e "\n\n---\n# Plan to Critique:\n" >> "$critique_prompt"
                cat "$refined_plan" >> "$critique_prompt"
                
                cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$critique_prompt" > "$critique_file" 2>&1
                
                new_score=$(extract_score "$critique_file" "score")
                echo "📊 New Score: $new_score/10"
                
                if [[ "$new_score" != "N/A" ]]; then
                    best_score=$new_score
                fi
                
                continue
            else
                echo "⚠️  No feedback provided, keeping current plan"
                break
            fi
            ;;
        q|Q)
            echo "❌ Workflow stopped by user"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please enter y, n, or q"
            ;;
    esac
done

# ════════════════════════════════════════════════════════════════════
# TOKEN OPTIMIZATION: CREATE PLAN SUMMARY FOR EXECUTION
# ════════════════════════════════════════════════════════════════════

echo ""
echo "💾 TOKEN OPTIMIZATION: Creating plan summary for execution..."

plan_summary="$WORKSPACE/plan-summary.md"
plan_summary_prompt="$WORKSPACE/plan-summary-prompt.txt"

cat > "$plan_summary_prompt" << 'EOF'
# Compress Plan to Execution Summary

Extract ONLY the actionable steps - no explanations, rationale, or background.

## Format:
```
## Steps
1. File: path/to/file.tsx
   - Action: What to do
   - Key code: One-line reference

2. File: path/to/other.ts
   - Action: What to do
   - Key code: One-line reference

## Critical Details
- Constraint 1
- Constraint 2
```

Keep under 50 lines. Maximum brevity.

---

# Full Plan to Compress:

EOF

cat "$final_plan" >> "$plan_summary_prompt"

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$plan_summary_prompt" > "$plan_summary" 2>&1

plan_summary_lines=$(wc -l < "$plan_summary")
plan_original_size=$(wc -c < "$final_plan")
plan_summary_size=$(wc -c < "$plan_summary")
plan_reduction=$((100 - (plan_summary_size * 100 / plan_original_size)))

echo "✅ Compressed: $(wc -l < "$final_plan") lines → $plan_summary_lines lines ($plan_reduction% smaller)"
log "Token savings: Plan compressed from $plan_original_size to $plan_summary_size bytes"

# ═══════════════════════════════════════════════════════════════════
# PHASE 2: EXECUTION & REVIEW (FULLY AUTOMATED, TOKEN-OPTIMIZED)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "⚙️  PHASE 2: EXECUTION & REVIEW (TOKEN-OPTIMIZED)"
echo "════════════════════════════════════════════════════════════════"

# ───────────────────────────────────────────────────────────────────
# STEP 1: EXECUTION - WITH SUMMARIES
# ───────────────────────────────────────────────────────────────────

log "Phase 2: Executing implementation..."

execution_file="$WORKSPACE/execution-output.md"
execution_prompt="$WORKSPACE/execution-prompt.txt"

if [[ -f "$COMMANDS_DIR/execute-autonomous.md" ]]; then
    log "Using execute-autonomous.md"
    cat "$COMMANDS_DIR/execute-autonomous.md" > "$execution_prompt"
else
    cat > "$execution_prompt" << 'EOF'
# Execute Implementation

Implement the plan step-by-step.

For each step:
- Show actual code changes
- Verify it works
- Mark status (✅ Complete / ⚠️ Partial / ❌ Failed)

Provide complete, working implementation.
EOF
fi

# TOKEN OPTIMIZATION: Use summaries instead of full documents
echo -e "\n\n---\n# Task:\n$TASK\n" >> "$execution_prompt"
echo -e "\n---\n# Codebase Key Facts:\n" >> "$execution_prompt"
cat "$exploration_summary" >> "$execution_prompt"  # ← Summary, not full exploration
echo -e "\n---\n# Implementation Plan (Summary):\n" >> "$execution_prompt"
cat "$plan_summary" >> "$execution_prompt"  # ← Summary, not full plan

# Add past learnings (keep this - it's useful context)
if [[ -f "$LEARNING_LOG" ]]; then
    echo -e "\n---\n# Past Learnings (last 50 lines):\n" >> "$execution_prompt"
    tail -50 "$LEARNING_LOG" >> "$execution_prompt"
fi

# Reduce context files to first 30 lines each
if [[ -d "$CONTEXT_DIR" ]] && [[ $(ls -A "$CONTEXT_DIR" 2>/dev/null) ]]; then
    echo -e "\n---\n# Relevant Past Context (abbreviated):\n" >> "$execution_prompt"
    for context_file in "$CONTEXT_DIR"/*.md; do
        if [[ -f "$context_file" ]]; then
            echo -e "\n## $(basename "$context_file"):\n" >> "$execution_prompt"
            head -30 "$context_file" >> "$execution_prompt"  # ← Only 30 lines, not 50
        fi
    done
fi

cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$execution_prompt" > "$execution_file" 2>&1

exec_lines=$(wc -l < "$execution_file")
echo "├─ ✅ Execution Complete: $exec_lines lines"

# ───────────────────────────────────────────────────────────────────
# STEP 2: REVIEW LOOP - TOKEN OPTIMIZED
# ───────────────────────────────────────────────────────────────────

echo "├─ 🔍 Starting Review Loop (up to 3 rounds)..."

review_history="$WORKSPACE/review-history.md"
cat > "$review_history" << 'EOF'
# Review History (Scores Only)

EOF

current_implementation="$execution_file"
final_score="N/A"
final_issues=0

for round in 1 2 3; do
    echo "├─ 🔍 Review Round $round/3..."
    
    review_output="$WORKSPACE/review-round${round}.md"
    review_prompt="$WORKSPACE/review-prompt-round${round}.txt"
    
    if (( round == 3 )) && [[ -f "$COMMANDS_DIR/review-round2-autonomous.md" ]]; then
        log "Using review-round2-autonomous.md for final verification"
        cat "$COMMANDS_DIR/review-round2-autonomous.md" > "$review_prompt"
    elif [[ -f "$COMMANDS_DIR/review-autonomous.md" ]]; then
        log "Using review-autonomous.md"
        cat "$COMMANDS_DIR/review-autonomous.md" > "$review_prompt"
    else
        cat > "$review_prompt" << 'EOF'
# Review Implementation

Check implementation quality.

Output JSON:
{
  "quality_score": 8.5,
  "issues_found": 2,
  "critical_issues": [],
  "minor_issues": [],
  "fixes_required": []
}

Then provide detailed analysis with fix locations.
EOF
    fi
    
    # TOKEN OPTIMIZATION: Lightweight review history (scores only)
    echo -e "\n\n---\n# Review History:\n" >> "$review_prompt"
    cat "$review_history" >> "$review_prompt"
    
    # TOKEN OPTIMIZATION: Send implementation, but use plan summary
    echo -e "\n---\n# Implementation to Review:\n" >> "$review_prompt"
    cat "$current_implementation" >> "$review_prompt"
    echo -e "\n---\n# Original Plan (Summary):\n" >> "$review_prompt"
    cat "$plan_summary" >> "$review_prompt"  # ← Summary, not full plan
    
    cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$review_prompt" > "$review_output" 2>&1
    
    review_score=$(extract_score "$review_output" "quality_score")
    if [[ "$review_score" == "N/A" ]]; then
        review_score=$(extract_score "$review_output" "score")
    fi
    
    issues_found=$(extract_issues "$review_output" "issues_found")
    
    if [[ "$issues_found" =~ ^[0-9]+$ ]]; then
        : # already a number
    elif [[ "$issues_found" == "none" ]]; then
        issues_found=0
    else
        critical=$(extract_issues "$review_output" "critical_issues")
        minor=$(extract_issues "$review_output" "minor_issues")
        
        critical_count=0
        minor_count=0
        
        if [[ "$critical" != "none" ]]; then
            critical_count=$(echo "$critical" | tr ',' '\n' | grep -v '^[[:space:]]*$' | wc -l)
        fi
        
        if [[ "$minor" != "none" ]]; then
            minor_count=$(echo "$minor" | tr ',' '\n' | grep -v '^[[:space:]]*$' | wc -l)
        fi
        
        issues_found=$((critical_count + minor_count))
    fi
    
    echo "│  ├─ Score: $review_score/10"
    echo "│  └─ Issues Found: $issues_found"
    
    # Lightweight history
    cat >> "$review_history" << EOF
Round $round: $review_score/10 ($issues_found issues)
EOF
    
    final_score=$review_score
    final_issues=$issues_found
    
    # Early stopping
    if [[ $issues_found -eq 0 ]]; then
        echo "├─ ✅ No issues found - stopping review loop early"
        cat >> "$review_history" << EOF
Early stop: Round $round clean
EOF
        break
    fi
    
    # Apply fixes
    if [[ $issues_found -gt 0 ]]; then
        echo "│  ├─ 🔧 Fixing $issues_found issue(s)..."
        
        fixed_output="$WORKSPACE/execution-fixed-round${round}.md"
        fix_prompt="$WORKSPACE/fix-prompt-round${round}.txt"
        
        cat > "$fix_prompt" << EOF
# Fix Implementation Issues - Round $round

Apply ALL fixes identified in the review.

## Review Findings:
EOF
        cat "$review_output" >> "$fix_prompt"
        echo -e "\n---\n# Current Implementation:\n" >> "$fix_prompt"
        cat "$current_implementation" >> "$fix_prompt"
        
        cat >> "$fix_prompt" << 'EOF'

## Instructions

1. Fix ALL critical issues completely
2. Fix ALL minor issues
3. Don't break working code
4. Verify each fix
5. Update documentation

Output the COMPLETE fixed implementation (not diffs).
EOF
        
        cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$fix_prompt" > "$fixed_output" 2>&1
        
        current_implementation="$fixed_output"
        echo "│  └─ ✅ Fixes applied"
    fi
done

echo "└─ ✅ Phase 2 Complete"
echo ""
echo "   📊 Review Summary:"
echo "      ├─ Rounds Completed: $round/3"
echo "      ├─ Final Score: $final_score/10"
echo "      └─ Final Issues: $final_issues"

# ═══════════════════════════════════════════════════════════════════
# PHASE 3: LEARNING & CONTEXT CAPTURE (TOKEN-OPTIMIZED)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📚 PHASE 3: CAPTURE LEARNINGS & CONTEXT"
echo "════════════════════════════════════════════════════════════════"

log "Phase 3: Capturing learnings..."

if [[ -f "$COMMANDS_DIR/lessons.md" ]]; then
    log "Extracting lessons using lessons.md"
    
    lessons_prompt="$WORKSPACE/lessons-prompt.txt"
    cat "$COMMANDS_DIR/lessons.md" > "$lessons_prompt"
    
    echo -e "\n\n---\n# Task Completed:\n$TASK\n" >> "$lessons_prompt"
    
    # TOKEN OPTIMIZATION: Send last 100 lines of implementation (not full)
    echo -e "\n---\n# Execution Output (Final Section):\n" >> "$lessons_prompt"
    tail -100 "$current_implementation" >> "$lessons_prompt"
    
    echo -e "\n---\n# Review Summary:\n" >> "$lessons_prompt"
    cat "$review_history" >> "$lessons_prompt"
    
    lessons_output="$WORKSPACE/lessons-learned.md"
    cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$lessons_prompt" > "$lessons_output" 2>&1
    
    echo "" >> "$LEARNING_LOG"
    echo "## $(date '+%Y-%m-%d %H:%M:%S') - $TASK" >> "$LEARNING_LOG"
    cat "$lessons_output" >> "$LEARNING_LOG"
    echo "" >> "$LEARNING_LOG"
    
    echo "✅ Lessons appended to: $LEARNING_LOG"
fi

if [[ -f "$COMMANDS_DIR/context.md" ]]; then
    log "Saving context using context.md"
    
    context_prompt="$WORKSPACE/context-prompt.txt"
    cat "$COMMANDS_DIR/context.md" > "$context_prompt"
    
    echo -e "\n\n---\n# Task:\n$TASK\n" >> "$context_prompt"
    echo -e "\n---\n# Key Files:\n" >> "$context_prompt"
    cat "$exploration_summary" >> "$context_prompt"  # ← Summary, not full
    echo -e "\n---\n# Implementation (First 50 lines):\n" >> "$context_prompt"
    head -50 "$current_implementation" >> "$context_prompt"  # ← 50 lines, not 100
    
    context_output="$WORKSPACE/context-summary.md"
    cursor agent --model "${AI_MODEL:-Composer 1.5}" < "$context_prompt" > "$context_output" 2>&1
    
    mkdir -p "$CONTEXT_DIR"
    
    context_filename="$CONTEXT_DIR/${SHORT_DESC}_${TIMESTAMP}.md"
    cp "$context_output" "$context_filename"
    
    echo "✅ Context saved to: $context_filename"
fi

# ═══════════════════════════════════════════════════════════════════
# COMPLETION SUMMARY WITH TOKEN STATS
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ TOKEN-OPTIMIZED WORKFLOW COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Phase 0 - Issue & Exploration:"
echo "   - Issue: $issue_lines lines"
echo "   - Exploration: $exploration_lines lines → $summary_lines lines ($reduction% reduction)"
echo ""
echo "📋 Phase 1 - Plan Refinement:"
echo "   - Iterations: $plan_iteration"
echo "   - Score Progression: ${score_history[*]}"
echo "   - Final Score: $best_score/10"
echo "   - Plan: $(wc -l < "$final_plan") lines → $plan_summary_lines lines ($plan_reduction% reduction)"
echo ""
echo "⚙️  Phase 2 - Execution & Review:"
echo "   - Execution: $exec_lines lines"
echo "   - Review Rounds: $round/3"
echo "   - Final Score: $final_score/10"
echo "   - Final Issues: $final_issues"
echo ""
echo "💾 Token Optimization Summary:"
echo "   - Exploration compressed: $reduction%"
echo "   - Plan compressed: $plan_reduction%"
echo "   - Refinement context: Minimal (scores + current plan + latest critique only)"
echo "   - Execution context: Summaries only (not full documents)"
echo "   - Review context: Lightweight history"
echo "   - Estimated total savings: ~70-80% in Phase 0&1"
echo ""
echo "📁 Workspace: $WORKSPACE"
echo "════════════════════════════════════════════════════════════════"

log "Token-optimized workflow completed successfully"