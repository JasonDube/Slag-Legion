"""Main game class"""
import pygame
import random
import sys
from typing import Dict, Optional, List
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
from lexi_chat import LexiChat
from systems.lexi_system import LexiSystem


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
        
        # World space tracking
        self.world_x = constants.WORLD_WIDTH // 2  # Start at center: (325000, 175000)
        self.world_y = constants.WORLD_HEIGHT // 2
        self.current_sector_x = constants.SECTORS_X // 2  # Sector (250, 250)
        self.current_sector_y = constants.SECTORS_Y // 2
        
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
        
        # Initialize planet screen positions (they need to be calculated from world positions)
        for planet in self.starfield.planets:
            planet.update_screen_position(self.world_x, self.world_y)
            print(f"Planet {planet.name} screen position: ({planet.screen_x:.1f}, {planet.screen_y:.1f}), world: ({planet.world_x:.1f}, {planet.world_y:.1f})")
        
        # Initialize Lexi system
        lexi_chat = LexiChat()
        self.lexi_system = LexiSystem(self.screen, lexi_chat, self.show_debug_viewport_only)
        
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
        
        try:
            right_path = "region_images/right/IS_AI_CHAT_00001.png"
            right_img = pygame.image.load(right_path).convert_alpha()
            right_top_left, right_bottom_right = REGIONS['right_region']
            region_width, region_height = calculate_region_size(right_top_left, right_bottom_right)
            right_img = pygame.transform.scale(right_img, (region_width, region_height))
            region_images['right_region'] = right_img
            print(f"Loaded image for right_region: {region_width}x{region_height}")
        except Exception as e:
            print(f"Error loading right_region image: {e}")
            region_images['right_region'] = None
        
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
                    self.lexi_system.set_debug_viewport_mode(self.show_debug_viewport_only)
                # Handle Lexi events first (takes priority)
                elif self.lexi_system.handle_event(event):
                    pass  # Event was handled by Lexi system
                # Flight controls - only process if Lexi didn't handle the event
                elif not self.lexi_system.input_active:
                    if event.key == pygame.K_t:
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
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                # Let Lexi system handle its events first
                if not self.lexi_system.handle_event(event):
                    # If Lexi didn't handle it, process other mouse events
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._handle_mouse_click(event.pos)
        
        return True
    
    def _handle_mouse_click(self, mouse_pos: tuple):
        """Handle mouse click on interactive elements and planet"""
        current_room_name = self.player_location['ship_room']
        
        # Check for planet click (only in Control Room or Tab mode)
        if current_room_name == 'Control Room' or self.show_debug_viewport_only:
            show_all = self.show_debug_viewport_only
            visible_polygon = None
            current_sector = (self.current_sector_x, self.current_sector_y)
            if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
                visible_polygon = constants.DEBUG_VIEWPORT
            
            if self.starfield.check_planet_click(mouse_pos, show_all, visible_polygon, current_sector):
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
        
        # Update Lexi system
        self.lexi_system.update(dt)
        
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
            
            # Update world position based on movement (opposite to star movement)
            if dx != 0 or dy != 0:
                move_delta_x = dx * self.starfield.move_speed * dt
                move_delta_y = dy * self.starfield.move_speed * dt
                self.world_x -= move_delta_x  # Move opposite to star movement
                self.world_y -= move_delta_y
                
                # Wrap world position (toroidal topology)
                self.world_x = self.world_x % constants.WORLD_WIDTH
                self.world_y = self.world_y % constants.WORLD_HEIGHT
                if self.world_x < 0:
                    self.world_x += constants.WORLD_WIDTH
                if self.world_y < 0:
                    self.world_y += constants.WORLD_HEIGHT
                
                # Calculate current sector from world position (with wrapping)
                self.current_sector_x = int(self.world_x // constants.SECTOR_WIDTH) % constants.SECTORS_X
                self.current_sector_y = int(self.world_y // constants.SECTOR_HEIGHT) % constants.SECTORS_Y
        else:
            # Stop movement and rotation when not in Control Room or Tab mode
            self.starfield.set_movement(0.0, 0.0)
            self.starfield.set_rotation(0.0)
        
        # Update starfield (pass player world position for planet screen position calculation)
        self.starfield.update(dt, self.world_x, self.world_y)
    
    # Lexi drawing methods removed - now handled by LexiSystem
    
    def draw(self):
        """Draw everything to the screen"""
        # Fill the screen with black background
        self.screen.fill(BLACK)
        
        # If in debug viewport only mode, draw stars, polygon, and targeted message only
        if self.show_debug_viewport_only:
            # Draw all stars
            current_sector = (self.current_sector_x, self.current_sector_y)
            self.starfield.draw(self.screen, show_all=True, current_sector=current_sector)
            self._draw_debug_viewport()
            # Draw targeted message
            self._draw_targeted_message()
            pygame.display.flip()
            return
        
        # Draw starfield - only visible in masked area of Control Room
        current_room_name = self.player_location['ship_room']
        if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
            # Draw stars only in the masked viewport area
            current_sector = (self.current_sector_x, self.current_sector_y)
            self.starfield.draw(self.screen, show_all=False, visible_polygon=constants.DEBUG_VIEWPORT, 
                              current_sector=current_sector)
        
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
        
        # Draw Lexi system (not in tab-debug mode)
        if not self.show_debug_viewport_only:
            self.lexi_system.draw()
        
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
        """Draw targeted planet message and sector info in Tab debug mode"""
        if self.show_debug_viewport_only:
            yellow = (255, 255, 0)
            y_offset = 10
            
            # Show sector information
            sector_text = f"Sector: ({self.current_sector_x}, {self.current_sector_y})"
            sector_surface = self.debug_font.render(sector_text, True, yellow)
            self.screen.blit(sector_surface, (10, y_offset))
            y_offset += 30
            
            # Show targeted planet
            targeted_name = self.starfield.get_targeted_planet_name()
            if targeted_name:
                target_text = f"{targeted_name} targeted"
                target_surface = self.debug_font.render(target_text, True, yellow)
                self.screen.blit(target_surface, (10, y_offset))
    
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

