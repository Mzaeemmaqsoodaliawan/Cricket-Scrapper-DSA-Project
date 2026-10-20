
import math

from data import TYPES

STRING_OPS = ["contains", "starts with", "ends with", "equals"]
NUMBER_OPS = ["=", "!=", "<", "<=", ">", ">="]
ALGOS = ["Linear Search", "Binary Search", "Jump Search"]
RANGE_OPS = {"=", "equals", "<", "<=", ">", ">=", "starts with"}


def parse_value(raw, ctype):
    raw = raw.strip()
    if ctype == "str":
        return raw.lower()
    if ctype == "int":
        return int(float(raw))
    return float(raw)


def _predicate(op, t):
    if op == "contains":
        return lambda v: t in v
    if op == "starts with":
        return lambda v: v.startswith(t)
    if op == "ends with":
        return lambda v: v.endswith(t)
    if op in ("equals", "="):
        return lambda v: v == t
    if op == "!=":
        return lambda v: v != t
    if op == "<":
        return lambda v: v < t
    if op == "<=":
        return lambda v: v <= t
    if op == ">":
        return lambda v: v > t
    return lambda v: v >= t


def linear_search(keys, pred):
    return [i for i, k in enumerate(keys) if pred(k)], len(keys)


def binary_bound(sk, x, right):
    """First index with sk[i] >= x  (right=False)  or  sk[i] > x  (right=True)."""
    lo, hi, c = 0, len(sk), 0
    while lo < hi:
        mid = (lo + hi) // 2
        c += 1
        if (sk[mid] <= x) if right else (sk[mid] < x):
            lo = mid + 1
        else:
            hi = mid
    return lo, c


def jump_bound(sk, x, right):
    """Same contract as binary_bound, found by jumping sqrt(n) blocks."""
    n, c = len(sk), 0
    if n == 0:
        return 0, 0
    step = int(math.sqrt(n)) or 1
    cond = (lambda v: v > x) if right else (lambda v: v >= x)
    prev, cur = 0, step
    while prev < n:
        c += 1
        if cond(sk[min(cur, n) - 1]):
            break
        prev, cur = cur, cur + step
    else:
        return n, c
    for i in range(prev, min(cur, n)):
        c += 1
        if cond(sk[i]):
            return i, c
    return min(cur, n), c


def search_condition(rows, spec):
    """spec = dict(col, op, value, algo). Returns (set of id(row), comparisons, algo used)."""
    col, op = spec["col"], spec["op"]
    ctype = TYPES[col]
    target = parse_value(spec["value"], ctype)
    keys = [r[col].lower() if ctype == "str" else r[col] for r in rows]

    algo = spec["algo"]
    if algo == "Linear Search" or op not in RANGE_OPS:
        used = algo if algo == "Linear Search" else "Linear Search (fallback)"
        hits, c = linear_search(keys, _predicate(op, target))
        return {id(rows[i]) for i in hits}, c, used

    order = sorted(range(len(keys)), key=keys.__getitem__)   # preparation, not counted
    sk = [keys[i] for i in order]
    find = binary_bound if algo == "Binary Search" else jump_bound
    n, c = len(sk), 0
    if op in ("=", "equals"):
        lo, c1 = find(sk, target, False)
        hi, c2 = find(sk, target, True)
        c = c1 + c2
    elif op == "<":
        lo, (hi, c) = 0, find(sk, target, False)
    elif op == "<=":
        lo, (hi, c) = 0, find(sk, target, True)
    elif op == ">":
        (lo, c), hi = find(sk, target, True), n
    elif op == ">=":
        (lo, c), hi = find(sk, target, False), n
    else:  # starts with
        lo, c1 = find(sk, target, False)
        hi, c2 = find(sk, target + "\U0010ffff", False)
        c = c1 + c2
    return {id(rows[i]) for i in order[lo:hi]}, c, algo
