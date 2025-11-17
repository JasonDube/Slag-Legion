"""Starfield system"""
import pygame
import random
import math
from typing import List, Tuple
import constants


class Star:
    """Represents a single star"""
    
    def __init__(self, x: float, y: float, brightness: float = 1.0):
        self.x = x
        self.y = y
        self.base_brightness = brightness
        self.brightness = brightness
        self.blinks = random.random() < 0.3  # 30% of stars blink
        self.blink_timer = random.uniform(0, math.pi * 2)  # Random starting phase
        self.blink_speed = random.uniform(0.5, 2.0)  # Blink speed varies
    
    def update(self, dt: float):
        """Update star animation (blinking)"""
        if self.blinks:
            self.blink_timer += dt * self.blink_speed
            # Use sine wave for smooth blinking (0.3 to 1.0 brightness)
            self.brightness = 0.3 + (self.base_brightness - 0.3) * (0.5 + 0.5 * math.sin(self.blink_timer))
        else:
            self.brightness = self.base_brightness
    
    def rotate(self, angle_radians: float, center_x: float, center_y: float):
        """Rotate the star around a center point by the given angle in radians"""
        # Translate to origin
        dx = self.x - center_x
        dy = self.y - center_y
        
        # Rotate
        cos_a = math.cos(angle_radians)
        sin_a = math.sin(angle_radians)
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a
        
        # Translate back
        self.x = new_x + center_x
        self.y = new_y + center_y
    
    def is_off_screen(self) -> bool:
        """Check if star is off screen"""
        return (self.x < -10 or self.x > constants.SCREEN_WIDTH + 10 or 
                self.y < -10 or self.y > constants.SCREEN_HEIGHT + 10)
    
    def get_color(self) -> Tuple[int, int, int]:
        """Get star color based on brightness"""
        # Stars are white with varying brightness
        brightness_int = int(255 * self.brightness)
        return (brightness_int, brightness_int, brightness_int)


class Planet:
    """Represents a planet in space"""
    
    def __init__(self, world_x: float, world_y: float, name: str, radius: float = 15.0, color: Tuple[int, int, int] = (0, 100, 255)):
        self.world_x = world_x  # Position in world space
        self.world_y = world_y
        self.screen_x = 0.0  # Calculated screen position
        self.screen_y = 0.0
        self.name = name
        self.radius = radius
        self.color = color
        self.selected = False
        self.targeted = False
    
    def update_screen_position(self, player_world_x: float, player_world_y: float):
        """Calculate screen position from world position relative to player"""
        # Screen center represents player's world position
        self.screen_x = (self.world_x - player_world_x) + constants.SCREEN_WIDTH / 2
        self.screen_y = (self.world_y - player_world_y) + constants.SCREEN_HEIGHT / 2
    
    def get_sector(self) -> Tuple[int, int]:
        """Get the sector this planet is in"""
        sector_x = int(self.world_x // constants.SECTOR_WIDTH) % constants.SECTORS_X
        sector_y = int(self.world_y // constants.SECTOR_HEIGHT) % constants.SECTORS_Y
        return (sector_x, sector_y)
    
    def is_clicked(self, mouse_pos: Tuple[int, int]) -> bool:
        """Check if the planet was clicked (uses screen position)"""
        dx = mouse_pos[0] - self.screen_x
        dy = mouse_pos[1] - self.screen_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radius
    
    def rotate(self, angle_radians: float, center_x: float, center_y: float):
        """Rotate the planet around a center point by the given angle in radians (in world space)"""
        # Translate to origin (in world space)
        dx = self.world_x - center_x
        dy = self.world_y - center_y
        
        # Rotate
        cos_a = math.cos(angle_radians)
        sin_a = math.sin(angle_radians)
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a
        
        # Translate back
        self.world_x = new_x + center_x
        self.world_y = new_y + center_y
    
    def draw(self, screen: pygame.Surface):
        """Draw the planet with optional yellow outline if selected (uses screen position)"""
        pygame.draw.circle(screen, self.color, (int(self.screen_x), int(self.screen_y)), int(self.radius))
        
        # Draw yellow outline if selected
        if self.selected:
            yellow = (255, 255, 0)
            pygame.draw.circle(screen, yellow, (int(self.screen_x), int(self.screen_y)), int(self.radius) + 3, 2)


class Starfield:
    """Manages the starfield"""
    
    def __init__(self, num_stars: int = 200, move_speed: float = 200.0, rotation_speed: float = 90.0):
        self.stars: List[Star] = []
        self.num_stars = num_stars
        self.move_speed = move_speed  # pixels per second
        self.rotation_speed = rotation_speed  # degrees per second
        self.velocity_x = 0.0  # Movement in x direction
        self.velocity_y = 0.0  # Movement in y direction
        self.rotation_velocity = 0.0  # Rotation speed (positive = clockwise, negative = counterclockwise)
        self.center_x = constants.SCREEN_WIDTH / 2  # Rotation center
        self.center_y = constants.SCREEN_HEIGHT / 2  # Rotation center
        self._generate_stars(num_stars)
        # Create planets in starting sector (250, 250) for testing
        self.planets: List[Planet] = []
        # Player starts at (WORLD_WIDTH // 2, WORLD_HEIGHT // 2) = (325000, 175000)
        # This is the left edge of sector (250, 250), which appears at screen center
        player_start_x = constants.WORLD_WIDTH // 2
        player_start_y = constants.WORLD_HEIGHT // 2
        
        # Blue planet - place offset from player start position (so it's visible on screen)
        # Offset by screen-relative amounts so they appear on screen
        blue_world_x = player_start_x + random.uniform(-400, 400)
        blue_world_y = player_start_y + random.uniform(-250, 250)
        blue_planet = Planet(blue_world_x, blue_world_y, "blue planet", 15.0, (0, 100, 255))
        self.planets.append(blue_planet)
        print(f"Created blue planet at world: ({blue_world_x:.1f}, {blue_world_y:.1f})")
        
        # Red planet - place offset from player start position
        red_world_x = player_start_x + random.uniform(-400, 400)
        red_world_y = player_start_y + random.uniform(-250, 250)
        red_planet = Planet(red_world_x, red_world_y, "red planet", 15.0, (255, 50, 50))
        self.planets.append(red_planet)
        print(f"Created red planet at world: ({red_world_x:.1f}, {red_world_y:.1f})")
    
    def _generate_stars(self, num_stars: int):
        """Generate random stars across the screen"""
        for _ in range(num_stars):
            x = random.uniform(0, constants.SCREEN_WIDTH)
            y = random.uniform(0, constants.SCREEN_HEIGHT)
            brightness = random.uniform(0.4, 1.0)  # Varying brightness
            self.stars.append(Star(x, y, brightness))
    
    def _create_star_at_edge(self, edge: str) -> Star:
        """Create a new star at a specific edge of the screen
        
        Args:
            edge: 'left', 'right', 'top', 'bottom'
        """
        brightness = random.uniform(0.4, 1.0)
        
        if edge == 'left':
            x = -10.0
            y = random.uniform(0, constants.SCREEN_HEIGHT)
        elif edge == 'right':
            x = constants.SCREEN_WIDTH + 10.0
            y = random.uniform(0, constants.SCREEN_HEIGHT)
        elif edge == 'top':
            x = random.uniform(0, constants.SCREEN_WIDTH)
            y = -10.0
        else:  # bottom
            x = random.uniform(0, constants.SCREEN_WIDTH)
            y = constants.SCREEN_HEIGHT + 10.0
        
        return Star(x, y, brightness)
    
    def set_movement(self, dx: float, dy: float):
        """Set movement direction for stars
        
        Args:
            dx: X direction (-1 for left, 1 for right, 0 for none)
            dy: Y direction (-1 for up, 1 for down, 0 for none)
        """
        self.velocity_x = dx * self.move_speed
        self.velocity_y = dy * self.move_speed
    
    def set_rotation(self, direction: float):
        """Set rotation direction for stars
        
        Args:
            direction: -1 for counterclockwise, 1 for clockwise, 0 for none
        """
        self.rotation_velocity = direction * self.rotation_speed
    
    def update(self, dt: float, player_world_x: float, player_world_y: float):
        """Update all stars (movement, rotation, and blinking) and planets
        
        Args:
            dt: Delta time
            player_world_x: Player's world X position
            player_world_y: Player's world Y position
        """
        # Calculate movement delta
        dx = self.velocity_x * dt
        dy = self.velocity_y * dt
        
        # Calculate rotation angle in radians if rotating
        rotation_angle_rad = 0.0
        if self.rotation_velocity != 0:
            rotation_angle_rad = math.radians(self.rotation_velocity * dt)
        
        # Update stars
        for star in self.stars:
            # Update blinking
            star.update(dt)
            
            # Apply linear movement first
            star.x += dx
            star.y += dy
            
            # Apply rotation if rotating
            if rotation_angle_rad != 0:
                star.rotate(rotation_angle_rad, self.center_x, self.center_y)
        
        # Update planets - they stay fixed in world space, only screen position changes
        for planet in self.planets:
            # Planets do NOT move in world space - they stay in their sector
            # Only apply rotation if rotating (around player's world position)
            if rotation_angle_rad != 0:
                planet.rotate(rotation_angle_rad, player_world_x, player_world_y)
            
            # Update screen position based on player's world position
            # This makes planets appear to move on screen like stars, but they stay in their sector
            planet.update_screen_position(player_world_x, player_world_y)
        
        # Remove stars that went off screen and create new ones
        stars_to_remove = []
        for star in self.stars:
            if star.is_off_screen():
                stars_to_remove.append(star)
        
        # Determine which edge(s) to spawn from based on movement direction
        # Stars move in the direction of velocity, so spawn from opposite edge(s)
        edges_to_spawn = []
        
        if self.velocity_x > 0:  # Moving right - spawn from left
            edges_to_spawn.append('left')
        elif self.velocity_x < 0:  # Moving left - spawn from right
            edges_to_spawn.append('right')
        
        if self.velocity_y > 0:  # Moving down - spawn from top
            edges_to_spawn.append('top')
        elif self.velocity_y < 0:  # Moving up - spawn from bottom
            edges_to_spawn.append('bottom')
        
        # If no movement, spawn from random edge
        if not edges_to_spawn:
            edges_to_spawn = [random.choice(['left', 'right', 'top', 'bottom'])]
        
        # Remove off-screen stars and spawn replacements
        for star in stars_to_remove:
            self.stars.remove(star)
            # Spawn from all determined edges
            for edge in edges_to_spawn:
                self.stars.append(self._create_star_at_edge(edge))
        
        # Maintain minimum star count
        while len(self.stars) < self.num_stars:
            # Spawn from edge(s) opposite to movement, or random if not moving
            if not edges_to_spawn:
                edges_to_spawn = [random.choice(['left', 'right', 'top', 'bottom'])]
            for edge in edges_to_spawn:
                self.stars.append(self._create_star_at_edge(edge))
    
    def check_planet_click(self, mouse_pos: Tuple[int, int], show_all: bool = False, 
                          visible_polygon: List[Tuple[int, int]] = None, 
                          current_sector: Tuple[int, int] = None) -> bool:
        """Check if any planet was clicked and handle selection
        
        Args:
            mouse_pos: Mouse position (x, y)
            show_all: If True, planets are always visible. If False, check visible_polygon
            visible_polygon: Polygon coordinates defining visible area
            current_sector: Current sector (x, y) - only show planets in this sector
            
        Returns:
            True if a planet was clicked, False otherwise
        """
        from utils import point_in_polygon
        
        # Check all planets
        for planet in self.planets:
            # Check if planet is in current sector (if not show_all)
            if not show_all and current_sector:
                planet_sector = planet.get_sector()
                if planet_sector != current_sector:
                    continue  # Skip planets not in current sector
            
            # Check if planet is visible on screen
            planet_visible = False
            if show_all:
                planet_visible = True
            elif visible_polygon:
                planet_visible = point_in_polygon((planet.screen_x, planet.screen_y), visible_polygon)
            else:
                # If no polygon but in sector, check if on screen
                planet_visible = (-50 <= planet.screen_x <= constants.SCREEN_WIDTH + 50 and 
                                 -50 <= planet.screen_y <= constants.SCREEN_HEIGHT + 50)
            
            if planet_visible and planet.is_clicked(mouse_pos):
                # Deselect all other planets
                for p in self.planets:
                    p.selected = False
                # Select clicked planet
                planet.selected = True
                return True
        
        return False
    
    def target_selected_planet(self) -> bool:
        """Target the currently selected planet
        
        Returns:
            True if a planet was targeted, False otherwise
        """
        # Find selected planet
        selected_planet = None
        for planet in self.planets:
            if planet.selected:
                selected_planet = planet
                break
        
        if selected_planet:
            # Untarget all planets
            for planet in self.planets:
                planet.targeted = False
            # Target the selected planet
            selected_planet.targeted = True
            return True
        
        return False
    
    def get_targeted_planet_name(self) -> str:
        """Get the name of the currently targeted planet
        
        Returns:
            Name of targeted planet, or None if no planet is targeted
        """
        for planet in self.planets:
            if planet.targeted:
                return planet.name
        return None
    
    def draw(self, screen: pygame.Surface, show_all: bool = False, visible_polygon: List[Tuple[int, int]] = None,
             current_sector: Tuple[int, int] = None):
        """Draw stars and planets
        
        Args:
            screen: Surface to draw on
            show_all: If True, draw all stars. If False, only draw stars in visible_polygon
            visible_polygon: Polygon coordinates defining visible area (screen coordinates)
            current_sector: Current sector (x, y) - only draw planets in this sector
        """
        from utils import point_in_polygon
        
        for star in self.stars:
            # Determine if star should be visible
            if show_all:
                visible = True
            elif visible_polygon:
                visible = point_in_polygon((star.x, star.y), visible_polygon)
            else:
                visible = False
            
            if visible:
                color = star.get_color()
                # Draw small star (1-2 pixels)
                size = 1 if star.brightness < 0.7 else 2
                pygame.draw.circle(screen, color, (int(star.x), int(star.y)), size)
        
        # Draw planets if visible and in current sector
        for planet in self.planets:
            # Check if planet is in current sector (if not show_all)
            if not show_all and current_sector:
                planet_sector = planet.get_sector()
                if planet_sector != current_sector:
                    continue  # Skip planets not in current sector
            
            # Check if planet is visible on screen
            planet_visible = False
            if show_all:
                planet_visible = True
            elif visible_polygon:
                # Check if planet center is in visible polygon
                planet_visible = point_in_polygon((planet.screen_x, planet.screen_y), visible_polygon)
            else:
                # If no polygon but in sector, check if on screen
                planet_visible = (-50 <= planet.screen_x <= constants.SCREEN_WIDTH + 50 and 
                                 -50 <= planet.screen_y <= constants.SCREEN_HEIGHT + 50)
            
            if planet_visible:
                planet.draw(screen)

