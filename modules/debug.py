"""Debug system for F1 debug mode functionality"""
import pygame
import os
from datetime import datetime
from typing import Optional, Tuple, Callable
from core import constants


class DebugSystem:
    """Manages all debug mode functionality"""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.debug_font = pygame.font.Font(None, 24)
        self.show_debug = False
        self.show_debug_viewport_only = False
        self.sampled_color: Optional[Tuple[int, int, int]] = None
        
        # Screenshot button
        self.screenshot_button_rect = pygame.Rect(10, 100, 150, 30)
        self.screenshot_button_hover = False
        
        # Callbacks for external state
        self.get_current_sector: Optional[Callable[[], Tuple[int, int]]] = None
        self.get_targeted_planet: Optional[Callable[[], Optional[str]]] = None
        self.get_flight_speed: Optional[Callable[[], int]] = None
        self.is_in_flight_mode: Optional[Callable[[], bool]] = None
        self.is_chat_active: Optional[Callable[[], bool]] = None
        self.increase_flight_speed: Optional[Callable[[], None]] = None
        self.decrease_flight_speed: Optional[Callable[[], None]] = None
        
        # Speed key hold tracking
        self.speed_key_held = None  # 'x' or 'z' or None
        self.speed_key_hold_timer = 0.0
        self.speed_key_hold_delay = 0.3  # Initial delay before auto-increment (seconds)
        self.speed_key_hold_interval = 0.05  # Interval between increments (seconds)
        self.last_increment_time = 0.0  # Time of last auto-increment
    
    def toggle_debug(self):
        """Toggle debug mode on/off"""
        self.show_debug = not self.show_debug
    
    def toggle_debug_viewport_only(self):
        """Toggle debug viewport only mode"""
        self.show_debug_viewport_only = not self.show_debug_viewport_only
        return self.show_debug_viewport_only
    
    def handle_key_event(self, event: pygame.event.Event) -> bool:
        """
        Handle debug-related key events.
        Returns True if event was handled, False otherwise.
        """
        if event.type != pygame.KEYDOWN:
            return False
        
        if event.key == constants.DEBUG_KEY:
            self.toggle_debug()
            return True
        
        # Speed control (X and Z keys) - works in all modes, only requires flight mode and not in chat
        # This is NOT debug-only, it should work everywhere
        if self.is_in_flight_mode and self.is_in_flight_mode() and \
           self.is_chat_active and not self.is_chat_active():
            if event.key == pygame.K_x:
                if self.increase_flight_speed:
                    self.increase_flight_speed()
                    self.speed_key_held = 'x'
                    self.speed_key_hold_timer = 0.0
                return True
            elif event.key == pygame.K_z:
                if self.decrease_flight_speed:
                    self.decrease_flight_speed()
                    self.speed_key_held = 'z'
                    self.speed_key_hold_timer = 0.0
                return True
        
        # Debug-only features (require F1 debug mode)
        if not self.show_debug:
            return False
        
        # Color sampling (I key) - debug only
        if event.key == pygame.K_i:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            try:
                if 0 <= mouse_x < constants.SCREEN_WIDTH and 0 <= mouse_y < constants.SCREEN_HEIGHT:
                    self.sampled_color = self.screen.get_at((mouse_x, mouse_y))
                    print(f"Sampled color at ({mouse_x}, {mouse_y}): RGB {self.sampled_color[:3]}")
                    return True
            except Exception as e:
                print(f"Error sampling color: {e}")
            return True
        
        return False
    
    def handle_key_up_event(self, event: pygame.event.Event) -> bool:
        """
        Handle key release events for speed control.
        Returns True if event was handled, False otherwise.
        """
        if event.type != pygame.KEYUP:
            return False
        
        # Speed key release works in all modes, not just debug
        # Release speed key hold
        if event.key == pygame.K_x and self.speed_key_held == 'x':
            self.speed_key_held = None
            self.speed_key_hold_timer = 0.0
            self.last_increment_time = 0.0
            return True
        elif event.key == pygame.K_z and self.speed_key_held == 'z':
            self.speed_key_held = None
            self.speed_key_hold_timer = 0.0
            self.last_increment_time = 0.0
            return True
        
        return False
    
    def update(self, dt: float):
        """Update debug system (for auto-increment when holding speed keys)"""
        # Speed key auto-increment works in all modes, not just debug
        if self.speed_key_held and self.is_in_flight_mode and self.is_in_flight_mode() and \
           self.is_chat_active and not self.is_chat_active():
            self.speed_key_hold_timer += dt
            
            # After initial delay, increment at regular intervals
            if self.speed_key_hold_timer >= self.speed_key_hold_delay:
                # Check if enough time has passed since last increment
                time_since_last = self.speed_key_hold_timer - self.speed_key_hold_delay - self.last_increment_time
                if time_since_last >= self.speed_key_hold_interval:
                    # Increment speed
                    if self.speed_key_held == 'x' and self.increase_flight_speed:
                        self.increase_flight_speed()
                    elif self.speed_key_held == 'z' and self.decrease_flight_speed:
                        self.decrease_flight_speed()
                    
                    # Update last increment time
                    self.last_increment_time = self.speed_key_hold_timer - self.speed_key_hold_delay
        else:
            # Reset timers when key is not held
            self.last_increment_time = 0.0
    
    def handle_mouse_event(self, event: pygame.event.Event) -> bool:
        """
        Handle debug-related mouse events (e.g., button clicks).
        Returns True if event was handled, False otherwise.
        """
        if not self.show_debug:
            return False
        
        if event.type == pygame.MOUSEMOTION:
            # Check if hovering over screenshot button
            self.screenshot_button_hover = self.screenshot_button_rect.collidepoint(event.pos)
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.screenshot_button_rect.collidepoint(event.pos):
                    self._take_region_screenshot('right_region')
                    return True
        
        return False
    
    def _take_region_screenshot(self, region_name: str):
        """Take a screenshot of a specific region and save it as PNG"""
        if region_name not in constants.REGIONS:
            print(f"Error: Region '{region_name}' not found")
            return
        
        top_left, bottom_right = constants.REGIONS[region_name]
        x, y = top_left
        width = bottom_right[0] - x
        height = bottom_right[1] - y
        
        # Create a subsurface of the region
        try:
            region_surface = self.screen.subsurface(pygame.Rect(x, y, width, height))
            
            # Create a copy to avoid issues with subsurface
            screenshot = pygame.Surface((width, height))
            screenshot.blit(region_surface, (0, 0))
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{region_name}_{timestamp}.png"
            
            # Save to current directory
            pygame.image.save(screenshot, filename)
            print(f"Screenshot saved: {filename} ({width}x{height})")
        except Exception as e:
            print(f"Error taking screenshot: {e}")
    
    def draw(self):
        """Draw all debug UI elements"""
        if self.show_debug:
            self._draw_debug_info()
            self._draw_screenshot_button()
        
        if self.show_debug_viewport_only:
            self._draw_debug_viewport()
            self._draw_targeted_message()
    
    def _draw_debug_info(self):
        """Draw debug information overlay"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        debug_text = f"Mouse: X: {mouse_x}, Y: {mouse_y}"
        text_surface = self.debug_font.render(debug_text, True, constants.BLACK)
        central_top_top_left, _ = constants.REGIONS['central_top_region']
        text_x = central_top_top_left[0] + 10
        text_y = central_top_top_left[1] + 10
        self.screen.blit(text_surface, (text_x, text_y))
        
        # Display sampled color below mouse coordinates
        if self.sampled_color is not None:
            r, g, b = self.sampled_color[:3]
            color_text = f"RGB: ({r}, {g}, {b})"
            color_surface = self.debug_font.render(color_text, True, constants.BLACK)
            self.screen.blit(color_surface, (text_x, text_y + 25))
        
        # Display flight speed (only in flight mode and not in chat)
        if self.is_in_flight_mode and self.is_in_flight_mode() and \
           self.is_chat_active and not self.is_chat_active() and \
           self.get_flight_speed:
            speed = self.get_flight_speed()
            speed_text = f"Speed: {speed}/100"
            speed_surface = self.debug_font.render(speed_text, True, constants.BLACK)
            self.screen.blit(speed_surface, (text_x, text_y + 50))
    
    def _draw_screenshot_button(self):
        """Draw the screenshot button"""
        # Button background
        button_color = (100, 150, 200) if self.screenshot_button_hover else (80, 120, 160)
        pygame.draw.rect(self.screen, button_color, self.screenshot_button_rect)
        pygame.draw.rect(self.screen, constants.BLACK, self.screenshot_button_rect, 2)
        
        # Button text
        button_text = "Screenshot Right"
        text_surface = self.debug_font.render(button_text, True, constants.WHITE)
        text_rect = text_surface.get_rect(center=self.screenshot_button_rect.center)
        self.screen.blit(text_surface, text_rect)
    
    def _draw_debug_viewport(self):
        """Draw red unfilled polygon for debug viewport"""
        if hasattr(constants, 'DEBUG_VIEWPORT'):
            # Draw unfilled polygon outline (closed=True connects last point to first)
            pygame.draw.lines(self.screen, constants.RED, True, constants.DEBUG_VIEWPORT, 1)
    
    def _draw_targeted_message(self):
        """Draw targeted planet message and sector info in Tab debug mode"""
        yellow = (255, 255, 0)
        y_offset = 10
        
        # Show sector information
        if self.get_current_sector:
            sector_x, sector_y = self.get_current_sector()
            sector_text = f"Sector: ({sector_x}, {sector_y})"
            sector_surface = self.debug_font.render(sector_text, True, yellow)
            self.screen.blit(sector_surface, (10, y_offset))
            y_offset += 30
        
        # Show targeted planet
        if self.get_targeted_planet:
            planet = self.get_targeted_planet()
            if planet:
                planet_text = f"Targeted: {planet}"
                planet_surface = self.debug_font.render(planet_text, True, yellow)
                self.screen.blit(planet_surface, (10, y_offset))

