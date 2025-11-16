"""Room system"""
import pygame
from typing import Dict, List, Optional, Tuple
from interactive import InteractiveElement
from animation import Animation
from sprite import Sprite
import constants


class Room:
    """Represents a room/location with all its data"""
    
    def __init__(self, name: str, background_image_path: str, position: Tuple[int, int], 
                 default_animation_name: Optional[str] = None):
        self.name = name
        self.background_image = None
        self.background_position = position
        self.interactive_elements: List[InteractiveElement] = []
        self.animations: Dict[str, Animation] = {}
        self.animation_positions: Dict[str, Tuple[int, int]] = {}  # Position for each animation
        self.default_animation_name = default_animation_name  # Base animation that runs automatically
        self.sprites: List[Sprite] = []
        self.state = {}  # Room-specific state data
        
        # Load background image
        try:
            img = pygame.image.load(background_image_path).convert_alpha()
            
            # Apply mask for Control Room if this is the Control Room
            if name == 'Control Room' and hasattr(constants, 'MASK_FOR_CONTROL_ROOM'):
                img = self._apply_mask_to_image(img)
            
            self.background_image = img
            print(f"Loaded background for {name}: {background_image_path}")
        except Exception as e:
            print(f"Error loading background for {name}: {e}")
    
    def _apply_mask_to_image(self, img: pygame.Surface) -> pygame.Surface:
        """Apply a polygon mask to cut out an area from the image.
        
        The mask coordinates are in screen coordinates, so we convert them
        to image-relative coordinates by subtracting the image position.
        """
        # Convert screen coordinates to image-relative coordinates
        # ROOM_IMAGE_POSITION is where the image is drawn on screen
        mask_coords = [
            (x - constants.ROOM_IMAGE_POSITION[0], y - constants.ROOM_IMAGE_POSITION[1])
            for x, y in constants.MASK_FOR_CONTROL_ROOM
        ]
        
        # Create a copy of the image to modify
        result = img.copy()
        
        # Create a mask surface - white pixels will be kept, transparent pixels will be cut out
        mask_surface = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        # Fill entire surface with opaque white (keep all pixels)
        mask_surface.fill((255, 255, 255, 255))
        # Draw polygon in transparent (this area will be cut out)
        pygame.draw.polygon(mask_surface, (0, 0, 0, 0), mask_coords)
        
        # Lock the surfaces for pixel access
        result.lock()
        mask_surface.lock()
        
        # Apply mask: make pixels transparent where mask is transparent
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                # Get mask alpha at this pixel
                mask_r, mask_g, mask_b, mask_a = mask_surface.get_at((x, y))
                if mask_a == 0:  # If mask pixel is transparent, cut out this area
                    result.set_at((x, y), (0, 0, 0, 0))  # Make pixel transparent
        
        result.unlock()
        mask_surface.unlock()
        
        return result
    
    def add_interactive_element(self, element: InteractiveElement):
        """Add an interactive element to this room"""
        self.interactive_elements.append(element)
    
    def add_animation(self, animation: Animation, is_default: bool = False, 
                     position: Optional[Tuple[int, int]] = None):
        """Add an animation to this room
        
        Args:
            animation: The Animation object to add
            is_default: If True, set this as the default animation and start it
            position: Optional (x, y) position for the animation. If None, uses background_position
        """
        self.animations[animation.name] = animation
        self.animation_positions[animation.name] = position if position else self.background_position
        if is_default:
            self.default_animation_name = animation.name
            animation.play()
        elif animation.name == self.default_animation_name:
            # If this is the default animation, start it
            animation.play()
    
    def set_default_animation(self, animation_name: str):
        """Set and start the default animation for this room"""
        if animation_name in self.animations:
            self.default_animation_name = animation_name
            self.animations[animation_name].play()
    
    def start_default_animation(self):
        """Start the default animation if it exists"""
        if self.default_animation_name and self.default_animation_name in self.animations:
            self.animations[self.default_animation_name].play()
    
    def add_sprite(self, sprite: Sprite):
        """Add a sprite to this room"""
        self.sprites.append(sprite)
    
    def get_hovered_element(self, mouse_pos: Tuple[int, int]) -> Optional[InteractiveElement]:
        """Get the interactive element the mouse is hovering over"""
        for element in self.interactive_elements:
            if element.is_hovered(mouse_pos):
                return element
        return None
    
    def update(self, dt: float):
        """Update room animations and sprites"""
        for animation in self.animations.values():
            animation.update(dt)
        for sprite in self.sprites:
            sprite.update(dt)
    
    def draw(self, screen: pygame.Surface, mouse_pos: Tuple[int, int]):
        """Draw the room background, animations, sprites, and hover effects"""
        # Draw background
        if self.background_image:
            screen.blit(self.background_image, self.background_position)
        
        # Draw room animations (base animations, lights, effects, etc.)
        for anim_name, animation in self.animations.items():
            if animation.playing:
                frame = animation.get_current_frame()
                if frame:
                    # Draw animation at its specified position
                    anim_pos = self.animation_positions.get(anim_name, self.background_position)
                    screen.blit(frame, anim_pos)
        
        # Draw sprites (crew members, NPCs, etc.)
        for sprite in self.sprites:
            sprite.draw(screen)
        
        # Draw hover effects for interactive elements
        hovered = self.get_hovered_element(mouse_pos)
        if hovered:
            hovered.draw_hover(screen)

