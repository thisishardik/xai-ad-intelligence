#!/usr/bin/env python3
"""
Visualize simulated CTR comparisons between original and enhanced creatives.

Usage:
    python visualize_ctr_results.py path/to/ctr_comparison.json --output chart.png
    # If no --output is provided, the chart opens in a window.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Any

import matplotlib.pyplot as plt


def load_comparison(path: Path) -> List[Dict[str, Any]]:
    """Load CTR comparison data from JSON or CSV."""
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # Coerce numeric fields
        for row in rows:
            for key in ["variant", "original_score", "enhanced_score", "winner_score"]:
                if key in row and row[key] not in (None, ""):
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        row[key] = None
        return rows
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # If the JSON is wrapped, pick common keys
    if isinstance(data, dict):
        for key in ["data", "rows", "ctr_comparison", "comparisons"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    
    return data if isinstance(data, list) else []


def plot_comparison(data: List[Dict[str, Any]], output: Path | None = None) -> None:
    """Render bar chart comparing original vs enhanced simulated CTR scores."""
    if not data:
        print("No CTR comparison data found.")
        return
    
    labels = [f"Var {int(row.get('variant', idx + 1))}" for idx, row in enumerate(data)]
    original = [float(row.get("original_score") or 0) for row in data]
    enhanced = [float(row.get("enhanced_score") or 0) for row in data]
    
    x = range(len(data))
    width = 0.38
    
    fig, ax = plt.subplots(figsize=(max(6, len(data) * 1.4), 4.8))
    
    ax.bar([i - width / 2 for i in x], original, width, label="Original")
    ax.bar([i + width / 2 for i in x], enhanced, width, label="Enhanced")
    
    ax.set_ylabel("Predicted CTR score")
    ax.set_title("Simulated CTR: Original vs Enhanced")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    
    for i, (orig, enh) in enumerate(zip(original, enhanced)):
        ax.text(i - width / 2, orig + 0.5, f"{orig:.1f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + width / 2, enh + 0.5, f"{enh:.1f}", ha="center", va="bottom", fontsize=8)
    
    fig.tight_layout()
    
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=150)
        print(f"Saved chart to {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Visualize simulated CTR comparisons (original vs enhanced)."
    )
    parser.add_argument(
        "input",
        help="Path to *_ctr_comparison.json or *_ctr_comparison.csv produced by the pipeline"
    )
    parser.add_argument(
        "--output",
        help="Optional path to save the chart image (e.g., out.png). If omitted, the chart is shown."
    )
    
    args = parser.parse_args()
    input_path = Path(args.input)
    
    if not input_path.exists():
        raise FileNotFoundError(f"CTR comparison file not found: {input_path}")
    
    data = load_comparison(input_path)
    plot_comparison(data, Path(args.output) if args.output else None)


if __name__ == "__main__":
    main()
