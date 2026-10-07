from __future__ import annotations
from typing import Iterable, List, Sequence, Tuple, Union

Number = Union[int, float]
Interval = Tuple[Number, Number]


def _normalize_intervals(intervals: Iterable[Sequence[Number]]) -> List[Interval]:
    result: List[Interval] = []
    for idx, pair in enumerate(intervals):
        if len(pair) != 2:
            raise ValueError(f"Interval at index {idx} is not a pair: {pair}")
        start, end = pair[0], pair[1]
        if start > end:
            raise ValueError(f"Invalid interval at index {idx}: start > end ({start} > {end})")
        result.append((start, end))
    return result


def merge_intervals(
        intervals: Iterable[Sequence[Number]],
        *,
        merge_adjacent: bool = True) -> List[Interval]:
    normalized = _normalize_intervals(intervals)
    if not normalized:
        return []

    normalized.sort(key=lambda x: (x[0], x[1]))

    merged: List[Interval] = []
    cur_start, cur_end = normalized[0]

    for start, end in normalized[1:]:
        if start < cur_end or (merge_adjacent and start <= cur_end):
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end

    merged.append((cur_start, cur_end))
    return merged


def contains_point(intervals: Iterable[Sequence[Number]], point: Number) -> bool:
    for start, end in _normalize_intervals(intervals):
        if start <= point <= end:
            return True
    return False


def intersects(first: Sequence[Number], second: Sequence[Number]) -> bool:
    a_start, a_end = _normalize_intervals([first])[0]
    b_start, b_end = _normalize_intervals([second])[0]
    return max(a_start, b_start) <= min(a_end, b_end)


def intersection(first: Sequence[Number], second: Sequence[Number]) -> Interval | None:
    a_start, a_end = _normalize_intervals([first])[0]
    b_start, b_end = _normalize_intervals([second])[0]
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if start <= end:
        return (start, end)
    return None
