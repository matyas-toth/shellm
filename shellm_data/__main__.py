import argparse
import json

from .core import build, validate

parser = argparse.ArgumentParser(description="Build/check/validate a versioned shell translation dataset")
parser.add_argument("action", choices=("build", "validate"))
parser.add_argument("--release", default="pilot-v1")
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
print(json.dumps(build(args.release, args.check) if args.action == "build" else validate(args.release), indent=2))
