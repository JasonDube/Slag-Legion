"""Main game class"""
import pygame
import random
import sys
import os
import glob
from typing import Dict, Optional, List
from core import constants
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, REGIONS, FPS, 
    DEBUG_KEY, ESCAPE_KEY
)
from modules.utils import calculate_region_size
from modules.room import Room
from modules.region_content import RegionContent
from modules.action_handler import ActionHandler
from modules.room_config import load_rooms
from modules.starfield import Starfield
from modules.lexi_chat import LexiChat
from modules.animation import Animation
from systems.lexi_system import LexiSystem
from systems.lexi_state_manager import LexiStateManager
from systems.lexi_animation_loader import LexiAnimationLoader
from modules.debug import DebugSystem


class Game:
    """Main game class that manages the game loop and state"""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Slag Legion 2.0 - Region Layout")
        
        # Initialize debug system
        self.debug_system = DebugSystem(self.screen)
        
        # Starfield movement keys (WASD)
        self.keys_pressed = set()  # Track currently pressed keys
        
        # Flight speed control (0-100, maps to starfield move_speed)
        self.flight_speed = 1  # Start at 1 (minimum speed for movement)
        
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
        
        # Lexi Control Room animations (loaded via animation loader)
        self.lexi_click_rect: Optional[pygame.Rect] = None
        self.lexi_sit_animation: Optional[Animation] = None
        self.lexi_chair_animation: Optional[Animation] = None
        self.lexi_control_room_animation: Optional[Animation] = None
        # Load region images
        self.region_images = self._load_region_images()
        
        # Generate random colors for placeholder regions
        self.region_colors = self._generate_region_colors()
        
        # Initialize starfield
        self.starfield = Starfield(num_stars=300)
        self._update_starfield_speed()  # Initialize starfield speed after starfield is created
        
        # Initialize planet screen positions (they need to be calculated from world positions)
        for planet in self.starfield.planets:
            planet.update_screen_position(self.world_x, self.world_y)
            print(f"Planet {planet.name} screen position: ({planet.screen_x:.1f}, {planet.screen_y:.1f}), world: ({planet.world_x:.1f}, {planet.world_y:.1f})")
        
        # Initialize Lexi state management and animation loading
        self.lexi_state_manager = LexiStateManager()
        self.lexi_animation_loader = LexiAnimationLoader()
        
        # Load Lexi assets for Control Room (must be after animation loader is created)
        self._setup_control_room_lexi_assets()
        
        # Subscribe to state changes for Control Room
        self.lexi_state_manager.subscribe_state_change(self._on_lexi_state_change)
        
        # Initialize Lexi chat and system
        lexi_chat = LexiChat()
        # Register callback to make Lexi stand up when spoken to
        lexi_chat.on_user_message = self._on_lexi_user_message
        self.lexi_system = LexiSystem(
            self.screen, lexi_chat, 
            self.lexi_state_manager, self.lexi_animation_loader,
            self.debug_system.show_debug_viewport_only
        )
        
        # Set up debug system callbacks
        self.debug_system.get_current_sector = lambda: (self.current_sector_x, self.current_sector_y)
        self.debug_system.get_targeted_planet = lambda: self.starfield.get_targeted_planet_name()
        self.debug_system.get_flight_speed = lambda: self.flight_speed
        self.debug_system.is_in_flight_mode = lambda: self._is_in_flight_mode()
        self.debug_system.is_chat_active = lambda: self.lexi_system.input_active
        self.debug_system.increase_flight_speed = self._increase_flight_speed
        self.debug_system.decrease_flight_speed = self._decrease_flight_speed
        
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
    
    def _setup_control_room_lexi_assets(self):
        """Prepare Lexi sit/chair poses and her full animation for the Control Room."""
        if 'Control Room' not in self.rooms:
            print("Warning: Control Room not found, cannot load Lexi assets")
            return
        
        control_room = self.rooms['Control Room']
        
        # Load animations using the animation loader
        control_room_animations = self.lexi_animation_loader.load_animations_for_location("control_room")
        
        # Get animations
        self.lexi_sit_animation = control_room_animations.get("sit")
        self.lexi_chair_animation = control_room_animations.get("chair")
        self.lexi_control_room_animation = control_room_animations.get("standing")
        
        # Set up click rect and initial state
        if self.lexi_sit_animation:
            sit_frame = self.lexi_sit_animation.get_current_frame()
            if sit_frame:
                sit_x = 780
                sit_y = 363
                self.lexi_click_rect = pygame.Rect(sit_x, sit_y, sit_frame.get_width(), sit_frame.get_height())
                
                # Add animations to room
                self.lexi_sit_animation.play()
                control_room.add_animation(self.lexi_sit_animation, is_default=False, position=(sit_x, sit_y))
                
                if self.lexi_chair_animation:
                    self.lexi_chair_animation.stop()
                    control_room.add_animation(self.lexi_chair_animation, is_default=False, position=(sit_x, sit_y))
                
                if self.lexi_control_room_animation:
                    self.lexi_control_room_animation.stop()
                    control_room.add_animation(self.lexi_control_room_animation, is_default=False, position=(645, 260))
                
                print(f"✓ Loaded Lexi Control Room assets (sit, chair, standing)")
            else:
                self.lexi_click_rect = None
        else:
            print("Warning: Lexi sit pose not found")
            self.lexi_click_rect = None
    
    def _handle_lexi_pose_click(self, mouse_pos: tuple) -> bool:
        """Toggle Lexi between sit/chair states when her sprite is clicked."""
        if self.player_location.get('ship_room') != 'Control Room':
            return False
        
        if not self.lexi_click_rect or not self.lexi_click_rect.collidepoint(mouse_pos):
            return False
        
        # Toggle pose via state manager
        current_pose = self.lexi_state_manager.physical_pose
        new_pose = "stand" if current_pose == "sit" else "sit"
        self.lexi_state_manager.update_pose(new_pose)
        
        return True
    
    def _on_lexi_state_change(self, emotion: str, pose: str):
        """Callback triggered when Lexi state changes - update Control Room animations."""
        if self.player_location.get('ship_room') != 'Control Room':
            return
        
        # Update animations based on pose
        if pose == "sit":
            if self.lexi_sit_animation:
                self.lexi_sit_animation.play()
            if self.lexi_chair_animation:
                self.lexi_chair_animation.stop()
            if self.lexi_control_room_animation:
                self.lexi_control_room_animation.stop()
            print("Lexi returned to seated pose.")
        elif pose == "stand":
            if self.lexi_sit_animation:
                self.lexi_sit_animation.stop()
            if self.lexi_chair_animation:
                self.lexi_chair_animation.play()
            if self.lexi_control_room_animation:
                self.lexi_control_room_animation.play()
            print("Lexi switched to standing/animated pose.")
    
    def _on_lexi_user_message(self, message: str):
        """Callback triggered when user sends a message to Lexi - makes her stand up."""
        # Only trigger if we're in Control Room and Lexi is currently sitting
        if (self.player_location.get('ship_room') == 'Control Room' and 
            self.lexi_state_manager.physical_pose == 'sit' and 
            self.lexi_chair_animation is not None):
            self.lexi_state_manager.update_pose('stand')
    
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
            
            # Handle debug system events first
            debug_handled = self.debug_system.handle_key_event(event)
            debug_keyup_handled = self.debug_system.handle_key_up_event(event)
            if self.debug_system.handle_mouse_event(event):
                continue
            
            # Don't let debug system consume WASD/QE keys - they need to reach flight controls
            if event.type == pygame.KEYDOWN:
                # If it's a flight control key, ignore debug system's handling
                if event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_q, pygame.K_e):
                    debug_handled = False
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_q, pygame.K_e):
                    debug_keyup_handled = False
            
            if debug_handled or debug_keyup_handled:
                continue
            
            if event.type == pygame.KEYDOWN:
                if event.key == ESCAPE_KEY:
                    return False
                elif event.key == pygame.K_TAB:
                    viewport_mode = self.debug_system.toggle_debug_viewport_only()
                    self.lexi_system.set_debug_viewport_mode(viewport_mode)
                # Handle Lexi events first (takes priority)
                elif self.lexi_system.handle_event(event):
                    pass  # Event was handled by Lexi system
                # Flight controls - only process if Lexi didn't handle the event
                elif not self.lexi_system.input_active:
                    if event.key == pygame.K_t:
                        # Target selected planet (only in Control Room or Tab mode)
                        current_room_name = self.player_location['ship_room']
                        if current_room_name == 'Control Room' or self.debug_system.show_debug_viewport_only:
                            self.starfield.target_selected_planet()
                    # Track WASD keys for starfield movement (always track, movement applied in update if in Control Room or tab debug)
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
        if current_room_name == 'Control Room' or self.debug_system.show_debug_viewport_only:
            show_all = self.debug_system.show_debug_viewport_only
            visible_polygon = None
            current_sector = (self.current_sector_x, self.current_sector_y)
            if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
                visible_polygon = constants.DEBUG_VIEWPORT
            
            if self.starfield.check_planet_click(mouse_pos, show_all, visible_polygon, current_sector):
                return  # Planet was clicked, don't check room elements
        
        # Allow Lexi pose toggling via direct sprite click
        if self._handle_lexi_pose_click(mouse_pos):
            return
        
        # Check for room interactive elements
        if current_room_name in self.rooms:
            room = self.rooms[current_room_name]
            hovered_element = room.get_hovered_element(mouse_pos)
            if hovered_element:
                self.action_handler.handle_action(hovered_element)
    
    def update(self, dt: float):
        """Update game state"""
        # Update debug system (for auto-increment speed keys)
        self.debug_system.update(dt)
        
        current_room_name = self.player_location['ship_room']
        if current_room_name in self.rooms:
            self.rooms[current_room_name].update(dt)
        
        # Update Lexi state manager
        self.lexi_state_manager.update(dt)
        
        # Update Lexi system
        self.lexi_system.update(dt)
        
        # Handle starfield movement and rotation (only in Control Room or Tab mode)
        # Check both conditions explicitly
        in_control_room = current_room_name == 'Control Room'
        in_tab_debug = self.debug_system.show_debug_viewport_only
        
        # Debug: print if condition should allow movement
        if self.keys_pressed and (in_control_room or in_tab_debug):
            # Only print once per second to avoid spam
            if not hasattr(self, '_last_movement_debug') or pygame.time.get_ticks() - self._last_movement_debug > 1000:
                print(f"Movement allowed: room='{current_room_name}', in_control_room={in_control_room}, in_tab_debug={in_tab_debug}, keys={self.keys_pressed}")
                self._last_movement_debug = pygame.time.get_ticks()
        
        if in_control_room or in_tab_debug:
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
        # Pass flight speed and viewport for viewport-based star movement
        visible_polygon = None
        current_room_name = self.player_location['ship_room']
        if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
            visible_polygon = constants.DEBUG_VIEWPORT
        
        self.starfield.update(dt, self.world_x, self.world_y, 
                             flight_speed=self.flight_speed, 
                             visible_polygon=visible_polygon)
    
    # Lexi drawing methods removed - now handled by LexiSystem
    
    def draw(self):
        """Draw everything to the screen"""
        # Fill the screen with black background
        self.screen.fill(BLACK)
        
        # If in debug viewport only mode, draw stars, polygon, and targeted message only
        if self.debug_system.show_debug_viewport_only:
            # Draw all stars
            current_sector = (self.current_sector_x, self.current_sector_y)
            self.starfield.draw(self.screen, show_all=True, current_sector=current_sector, flight_speed=self.flight_speed)
            # Draw debug system elements (red viewport outline and sector info)
            self.debug_system.draw()
            pygame.display.flip()
            return
        
        # Draw starfield - only visible in masked area of Control Room
        current_room_name = self.player_location['ship_room']
        if current_room_name == 'Control Room' and hasattr(constants, 'DEBUG_VIEWPORT'):
            # Draw stars only in the masked viewport area
            current_sector = (self.current_sector_x, self.current_sector_y)
            self.starfield.draw(self.screen, show_all=False, visible_polygon=constants.DEBUG_VIEWPORT, 
                              current_sector=current_sector, flight_speed=self.flight_speed)
        
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
        
        # Draw debug system (handles all debug UI including viewport)
        self.debug_system.draw()
        
        # Draw Lexi system (not in tab-debug mode)
        if not self.debug_system.show_debug_viewport_only:
            self.lexi_system.draw()
        
        # Draw targeted planet name (center-justified at 647, 141) when not in debug viewport mode
        if not self.debug_system.show_debug_viewport_only:
            self._draw_targeted_message()
        
        # Update the display
        pygame.display.flip()
    
    def _is_in_flight_mode(self) -> bool:
        """Check if we're in flight mode (Control Room or debug viewport mode)"""
        current_room_name = self.player_location['ship_room']
        return current_room_name == 'Control Room' or self.debug_system.show_debug_viewport_only
    
    def _increase_flight_speed(self):
        """Increase flight speed by 1 (max 100)"""
        if self.flight_speed < 100:
            self.flight_speed += 1
            self._update_starfield_speed()
    
    def _decrease_flight_speed(self):
        """Decrease flight speed by 1 (min 1)"""
        if self.flight_speed > 1:
            self.flight_speed -= 1
            self._update_starfield_speed()
    
    def _update_starfield_speed(self):
        """Update starfield move_speed based on flight_speed (0-100 maps to 0-1000 pixels/sec)"""
        # Map 0-100 to 0-1000 pixels per second
        # Formula: speed = flight_speed * 10
        self.starfield.move_speed = self.flight_speed * 10.0
    
    def _draw_targeted_message(self):
        """Draw targeted planet name (only when NOT in debug viewport mode)"""
        # Draw targeted planet name center-justified at (647, 137) when not in debug mode
        targeted_name = self.starfield.get_targeted_planet_name()
        if targeted_name:
            target_surface = self.debug_font.render(targeted_name, True, (255, 255, 0))
            # Center-justify: subtract half the text width from x position
            text_width = target_surface.get_width()
            text_x = 647 - (text_width // 2)
            self.screen.blit(target_surface, (text_x, 137))
    
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


