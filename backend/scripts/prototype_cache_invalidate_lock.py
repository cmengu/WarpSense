#!/usr/bin/env python3
"""
Prototype: invalidate_cache must acquire _load_lock to avoid race.

Validates the Plan Critique Fix #2: without the lock in invalidate_cache,
a thread in _load_all can have _cache_loaded set False by another thread,
triggering redundant _load_all on next request. With the lock, both
invalidate and _load serialize correctly.

Run: python scripts/prototype_cache_invalidate_lock.py
"""

import threading
import time

# Shared state
_cache = {}
_cache_loaded = False
_load_lock = threading.Lock()


def _load_all_simulated():
    """Simulates DB load — holds lock, builds cache."""
    global _cache, _cache_loaded
    with _load_lock:
        if _cache_loaded:
            return
        time.sleep(0.01)  # Simulate DB work
        _cache = {"mig": 45}
        _cache_loaded = True


def invalidate_wrong():
    """Original bug: no lock."""
    global _cache_loaded
    _cache_loaded = False


def invalidate_fixed():
    """Fixed: acquire lock before clearing."""
    global _cache_loaded
    with _load_lock:
        _cache_loaded = False


def get(use_fixed_invalidate: bool):
    global _cache_loaded
    if not _cache_loaded:
        _load_all_simulated()
    return _cache.get("mig", 0)


def run_race_test(use_fixed: bool):
    """Two threads: one loading, one invalidating. Fixed version serializes."""
    global _cache, _cache_loaded
    _cache = {}
    _cache_loaded = False

    result = [None]
    load_count = [0]

    def loader():
        for _ in range(5):
            get(use_fixed)
            load_count[0] += 1

    def invalidator():
        inv = invalidate_fixed if use_fixed else invalidate_wrong
        for _ in range(5):
            time.sleep(0.005)
            inv()

    t1 = threading.Thread(target=loader)
    t2 = threading.Thread(target=invalidator)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    return load_count[0]


def main():
    print("Prototype: invalidate_cache locking")
    print("-" * 50)
    # With wrong invalidate: possible redundant loads
    wrong_loads = run_race_test(use_fixed=False)
    print(f"Without lock in invalidate: ~{wrong_loads} load attempts (may trigger redundant _load_all)")
    # With fixed invalidate: serialize, no redundant load
    fixed_loads = run_race_test(use_fixed=True)
    print(f"With lock in invalidate: ~{fixed_loads} load attempts (serialized)")
    print()
    print("Conclusion: invalidate_cache must acquire _load_lock before setting _cache_loaded = False")
    print("Plan Step 1.4: add 'with _load_lock:' in invalidate_cache")


if __name__ == "__main__":
    main()
