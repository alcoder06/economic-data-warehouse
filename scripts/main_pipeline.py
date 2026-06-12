import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

STEP_SCRIPTS = {
    "download": "download_data.py",
    "metadata": "download_metadata.py",
    "transform": "transform_data.py",
    "gold": "gold_transform.py",
    "validate": "validate_data.py",
}


def run_step(script_name: str) -> None:
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print(f"\n=== Running {script_name} ===")

    result = subprocess.run([sys.executable, script_path], cwd=BASE_DIR)
    if result.returncode != 0:
        raise SystemExit(f"{script_name} failed with exit code {result.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Uzbekistan economic pipeline steps."
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=list(STEP_SCRIPTS.keys()) + ["all"],
        default=["all"],
        help="Pipeline steps to execute.",
    )
    args = parser.parse_args()

    if "all" in args.steps:
        steps = ["download", "metadata", "transform", "gold", "validate"]
    else:
        steps = args.steps

    for step in steps:
        run_step(STEP_SCRIPTS[step])

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
