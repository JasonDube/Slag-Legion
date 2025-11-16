"""Main game class"""
import pygame
import random
import sys
from typing import Dict, Optional
import constants
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, REGIONS, FPS, 
    DEBUG_KEY, ESCAPE_KEY
)
from utils import calculate_region_size
from room import Room
from region_content import RegionContent
from action_handler import ActionHandler
from room_config import load_rooms
from starfield import Starfield


class Game:
    """Main game class that manages the game loop and state"""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Slag Legion 2.0 - Region Layout")
        
        self.debug_font = pygame.font.Font(None, 24)
        self.show_debug = False
        self.show_debug_viewport_only = False  # Toggle with Tab key
        
        # Starfield movement keys (WASD)
        self.keys_pressed = set()  # Track currently pressed keys
        
        # Player location tracking
        self.player_location = {
            'on_ship': True,
            'ship_name': 'Dagger',
            'ship_room': 'Control Room'
        }
        
        # Initialize systems
        self.region_content = RegionContent()
        self.rooms = load_rooms()
        self.action_handler = ActionHandler(self.player_location, self.rooms, self.region_content)
        
        # Load region images
        self.region_images = self._load_region_images()
        
        # Generate random colors for placeholder regions
        self.region_colors = self._generate_region_colors()
        
        # Initialize starfield
        self.starfield = Starfield(num_stars=300)
        
        # Start default animation for starting room
        starting_room = self.player_location['ship_room']
        if starting_room in self.rooms:
            self.rooms[starting_room].start_default_animation()
        
        self._print_startup_info()
    
    def _load_region_images(self) -> Dict[str, Optional[pygame.Surface]]:
        """Load and scale images for regions"""
        region_images = {}
        try:
            central_middle_path = "region_images/central_middle/IS_Central_00001.png"
            central_middle_img = pygame.image.load(central_middle_path).convert_alpha()
            central_middle_top_left, central_middle_bottom_right = REGIONS['central_middle_region']
            region_width, region_height = calculate_region_size(central_middle_top_left, central_middle_bottom_right)
            central_middle_img = pygame.transform.scale(central_middle_img, (region_width, region_height))
            region_images['central_middle_region'] = central_middle_img
            print(f"Loaded image for central_middle_region: {region_width}x{region_height}")
        except Exception as e:
            print(f"Error loading central_middle_region image: {e}")
            region_images['central_middle_region'] = None
        
        return region_images
    
    def _generate_region_colors(self) -> Dict[str, tuple]:
        """Generate random colors for placeholder regions"""
        region_colors = {}
        for region_name in REGIONS.keys():
            region_colors[region_name] = (
                random.randint(50, 255),
                random.randint(50, 255),
                random.randint(50, 255)
            )
        return region_colors
    
    def _print_startup_info(self):
        """Print startup information to console"""
        print("\n=== REGION SIZES ===")
        for region_name, (top_left, bottom_right) in REGIONS.items():
            width, height = calculate_region_size(top_left, bottom_right)
            print(f"{region_name}: {width} x {height} pixels")
        print("===================\n")
        
        print(f"Player starting location: {self.player_location['ship_name']} - {self.player_location['ship_room']}")
        print("===================\n")
        
        print("=== LOADED ROOMS ===")
        for room_name in sorted(self.rooms.keys()):
            room = self.rooms[room_name]
            transition_count = len(room.interactive_elements)
            has_image = room.background_image is not None
            status = "✓" if has_image else "⚠ (image path set, file may not exist)"
            print(f"{status} {room_name} - {transition_count} transition(s)")
        print("===================\n")
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == ESCAPE_KEY:
                    return False
                elif event.key == DEBUG_KEY:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_TAB:
                    self.show_debug_viewport_only = not self.show_debug_viewport_only
                elif event.key == pygame.K_t:
                    # Target selected planet (only in Control Room or Tab mode)
                    current_room_name = self.player_location['ship_room']
                    if current_room_name == 'Control Room' or self.show_debug_viewport_only:
                        self.starfield.target_selected_planet()
                # Track WASD keys for starfield movement
                elif event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
                    self.keys_pressed.add(event.key)
                # Track Q and E keys for starfield rotation
                elif event.key in (pygame.K_q, pygame.K_e):
                    self.keys_pressed.add(event.key)
            elif event.type == pygame.KEYUP:
                # Remove keys when released
                if event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
                    self.keys_pressed.discard(event.key)
                elif event.key in (pygame.K_q, pygame.K_e):
                    self.keys_pressed.discard(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self._handle_mouse_click(event.pos)
        
        return True
    
    def _handle_mouse_click(self, mouse_pos: tuple):
        """Handle mouse click on interactive elements and planet"""
        current_room_name = self.player_location['ship_room']
        
        # Check for planet click (only in Control Room or Tab mode)
        if current_room_name == 'Control Room' or self.show_debug_viewport_only:
            show_all = self.show_debug_viewport_only
            visible_polygon = None
            if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
                visible_polygon = constants.DEBUG_VIEWPORT
            
            if self.starfield.check_planet_click(mouse_pos, show_all, visible_polygon):
                return  # Planet was clicked, don't check room elements
        
        # Check for room interactive elements
        if current_room_name in self.rooms:
            room = self.rooms[current_room_name]
            hovered_element = room.get_hovered_element(mouse_pos)
            if hovered_element:
                self.action_handler.handle_action(hovered_element)
    
    def update(self, dt: float):
        """Update game state"""
        current_room_name = self.player_location['ship_room']
        if current_room_name in self.rooms:
            self.rooms[current_room_name].update(dt)
        
        # Handle starfield movement and rotation (only in Control Room or Tab mode)
        if current_room_name == 'Control Room' or self.show_debug_viewport_only:
            dx, dy = 0.0, 0.0
            rotation_dir = 0.0
            
            # W: stars move down (positive Y)
            if pygame.K_w in self.keys_pressed:
                dy = 1.0
            # S: stars move up (negative Y)
            if pygame.K_s in self.keys_pressed:
                dy = -1.0
            # A: stars move right (positive X)
            if pygame.K_a in self.keys_pressed:
                dx = 1.0
            # D: stars move left (negative X)
            if pygame.K_d in self.keys_pressed:
                dx = -1.0
            
            # Q: rotate clockwise (positive direction)
            if pygame.K_q in self.keys_pressed:
                rotation_dir = 1.0
            # E: rotate counterclockwise (negative direction)
            if pygame.K_e in self.keys_pressed:
                rotation_dir = -1.0
            
            self.starfield.set_movement(dx, dy)
            self.starfield.set_rotation(rotation_dir)
        else:
            # Stop movement and rotation when not in Control Room or Tab mode
            self.starfield.set_movement(0.0, 0.0)
            self.starfield.set_rotation(0.0)
        
        # Update starfield
        self.starfield.update(dt)
    
    def draw(self):
        """Draw everything to the screen"""
        # Fill the screen with black background
        self.screen.fill(BLACK)
        
        # If in debug viewport only mode, draw stars, polygon, and targeted message only
        if self.show_debug_viewport_only:
            # Draw all stars
            self.starfield.draw(self.screen, show_all=True)
            self._draw_debug_viewport()
            # Draw targeted message
            self._draw_targeted_message()
            pygame.display.flip()
            return
        
        # Draw starfield - only visible in masked area of Control Room
        current_room_name = self.player_location['ship_room']
        if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
            # Draw stars only in the masked viewport area
            self.starfield.draw(self.screen, show_all=False, visible_polygon=constants.DEBUG_VIEWPORT)
        
        # Draw all regions as filled rectangles or images
        for region_name, (top_left, bottom_right) in REGIONS.items():
            if region_name in self.region_images and self.region_images[region_name] is not None:
                self.screen.blit(self.region_images[region_name], top_left)
            else:
                width, height = calculate_region_size(top_left, bottom_right)
                color = self.region_colors[region_name]
                pygame.draw.rect(self.screen, color, (top_left[0], top_left[1], width, height))
        
        # Update and draw current room
        if current_room_name in self.rooms:
            room = self.rooms[current_room_name]
            mouse_x, mouse_y = pygame.mouse.get_pos()
            room.draw(self.screen, (mouse_x, mouse_y))
        
        # Draw region content (screens, info, etc.)
        for region_name, content_data in self.region_content.content.items():
            if content_data['type'] == 'screen' and content_data['data']:
                top_left, _ = REGIONS[region_name]
                self.screen.blit(content_data['data'], top_left)
            elif content_data['type'] == 'info' and content_data['data']:
                # Draw info text (you can customize this)
                top_left, _ = REGIONS[region_name]
                # TODO: Implement text rendering for info
        
        # Draw debug viewport polygon (red outline) - only in Control Room
        if current_room_name == 'Control Room':
            self._draw_debug_viewport()
        
        # Debug display
        if self.show_debug:
            self._draw_debug()
        
        # Update the display
        pygame.display.flip()
    
    def _draw_debug_viewport(self):
        """Draw red unfilled polygon for debug viewport"""
        if hasattr(constants, 'DEBUG_VIEWPORT'):
            # Draw unfilled polygon outline (closed=True connects last point to first)
            pygame.draw.lines(self.screen, constants.RED, True, constants.DEBUG_VIEWPORT, 1)
    
    def _draw_debug(self):
        """Draw debug information"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        debug_text = f"Mouse: X: {mouse_x}, Y: {mouse_y}"
        text_surface = self.debug_font.render(debug_text, True, BLACK)
        central_top_top_left, _ = REGIONS['central_top_region']
        text_x = central_top_top_left[0] + 10
        text_y = central_top_top_left[1] + 10
        self.screen.blit(text_surface, (text_x, text_y))
    
    def _draw_targeted_message(self):
        """Draw targeted planet message in Tab debug mode"""
        if self.show_debug_viewport_only:
            targeted_name = self.starfield.get_targeted_planet_name()
            if targeted_name:
                target_text = f"{targeted_name} targeted"
                # Use bright yellow for visibility
                yellow = (255, 255, 0)
                target_surface = self.debug_font.render(target_text, True, yellow)
                # Position in top-left corner for visibility
                self.screen.blit(target_surface, (10, 10))
    
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        last_time = pygame.time.get_ticks()
        running = True
        
        while running:
            # Calculate delta time
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0  # Convert to seconds
            last_time = current_time
            
            # Handle events
            running = self.handle_events()
            
            # Update game state
            self.update(dt)
            
            # Draw everything
            self.draw()
            
            # Cap framerate
            clock.tick(FPS)
        
        # Cleanup
        pygame.quit()
        sys.exit()


def main():
    """Entry point"""
    game = Game()
    game.run()


if __name__ == '__main__':
    main()

