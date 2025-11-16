"""Interactive element system"""
import pygame
from typing import List, Optional, Tuple
from utils import point_in_polygon
import constants


class InteractiveElement:
    """Represents a clickable/hoverable element in a room"""
    
    def __init__(self, shape, action_type: str, shape_type: str = 'rect', **kwargs):
        """
        Args:
            shape: pygame.Rect for rectangles, or List[tuple] for polygons (list of (x,y) points)
            action_type: Type of action ('room_transition', 'show_screen', etc.)
            shape_type: 'rect' or 'polygon'
        """
        self.shape = shape
        self.shape_type = shape_type  # 'rect' or 'polygon'
        self.action_type = action_type
        self.action_data = kwargs
        self.hover_alpha = 51  # 80% transparent = 20% opacity
        
        # Calculate bounding rect for drawing purposes
        if shape_type == 'rect':
            self.bounding_rect = shape
        else:  # polygon
            xs = [p[0] for p in shape]
            ys = [p[1] for p in shape]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            self.bounding_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
        
    def is_hovered(self, mouse_pos: Tuple[int, int]) -> bool:
        """Check if mouse is over this element"""
        if self.shape_type == 'rect':
            return self.shape.collidepoint(mouse_pos)
        else:  # polygon
            return point_in_polygon(mouse_pos, self.shape)
    
    def draw_hover(self, screen: pygame.Surface):
        """Draw hover effect (red transparent shape)"""
        hover_surface = pygame.Surface((self.bounding_rect.width, self.bounding_rect.height), pygame.SRCALPHA)
        
        if self.shape_type == 'rect':
            hover_surface.fill((constants.RED[0], constants.RED[1], constants.RED[2], self.hover_alpha))
        else:  # polygon
            # Adjust polygon points relative to bounding rect
            adjusted_points = [(p[0] - self.bounding_rect.x, p[1] - self.bounding_rect.y) for p in self.shape]
            pygame.draw.polygon(hover_surface, (constants.RED[0], constants.RED[1], constants.RED[2], self.hover_alpha), adjusted_points)
        
        screen.blit(hover_surface, self.bounding_rect.topleft)

