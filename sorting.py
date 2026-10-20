import random
import time

from data import TYPES


class Rev:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return o.v < self.v

    def __gt__(self, o):
        return o.v > self.v

    def __le__(self, o):
        return o.v <= self.v

    def __ge__(self, o):
        return o.v >= self.v


def bubble_sort(a):
    c = s = 0
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            c += 1
            if a[j][0] > a[j + 1][0]:
                a[j], a[j + 1] = a[j + 1], a[j]
                s += 1
                swapped = True
        if not swapped:
            break
    return c, s


def selection_sort(a):
    c = s = 0
    n = len(a)
    for i in range(n - 1):
        m = i
        for j in range(i + 1, n):
            c += 1
            if a[j][0] < a[m][0]:
                m = j
        if m != i:
            a[i], a[m] = a[m], a[i]
            s += 1
    return c, s


def insertion_sort(a):
    c = s = 0
    for i in range(1, len(a)):
        t = a[i]
        j = i - 1
        while j >= 0:
            c += 1
            if a[j][0] > t[0]:
                a[j + 1] = a[j]
                s += 1
                j -= 1
            else:
                break
        a[j + 1] = t
    return c, s


def merge_sort(a):
    c = s = 0
    n = len(a)
    src, dst = a, [None] * n
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                c += 1
                if src[j][0] < src[i][0]:
                    dst[k] = src[j]
                    j += 1
                else:
                    dst[k] = src[i]
                    i += 1
                k += 1
                s += 1
            while i < mid:
                dst[k] = src[i]
                i += 1
                k += 1
                s += 1
            while j < hi:
                dst[k] = src[j]
                j += 1
                k += 1
                s += 1
        src, dst = dst, src
        width *= 2
    if src is not a:
        a[:] = src
    return c, s


def quick_sort(a):
    c = s = 0
    stack = [(0, len(a) - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        p = a[random.randint(lo, hi)][0]
        lt, i, gt = lo, lo, hi
        while i <= gt:
            x = a[i][0]
            c += 1
            if x < p:
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
                s += 1
            else:
                c += 1
                if x > p:
                    a[i], a[gt] = a[gt], a[i]
                    gt -= 1
                    s += 1
                else:
                    i += 1
        if lt - lo < hi - gt:
            stack.append((gt + 1, hi))
            stack.append((lo, lt - 1))
        else:
            stack.append((lo, lt - 1))
            stack.append((gt + 1, hi))
    return c, s


def cocktail_sort(a):
    c = s = 0
    lo, hi = 0, len(a) - 1
    swapped = True
    while swapped and lo < hi:
        swapped = False
        for j in range(lo, hi):
            c += 1
            if a[j][0] > a[j + 1][0]:
                a[j], a[j + 1] = a[j + 1], a[j]
                s += 1
                swapped = True
        hi -= 1
        for j in range(hi, lo, -1):
            c += 1
            if a[j - 1][0] > a[j][0]:
                a[j - 1], a[j] = a[j], a[j - 1]
                s += 1
                swapped = True
        lo += 1
    return c, s


def hybrid_sort(a):
    RUN = 16
    c = s = 0
    n = len(a)
    for lo in range(0, n, RUN):
        hi = min(lo + RUN, n)
        for i in range(lo + 1, hi):
            t = a[i]
            j = i - 1
            while j >= lo:
                c += 1
                if a[j][0] > t[0]:
                    a[j + 1] = a[j]
                    s += 1
                    j -= 1
                else:
                    break
            a[j + 1] = t
    src, dst = a, [None] * n
    width = RUN
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                c += 1
                if src[j][0] < src[i][0]:
                    dst[k] = src[j]
                    j += 1
                else:
                    dst[k] = src[i]
                    i += 1
                k += 1
                s += 1
            while i < mid:
                dst[k] = src[i]
                i += 1
                k += 1
                s += 1
            while j < hi:
                dst[k] = src[j]
                j += 1
                k += 1
                s += 1
        src, dst = dst, src
        width *= 2
    if src is not a:
        a[:] = src
    return c, s


def counting_sort(a):
    n = len(a)
    if n < 2:
        return 0, 0
    lo = min(x[0] for x in a)
    hi = max(x[0] for x in a)
    k = hi - lo
    if k > 5_000_000:
        raise ValueError("Value range too large for Counting Sort")
    count = [0] * (k + 1)
    for x in a:
        count[x[0] - lo] += 1
    for i in range(1, k + 1):
        count[i] += count[i - 1]
    out = [None] * n
    for x in reversed(a):
        j = x[0] - lo
        count[j] -= 1
        out[count[j]] = x
    a[:] = out
    return 0, n


def radix_sort(a):
    n = len(a)
    if n < 2:
        return 0, 0
    lo = min(x[0] for x in a)
    b = [(x[0] - lo, x) for x in a]
    maxv = max(v for v, _ in b)
    exp, s = 1, 0
    while maxv // exp > 0:
        count = [0] * 10
        for v, _ in b:
            count[(v // exp) % 10] += 1
        for i in range(1, 10):
            count[i] += count[i - 1]
        out = [None] * n
        for item in reversed(b):
            d = (item[0] // exp) % 10
            count[d] -= 1
            out[count[d]] = item
            s += 1
        b = out
        exp *= 10
    a[:] = [x for _, x in b]
    return 0, s


def bucket_sort(a):
    n = len(a)
    if n < 2:
        return 0, 0
    lo = min(x[0] for x in a)
    hi = max(x[0] for x in a)
    span = hi - lo
    if span == 0:
        return 0, 0
    c = s = 0
    buckets = [[] for _ in range(n)]
    for x in a:
        buckets[int((x[0] - lo) / span * (n - 1))].append(x)
        s += 1
    out = []
    for b in buckets:
        for i in range(1, len(b)):
            t = b[i]
            j = i - 1
            while j >= 0:
                c += 1
                if b[j][0] > t[0]:
                    b[j + 1] = b[j]
                    s += 1
                    j -= 1
                else:
                    break
            b[j + 1] = t
        out.extend(b)
    a[:] = out
    return c, s


ALGORITHMS = {
    "Bubble Sort":    dict(fn=bubble_sort,    complexity="O(n²)",                       stable=True,  kind="any"),
    "Selection Sort": dict(fn=selection_sort, complexity="O(n²)",                       stable=False, kind="any"),
    "Insertion Sort": dict(fn=insertion_sort, complexity="O(n²)",                       stable=True,  kind="any"),
    "Merge Sort":     dict(fn=merge_sort,     complexity="O(n log n)",                  stable=True,  kind="any"),
    "Quick Sort":     dict(fn=quick_sort,     complexity="O(n log n) avg",              stable=False, kind="any"),
    "Cocktail Sort":  dict(fn=cocktail_sort,  complexity="O(n²)",                       stable=True,  kind="any"),
    "Hybrid Sort":    dict(fn=hybrid_sort,    complexity="O(n log n)",                  stable=True,  kind="any"),
    "Counting Sort":  dict(fn=counting_sort,  complexity="O(n + k)",                    stable=True,  kind="int"),
    "Radix Sort":     dict(fn=radix_sort,     complexity="O(d·(n + b))",                stable=True,  kind="int"),
    "Bucket Sort":    dict(fn=bucket_sort,    complexity="O(n + k) avg, O(n²) worst",   stable=True,  kind="num"),
}
SLOW_ALGOS = {"Bubble Sort", "Selection Sort", "Insertion Sort", "Cocktail Sort", "Bucket Sort"}


def label(name):
    info = ALGORITHMS[name]
    return f"{name}  [{info['complexity']}, {'stable' if info['stable'] else 'unstable'}]"


def applicable(name, specs):
    kind = ALGORITHMS[name]["kind"]
    if kind == "any":
        return True
    if len(specs) != 1:
        return False
    t = TYPES[specs[0][0]]
    return t == "int" if kind == "int" else t in ("int", "float")


def build_items(rows, specs):
    getters = []
    for col, desc in specs:
        if TYPES[col] == "str":
            if desc:
                g = lambda r, c=col: Rev(r[c].lower())
            else:
                g = lambda r, c=col: r[c].lower()
        else:
            g = (lambda r, c=col: -r[c]) if desc else (lambda r, c=col: r[c])
        getters.append(g)
    if len(getters) == 1:
        g = getters[0]
        return [(g(r), r) for r in rows]
    return [(tuple(g(r) for g in getters), r) for r in rows]


def run_sort(rows, specs, algo):
    if not applicable(algo, specs):
        raise ValueError(f"{algo} cannot be used for this column selection")
    items = build_items(rows, specs)
    t0 = time.perf_counter()
    comparisons, swaps = ALGORITHMS[algo]["fn"](items)
    ms = (time.perf_counter() - t0) * 1000
    return dict(rows=[it[1] for it in items], comparisons=comparisons, swaps=swaps, ms=ms)


def benchmark(rows, col, desc, n):
    sample = list(rows) if n >= len(rows) else random.sample(rows, n)
    specs = [(col, desc)]
    out = []
    for name, info in ALGORITHMS.items():
        if not applicable(name, specs):
            continue
        entry = dict(name=name, complexity=info["complexity"], stable=info["stable"])
        try:
            r = run_sort(sample, specs, name)
            entry.update(ms=r["ms"], comparisons=r["comparisons"], swaps=r["swaps"])
        except ValueError as e:
            entry.update(ms=None, comparisons=None, swaps=None, error=str(e))
        out.append(entry)
    return out, len(sample)