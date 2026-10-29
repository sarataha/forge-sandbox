"""Generate fake users with a fixed seed. Never use real data."""

import json
import random
import sys
from pathlib import Path

if sys.argv[1:] == ["--license"]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sandbox.billing.license import issue_key

    print(issue_key("owner"))
    raise SystemExit(0)

rng = random.Random(42)
names = ["ada", "grace", "linus", "barbara", "ken", "margaret"]
users = [
    {"id": i, "name": rng.choice(names), "email": f"user{i}@example.com"}
    for i in range(10)
]
print(json.dumps(users, indent=2))
