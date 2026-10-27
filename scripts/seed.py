"""Generate fake users with a fixed seed. Never use real data."""
import json
import random

rng = random.Random(42)
names = ["ada", "grace", "linus", "barbara", "ken", "margaret"]
users = [{"id": i, "name": rng.choice(names), "email": f"user{i}@example.com"} for i in range(10)]
print(json.dumps(users, indent=2))
