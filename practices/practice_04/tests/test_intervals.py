import math
import pytest

from intervals import merge_intervals, contains_point
from intervals import intersects, intersection


def test_merge_empty():
    assert merge_intervals([]) == []


def test_merge_no_overlap():
    intervals = [(1, 2), (4, 5)]
    assert merge_intervals(intervals) == [(1, 2), (4, 5)]


def test_merge_overlap():
    intervals = [(1, 3), (2, 4), (6, 7)]
    assert merge_intervals(intervals) == [(1, 4), (6, 7)]


def test_merge_unsorted_and_adjacent():
    intervals = [(5, 6), (1, 2), (2, 3), (3, 5)]
    assert merge_intervals(intervals) == [(1, 6)]


def test_merge_without_adjacent():
    intervals = [(1, 2), (2, 3), (4, 5)]
    assert merge_intervals(intervals, merge_adjacent=False) == [(1, 2), (2, 3), (4, 5)]


def test_contains_point_basic():
    intervals = [(0, 1), (2, 5)]
    assert contains_point(intervals, 0)
    assert contains_point(intervals, 1)
    assert contains_point(intervals, 2)
    assert contains_point(intervals, 5)
    assert contains_point(intervals, 3)
    assert not contains_point(intervals, 1.5)


def test_contains_point_float():
    intervals = [(0.5, 1.5), (2, 3)]
    assert contains_point(intervals, 1.0)
    assert contains_point(intervals, 0.5)
    assert not contains_point(intervals, 4.2)


def test_invalid_interval_raises():
    with pytest.raises(ValueError):
        merge_intervals([(3, 1)])
    with pytest.raises(ValueError):
        contains_point([(3, 1)], 0)


def test_intersects_true_overlap():
    assert intersects((1, 5), (4, 8)) is True


def test_intersects_true_touching():
    assert intersects((1, 5), (5, 8)) is True


def test_intersects_false():
    assert intersects((1, 5), (6, 8)) is False


def test_intersects_validation():
    with pytest.raises(ValueError):
        intersects((5, 1), (0, 1))


def test_intersection_overlap():
    assert intersection((1, 5), (4, 8)) == (4, 5)


def test_intersection_touching():
    assert intersection((1, 5), (5, 8)) == (5, 5)


def test_intersection_none():
    assert intersection((1, 5), (6, 8)) is None


def test_intersection_validation():
    with pytest.raises(ValueError):
        intersection((5, 1), (0, 1))
