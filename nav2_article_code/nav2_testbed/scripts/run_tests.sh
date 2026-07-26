#!/bin/bash
# Batch test runner for Nav2 algorithm comparison
# Run this after sourcing ROS2: source /opt/ros/humble/setup.bash

TESTBED="$HOME/nav2_article_code/nav2_testbed"
RESULTS="$TESTBED/results"
mkdir -p "$RESULTS"

MAZE_GOAL_X=-2
MAZE_GOAL_Y=3

declare -a TESTS=(
    "T01 maze config1 $MAZE_GOAL_X $MAZE_GOAL_Y"
    "T02 maze smac_rpp $MAZE_GOAL_X $MAZE_GOAL_Y"
    "T03 maze smac_mppi $MAZE_GOAL_X $MAZE_GOAL_Y"
    "T04 maze hybrid_rpp $MAZE_GOAL_X $MAZE_GOAL_Y"
)

run_test() {
    local tid=$1 world=$2 params=$3 gx=$4 gy=$5
    local LOGFILE="/tmp/nav2_test_output_${tid}.log"

    echo ""
    echo "================================================================"
    echo "  $tid: world=$world params=$params goal=($gx,$gy)"
    echo "================================================================"

    # --- Cleanup ---
    echo "[run_tests] Cleaning up..."
    bash "$TESTBED/scripts/cleanup.sh" || true
    sleep 2

    # --- Launch simulation ---
    echo "[run_tests] Launching simulation..."
    ros2 launch "$TESTBED/launch/testbed.launch.py" \
        world:="$TESTBED/worlds/$world.world" \
        map:="$TESTBED/maps/$world.yaml" \
        params:="$TESTBED/params/$params.yaml" \
        headless:=False \
        > "$LOGFILE" 2>&1 &
    LAUNCH_PID=$!
    echo "[run_tests] Launch PID: $LAUNCH_PID"

    # --- Wait for navigation stack (rclpy-based check, avoids daemon issue) ---
    echo "[run_tests] Waiting for Nav2 action server (max 90s)..."
    if timeout 100 python3 "$TESTBED/scripts/wait_for_nav.py" 90 2>/dev/null; then
        echo "[run_tests] Navigation stack ready!"
    else
        echo "[run_tests] TIMEOUT: navigation stack not ready after 90s"
        echo "$tid,$world,$params,TIMEOUT_STARTUP,0,0" >> "$RESULTS/summary.csv"
        kill $LAUNCH_PID 2>/dev/null || true
        wait $LAUNCH_PID 2>/dev/null || true
        bash "$TESTBED/scripts/cleanup.sh" || true
        sleep 3
        return
    fi

    # --- Wait for AMCL convergence ---
    echo "[run_tests] Waiting for AMCL convergence (15s)..."
    sleep 15

    # --- Send goal ---
    echo "[run_tests] Sending goal ($gx, $gy)..."
    local GOAL_OUTPUT
    GOAL_OUTPUT=$(timeout 180 python3 "$TESTBED/scripts/send_goal.py" "$gx" "$gy" 2>&1)
    local GOAL_EXIT=$?
    echo "[run_tests] send_goal exit=$GOAL_EXIT output: $GOAL_OUTPUT"

    # Extract CSV line
    local CSV_LINE
    if [ $GOAL_EXIT -eq 0 ] || [ $GOAL_EXIT -eq 1 ]; then
        CSV_LINE=$(echo "$GOAL_OUTPUT" | grep -E '^(SUCCESS|FAILED|INTERRUPTED)' | tail -1)
    elif [ $GOAL_EXIT -eq 124 ]; then
        CSV_LINE="TIMEOUT,0,0"
    else
        CSV_LINE="ERROR_${GOAL_EXIT},0,0"
    fi
    [ -z "$CSV_LINE" ] && CSV_LINE="UNKNOWN,0,0"
    echo "$tid,$world,$params,$CSV_LINE" >> "$RESULTS/summary.csv"

    # --- Cleanup ---
    echo "[run_tests] Cleaning up after test..."
    kill $LAUNCH_PID 2>/dev/null || true
    wait $LAUNCH_PID 2>/dev/null || true
    bash "$TESTBED/scripts/cleanup.sh" || true
    sleep 3
}

# Main loop
for test in "${TESTS[@]}"; do
    run_test $test
done

echo ""
echo "===== All tests complete ====="
echo ""
cat "$RESULTS/summary.csv"
echo ""
echo "Results saved to $RESULTS/summary.csv"
echo "Launch logs saved to /tmp/nav2_test_output_*.log"
