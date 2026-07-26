#!/bin/bash
# evo_eval.sh — Wrapper for evo trajectory evaluation (ATE + RPE)
# Usage:
#    evo_eval.sh <groundtruth.txt> <estimate.txt> <output_prefix>
# Example:
#    evo_eval.sh MH_01_gt.txt CameraTrajectory.txt results/mh01
# Output:
#    <prefix>_ate.png, <prefix>_rpe.png, terminal summary

set -euo pipefail

GT="$1"
EST="$2"
PREFIX="${3:-results/eval}"

if [[ ! -f "$GT" ]]; then
    echo "ERROR: groundtruth file not found: $GT"
    exit 1
fi
if [[ ! -f "$EST" ]]; then
    echo "ERROR: estimate file not found: $EST"
    exit 1
fi

echo "=== ATE (Absolute Trajectory Error) ==="
evo_ape tum "$GT" "$EST" -va --plot --plot_mode xy \
    --save_plot "${PREFIX}_ate.png"

echo ""
echo "=== RPE (Relative Pose Error) ==="
evo_rpe tum "$GT" "$EST" -va --plot --plot_mode xy \
    --save_plot "${PREFIX}_rpe.png" \
    --delta 1 --delta_unit f

echo ""
echo "Plots saved: ${PREFIX}_ate.png, ${PREFIX}_rpe.png"
echo "Done."
