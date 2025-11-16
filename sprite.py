"""Sprite system"""
import pygame
from typing import Dict, Optional
from animation import Animation


class Sprite:
    """Animated sprite (crew members, NPCs, etc.)"""
    
    def __init__(self, name: str, position: tuple, animations: Dict[str, Animation], default_animation: str = 'idle'):
        self.name = name
        self.position = position
        self.animations = animations
        self.current_animation_name = default_animation
        self.visible = True
        
    def get_current_animation(self) -> Optional[Animation]:
        """Get the currently playing animation"""
        return self.animations.get(self.current_animation_name)
    
    def play_animation(self, animation_name: str):
        """Switch to and play a different animation"""
        if animation_name in self.animations:
            if self.current_animation_name in self.animations:
                self.animations[self.current_animation_name].stop()
            self.current_animation_name = animation_name
            self.animations[animation_name].play()
    
    def update(self, dt: float):
        """Update sprite animations"""
        anim = self.get_current_animation()
        if anim:
            anim.update(dt)
    
    def draw(self, screen: pygame.Surface):
        """Draw the sprite"""
        if not self.visible:
            return
            
        anim = self.get_current_animation()
        if anim and anim.playing:
            frame = anim.get_current_frame()
            if frame:
                screen.blit(frame, self.position)

