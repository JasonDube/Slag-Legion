"""Utility functions"""
from typing import List, Tuple


def calculate_region_size(top_left: Tuple[int, int], bottom_right: Tuple[int, int]) -> Tuple[int, int]:
    """Calculate width and height of a region"""
    width = bottom_right[0] - top_left[0]
    height = bottom_right[1] - top_left[1]
    return width, height


def point_in_polygon(point: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

