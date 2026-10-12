"""Run the full comparison grid: 3 chunkers x 3 retrieval modes. Paste eval/results.md into the README."""
import subprocess
import sys

for strategy in ("fixed", "sentence", "structure"):
    for mode in ("vector", "keyword", "hybrid"):
        subprocess.run([sys.executable, "-m", "eval.run_eval", "--strategy", strategy, "--mode", mode], check=True)
