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


def circle_intersects_polygon(center: Tuple[float, float], radius: float, polygon: List[Tuple[int, int]]) -> bool:
    """Check if a circle intersects with a polygon.
    
    A circle intersects if:
    1. The center is inside the polygon, OR
    2. Any point on the circle's edge is inside the polygon, OR
    3. The circle's bounding box overlaps with the polygon
    
    Args:
        center: Circle center (x, y)
        radius: Circle radius
        polygon: List of polygon vertices
        
    Returns:
        True if circle intersects polygon, False otherwise
    """
    cx, cy = center
    
    # Check if center is inside polygon
    if point_in_polygon((int(cx), int(cy)), polygon):
        return True
    
    # Check if any point on the circle's edge (cardinal and diagonal directions) is inside
    # This handles cases where the center is outside but part of the circle is inside
    check_points = [
        (cx + radius, cy),      # Right
        (cx - radius, cy),      # Left
        (cx, cy + radius),      # Down
        (cx, cy - radius),      # Up
        (cx + radius * 0.707, cy + radius * 0.707),  # Bottom-right
        (cx - radius * 0.707, cy + radius * 0.707),  # Bottom-left
        (cx + radius * 0.707, cy - radius * 0.707),  # Top-right
        (cx - radius * 0.707, cy - radius * 0.707),  # Top-left
    ]
    
    for px, py in check_points:
        if point_in_polygon((int(px), int(py)), polygon):
            return True
    
    # Also check if any polygon edge intersects the circle
    # This handles cases where the circle surrounds part of the polygon
    n = len(polygon)
    for i in range(n):
        p1x, p1y = polygon[i]
        p2x, p2y = polygon[(i + 1) % n]
        
        # Check if line segment from p1 to p2 is within radius of center
        # Calculate distance from center to line segment
        dx = p2x - p1x
        dy = p2y - p1y
        length_sq = dx * dx + dy * dy
        
        if length_sq == 0:
            # Degenerate segment, check distance to point
            dist_sq = (cx - p1x) ** 2 + (cy - p1y) ** 2
            if dist_sq <= radius * radius:
                return True
        else:
            # Project center onto line segment
            t = max(0, min(1, ((cx - p1x) * dx + (cy - p1y) * dy) / length_sq))
            proj_x = p1x + t * dx
            proj_y = p1y + t * dy
            
            # Check distance from center to projection
            dist_sq = (cx - proj_x) ** 2 + (cy - proj_y) ** 2
            if dist_sq <= radius * radius:
                return True
    
    return False
