#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# PLAN REFINER - Autonomous Quality Improvement with Smart Looping
# ═══════════════════════════════════════════════════════════════════
# 
# Usage: ./plan-refiner.sh <input_plan.md> [max_iterations] [target_score]
# 
# Returns: Exit 0 if refinement successful, 1 if failed
# ═══════════════════════════════════════════════════════════════════

PLAN_FILE="${1:?Error: Provide plan file path}"
MAX_ITERATIONS="${2:-5}"
TARGET_SCORE="${3:-9.0}"
COMMANDS_DIR="${COMMANDS_DIR:-.cursor/commands}"
AI_MODEL="${AI_MODEL:-Composer 1.5}"

# Validate inputs
if [[ ! -f "$PLAN_FILE" ]]; then
    echo "❌ Error: Plan file not found: $PLAN_FILE"
    exit 1
fi

# Validate command files exist
required_files=(
    "$COMMANDS_DIR/critique-plan.md"
    "$COMMANDS_DIR/refine-plan.md"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "⚠️  Warning: Required prompt file not found: $file"
        echo "    The script will try to continue but may not work correctly."
    fi
done

# Setup workspace
WORKSPACE=".cursor/plan-refinement-$(date +%s)"
mkdir -p "$WORKSPACE"
HISTORY_FILE="$WORKSPACE/iteration-history.md"

# Initialize history
cat > "$HISTORY_FILE" << 'EOF'
# Plan Refinement History

This tracks all iterations and learnings for continuous improvement.

## Goal
- Target Score: 9.0/10
- Max Iterations: 5

---

EOF

# Logging
log() {
    echo "[$(date +'%H:%M:%S')] $*" | tee -a "$WORKSPACE/refiner.log"
}

# Extract score (macOS compatible)
extract_score() {
    local file="$1"
    local pattern="${2:-score}"
    
    # Method 1: Try JSON extraction with jq
    if command -v jq &> /dev/null; then
        local json=$(sed -n '/^{/,/^}/p' "$file" | tr -d '\n')
        if [[ -n "$json" ]]; then
            local score=$(echo "$json" | jq -r ".${pattern} // empty" 2>/dev/null)
            if [[ -n "$score" && "$score" != "null" ]]; then
                echo "$score"
                return 0
            fi
        fi
    fi
    
    # Method 2: Pattern matching
    local score=$(grep -oiE "(${pattern}|quality).*[0-9]+\.?[0-9]*/10" "$file" | \
                  grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [[ -n "$score" ]]; then
        echo "$score"
        return 0
    fi
    
    # Method 3: Standalone number/10
    score=$(grep -oE '[0-9]+\.?[0-9]*/10' "$file" | \
            grep -oE '[0-9]+\.?[0-9]*' | head -1)
    
    if [[ -n "$score" ]]; then
        echo "$score"
        return 0
    fi
    
    echo "N/A"
}

# Extract issues (macOS compatible)
extract_issues() {
    local file="$1"
    local issue_type="$2"
    
    if command -v jq &> /dev/null; then
        local json=$(sed -n '/^{/,/^}/p' "$file" | tr -d '\n')
        if [[ -n "$json" ]]; then
            local result=$(echo "$json" | jq -r ".${issue_type}[]? // empty" 2>/dev/null | paste -sd ", " -)
            if [[ -n "$result" ]]; then
                echo "$result"
                return 0
            fi
        fi
    fi
    
    # Fallback: use sed (macOS compatible)
    sed -n "s/.*\"${issue_type}\"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p" "$file" | head -1 || echo "none"
}

# ═══════════════════════════════════════════════════════════════════
# MAIN REFINEMENT LOOP
# ═══════════════════════════════════════════════════════════════════

log "Starting plan refinement for: $PLAN_FILE"
log "Target: $TARGET_SCORE/10 in max $MAX_ITERATIONS iterations"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📋 AUTONOMOUS PLAN REFINEMENT"
echo "════════════════════════════════════════════════════════════════"
echo "Input: $PLAN_FILE"
echo "Target Score: $TARGET_SCORE/10"
echo "Max Iterations: $MAX_ITERATIONS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Copy initial plan
current_plan="$WORKSPACE/plan-v0.md"
cp "$PLAN_FILE" "$current_plan"
initial_lines=$(wc -l < "$current_plan")

iteration=0
best_score=0
no_improvement_count=0
plateau_threshold=3

while (( iteration < MAX_ITERATIONS )); do
    iteration=$((iteration + 1))
    
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "🔄 ITERATION $iteration/$MAX_ITERATIONS"
    echo "════════════════════════════════════════════════════════════════"
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: CRITIQUE - Use actual critique-plan.md
    # ═══════════════════════════════════════════════════════════════
    
    log "Critiquing plan (iteration $iteration)..."
    
    critique_file="$WORKSPACE/critique-iter${iteration}.json"
    critique_prompt="$WORKSPACE/critique-prompt-iter${iteration}.txt"
    
    # Build prompt with critique-plan.md + context
    if [[ -f "$COMMANDS_DIR/critique-plan.md" ]]; then
        cat "$COMMANDS_DIR/critique-plan.md" > "$critique_prompt"
    else
        echo "⚠️  critique-plan.md not found, using fallback prompt"
        cat > "$critique_prompt" << 'EOF'
# Plan Quality Analysis

Analyze this plan and provide a quality score (0-10).

## Required Output Format

Start with this EXACT JSON (no markdown, no code blocks):

{
  "score": 7.5,
  "critical_issues": ["issue 1"],
  "minor_issues": ["issue 1"],
  "strengths": ["strength 1"],
  "reasoning": "Explanation of score",
  "improvement_priority": ["fix 1"]
}

Then provide detailed analysis.
EOF
    fi
    
    # Add context
    echo -e "\n\n---\n# Context from Previous Iterations:\n" >> "$critique_prompt"
    cat "$HISTORY_FILE" >> "$critique_prompt"
    
    echo -e "\n---\n# Plan to Analyze:\n" >> "$critique_prompt"
    cat "$current_plan" >> "$critique_prompt"
    
    cursor agent --model "$AI_MODEL" < "$critique_prompt" > "$critique_file" 2>&1
    
    # Extract results
    current_score=$(extract_score "$critique_file" "score")
    critical_issues=$(extract_issues "$critique_file" "critical_issues")
    minor_issues=$(extract_issues "$critique_file" "minor_issues")
    strengths=$(extract_issues "$critique_file" "strengths")
    
    echo "📊 Critique Results:"
    echo "   Score: $current_score/10 (Best so far: $best_score/10)"
    echo "   Critical Issues: $critical_issues"
    echo "   Minor Issues: $minor_issues"
    
    # Update history
    cat >> "$HISTORY_FILE" << EOF

## Iteration $iteration - Critique
- **Score**: $current_score/10
- **Critical Issues**: $critical_issues
- **Minor Issues**: $minor_issues
- **Strengths**: $strengths
- **Lines**: $(wc -l < "$current_plan")

EOF
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: CHECK STOPPING CONDITIONS
    # ═══════════════════════════════════════════════════════════════
    
    if [[ "$current_score" != "N/A" ]]; then
        target_achieved=$(echo "$current_score >= $TARGET_SCORE" | bc -l 2>/dev/null || echo 0)
        
        if (( target_achieved )); then
            echo ""
            echo "✅ SUCCESS: Target score achieved!"
            echo "   Score: $current_score/10 (target: $TARGET_SCORE/10)"
            echo "   Iterations: $iteration"
            break
        fi
        
        score_improved=$(echo "$current_score > $best_score" | bc -l 2>/dev/null || echo 0)
        
        if (( score_improved )); then
            improvement=$(echo "$current_score - $best_score" | bc -l)
            echo "📈 Improved by $improvement points"
            best_score=$current_score
            no_improvement_count=0
        else
            no_improvement_count=$((no_improvement_count + 1))
            echo "⚠️  No improvement (stalled for $no_improvement_count iteration(s))"
            
            if (( no_improvement_count >= plateau_threshold )); then
                echo ""
                echo "🛑 STOPPING: Plateau detected"
                echo "   No improvement for $plateau_threshold iterations"
                echo "   Best score: $best_score/10"
                break
            fi
        fi
    else
        echo "⚠️  Warning: Could not extract score - continuing anyway"
    fi
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: REFINE - Use actual refine-plan.md
    # ═══════════════════════════════════════════════════════════════
    
    log "Refining plan based on critique..."
    
    refined_plan="$WORKSPACE/plan-v${iteration}.md"
    refine_prompt="$WORKSPACE/refine-prompt-iter${iteration}.txt"
    
    # Build prompt with refine-plan.md + context
    if [[ -f "$COMMANDS_DIR/refine-plan.md" ]]; then
        cat "$COMMANDS_DIR/refine-plan.md" > "$refine_prompt"
    else
        echo "⚠️  refine-plan.md not found, using fallback prompt"
        cat > "$refine_prompt" << 'EOF'
# Plan Refinement

Fix all critical issues identified in the critique.

Output the COMPLETE refined plan in markdown format.
EOF
    fi
    
    # Add context
    echo -e "\n\n---\n# Refinement History:\n" >> "$refine_prompt"
    cat "$HISTORY_FILE" >> "$refine_prompt"
    
    echo -e "\n---\n# Current Plan:\n" >> "$refine_prompt"
    cat "$current_plan" >> "$refine_prompt"
    
    echo -e "\n---\n# Critique Results:\n" >> "$refine_prompt"
    cat "$critique_file" >> "$refine_prompt"
    
    cursor agent --model "$AI_MODEL" < "$refine_prompt" > "$refined_plan" 2>&1
    
    refined_lines=$(wc -l < "$refined_plan")
    change=$(( refined_lines - $(wc -l < "$current_plan") ))
    change_display="${change}"
    if (( change > 0 )); then
        change_display="+${change}"
    fi
    
    echo "📄 Refinement Complete:"
    echo "   Lines: $(wc -l < "$current_plan") → $refined_lines ($change_display)"
    
    # Update history
    cat >> "$HISTORY_FILE" << EOF
### Refinement Applied
- **Line delta**: $change_display
- **Next**: Re-critique to verify improvements

EOF
    
    # Update current plan for next iteration
    current_plan="$refined_plan"
    
    log "Iteration $iteration complete"
done

# ═══════════════════════════════════════════════════════════════════
# FINALIZATION
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ REFINEMENT COMPLETE"
echo "════════════════════════════════════════════════════════════════"

final_plan="$WORKSPACE/plan-final.md"
cp "$current_plan" "$final_plan"

# Generate summary
summary_file="$WORKSPACE/refinement-summary.md"
cat > "$summary_file" << EOF
# Plan Refinement Summary

## Results
- **Iterations**: $iteration/$MAX_ITERATIONS
- **Initial Score**: N/A (baseline)
- **Final Score**: $best_score/10
- **Target Score**: $TARGET_SCORE/10
- **Status**: $(if (( $(echo "$best_score >= $TARGET_SCORE" | bc -l 2>/dev/null || echo 0) )); then echo "✅ Target Achieved"; else echo "⚠️ Partially Improved"; fi)

## Metrics
- **Initial Length**: $initial_lines lines
- **Final Length**: $(wc -l < "$final_plan") lines
- **Change**: $(($(wc -l < "$final_plan") - initial_lines)) lines

## Improvement Trajectory
EOF

# Add iteration scores
for ((i=1; i<=iteration; i++)); do
    iter_score=$(extract_score "$WORKSPACE/critique-iter${i}.json" "score")
    echo "- Iteration $i: $iter_score/10" >> "$summary_file"
done

cat >> "$summary_file" << EOF

## Final Plan Location
\`$final_plan\`

## Full History
See: \`$HISTORY_FILE\`

## All Artifacts
- Workspace: \`$WORKSPACE\`
- Critiques: \`$WORKSPACE/critique-iter*.json\`
- Versions: \`$WORKSPACE/plan-v*.md\`
EOF

echo ""
echo "📊 Summary:"
echo "   Iterations: $iteration/$MAX_ITERATIONS"
echo "   Best Score: $best_score/10 (target: $TARGET_SCORE/10)"
echo "   Initial: $initial_lines lines → Final: $(wc -l < "$final_plan") lines"
echo ""
echo "📁 Output Files:"
echo "   Final Plan: $final_plan"
echo "   Summary: $summary_file"
echo "   History: $HISTORY_FILE"
echo "   Workspace: $WORKSPACE"
echo ""

# Copy final plan back to original location if requested
read -p "📋 Copy refined plan back to $PLAN_FILE? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp "$final_plan" "$PLAN_FILE"
    echo "✅ Updated: $PLAN_FILE"
fi

log "Refinement completed successfully"

# Exit with appropriate code
if (( $(echo "$best_score >= $TARGET_SCORE" | bc -l 2>/dev/null || echo 0) )); then
    exit 0
else
    exit 1
fi