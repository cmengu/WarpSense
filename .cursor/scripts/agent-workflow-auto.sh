#!/bin/bash
set -e

TASK="${1:?Error: Provide task description}"
TIMESTAMP=$(date +%s)
WORKSPACE=".cursor/agents/task_${TIMESTAMP}"
COMMANDS_DIR=".cursor/commands"

mkdir -p "$WORKSPACE"
echo "$TASK" > "$WORKSPACE/task.txt"

echo "🚀 Using Composer 1.5"
echo "📁 Workspace: $WORKSPACE"
echo ""

run_agent() {
    cursor agent --model "Composer 1.5" --print --trust "$@"
}

echo "═══ PHASE 1: PLANNING ═══"

echo "[1/3] Creating issue..."
cat "$COMMANDS_DIR/create-issue.md" > "$WORKSPACE/prompt.txt"
echo "" >> "$WORKSPACE/prompt.txt"
echo "Task: $TASK" >> "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/create-issue-output.md" 2>&1
echo "✅ Done"

echo "[2/3] Exploring..."
cat "$COMMANDS_DIR/explore.md" > "$WORKSPACE/prompt.txt"
echo "" >> "$WORKSPACE/prompt.txt"
echo "Task: $TASK" >> "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/explore-output.md" 2>&1
echo "✅ Done"

echo "[3/3] Creating plan..."
cat "$COMMANDS_DIR/create-plan.md" > "$WORKSPACE/prompt.txt"
echo "" >> "$WORKSPACE/prompt.txt"
echo "Task: $TASK" >> "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/create-plan-output.md" 2>&1
echo "✅ Done"

echo ""
echo "═══ PHASE 2: EXECUTION ═══"

echo "[1/6] Executing..."
cat "$COMMANDS_DIR/execute.md" > "$WORKSPACE/prompt.txt"
echo "" >> "$WORKSPACE/prompt.txt"
echo "Task: $TASK" >> "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/execute-output.md" 2>&1
echo "✅ Done"

echo "[2/6] Reviewing..."
cat "$COMMANDS_DIR/review.md" > "$WORKSPACE/prompt.txt"
echo "" >> "$WORKSPACE/prompt.txt"
echo "Task: $TASK" >> "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/review-round1-output.md" 2>&1
echo "✅ Done"

echo "[3/6] Fixing..."
echo "Fix all HIGH and MEDIUM priority issues." > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/fix-round1-output.md" 2>&1
echo "✅ Done"

echo "[4/6] Reviewing..."
echo "Review code after fixes." > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/review-round2-output.md" 2>&1
echo "✅ Done"

echo "[5/6] Fixing..."
echo "Fix remaining issues." > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/fix-round2-output.md" 2>&1
echo "✅ Done"

echo "[6/6] Final review..."
echo "Create final summary." > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/final-review-output.md" 2>&1
echo "✅ Done"

echo ""
echo "═══ PHASE 3: LEARNING ═══"

echo "[1/2] Lessons..."
cat "$COMMANDS_DIR/lessons.md" > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/lessons-output.md" 2>&1
echo "✅ Done"

echo "[2/2] Context..."
cat "$COMMANDS_DIR/context.md" > "$WORKSPACE/prompt.txt"
run_agent < "$WORKSPACE/prompt.txt" > "$WORKSPACE/context-output.md" 2>&1
echo "✅ Done"

echo ""
echo "✅ COMPLETE: $WORKSPACE"
rm -f "$WORKSPACE/prompt.txt"
