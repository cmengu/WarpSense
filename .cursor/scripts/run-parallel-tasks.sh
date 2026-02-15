#!/bin/bash
# run-parallel-tasks.sh
# Launch multiple agent workflows in parallel (simple approach)

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <task1> <task2> <task3> ..."
    echo ""
    echo "Examples:"
    echo "  $0 'Add auth' 'Build API' 'Create dashboard'"
    echo "  $0 'Task 1' 'Task 2' 'Task 3' 'Task 4' 'Task 5'"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔════════════════════════════════════════╗"
echo "║   LAUNCHING PARALLEL AGENT WORKFLOWS   ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📊 Tasks to process: $#"
echo ""

# Array to track background PIDs
declare -a pids

# Launch each task in background
task_num=0
for task in "$@"; do
    task_num=$((task_num + 1))
    echo "🚀 Starting task $task_num: $task"
    
    # Launch in background with full path
    "$SCRIPT_DIR/agent-workflow-auto.sh" "$task" > ".cursor/agents/task_${task_num}_$(date +%s).log" 2>&1 &
    
    # Store PID
    pids+=($!)
    
    # Small delay to avoid race conditions
    sleep 1
done

echo ""
echo "✅ Launched $task_num workflows in parallel"
echo ""
echo "📊 Monitoring progress..."
echo "   PIDs: ${pids[*]}"
echo ""
echo "⏳ Waiting for all tasks to complete..."
echo "   (You can Ctrl+C to detach - tasks will continue running)"
echo ""

# Wait for all background jobs
for pid in "${pids[@]}"; do
    wait $pid
    echo "✅ Task with PID $pid completed"
done

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   🎉 ALL TASKS COMPLETE! 🎉            ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📁 Check outputs in: .cursor/agents/"
echo ""
