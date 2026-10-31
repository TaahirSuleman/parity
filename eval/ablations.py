"""The ablation table: full Parity, screenshot only, tree only, no grounding (spec §13).

Thin wrapper over the harness: `.venv/bin/python -m eval.ablations --runs 3` is `eval.harness --ablations --runs 3`.
"""

import sys

from eval.harness import main

if __name__ == "__main__":
    sys.exit(main(["--ablations", *sys.argv[1:]]))
