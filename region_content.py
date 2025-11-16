"""Region content management system"""
import pygame
from typing import Dict, Any
import constants


class RegionContent:
    """Manages what content is displayed in each region"""
    
    def __init__(self):
        self.content: Dict[str, Dict[str, Any]] = {}
        # Initialize all regions
        for region_name in constants.REGIONS.keys():
            self.content[region_name] = {
                'type': 'default',  # 'default', 'screen', 'info', 'custom'
                'data': None
            }
    
    def set_screen(self, region_name: str, screen_image: pygame.Surface):
        """Display a screen image in a region"""
        if region_name in self.content:
            self.content[region_name]['type'] = 'screen'
            self.content[region_name]['data'] = screen_image
    
    def set_info(self, region_name: str, info_text: str):
        """Set info text in a region"""
        if region_name in self.content:
            self.content[region_name]['type'] = 'info'
            self.content[region_name]['data'] = info_text
    
    def clear(self, region_name: str):
        """Clear content from a region (return to default)"""
        if region_name in self.content:
            self.content[region_name]['type'] = 'default'
            self.content[region_name]['data'] = None

