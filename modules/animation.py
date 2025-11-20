"""Animation system"""
import pygame
from typing import List, Optional


class Animation:
    """Base class for animations"""
    
    def __init__(self, name: str, frames: List[pygame.Surface], fps: float = 10.0, loop: bool = True):
        self.name = name
        self.frames = frames
        # Ensure fps is always positive to avoid division by zero
        self.fps = max(fps, 0.0001)
        self.loop = loop
        self.current_frame = 0
        self.frame_timer = 0
        self.playing = False
        self.finished = False
        
    def update(self, dt: float):
        """Update animation frame"""
        if not self.playing:
            return
            
        self.frame_timer += dt
        frame_duration = 1.0 / self.fps
        
        if self.frame_timer >= frame_duration:
            self.frame_timer = 0
            self.current_frame += 1
            
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True
                    self.playing = False
    
    def play(self):
        """Start playing the animation"""
        self.playing = True
        self.finished = False
        self.current_frame = 0
        self.frame_timer = 0
    
    def stop(self):
        """Stop the animation"""
        self.playing = False
    
    def get_current_frame(self) -> Optional[pygame.Surface]:
        """Get the current frame"""
        if self.frames:
            return self.frames[self.current_frame]
        return None

