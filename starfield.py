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
    
    def __init__(self, x: float, y: float, name: str, radius: float = 15.0, color: Tuple[int, int, int] = (0, 100, 255)):
        self.x = x
        self.y = y
        self.name = name
        self.radius = radius
        self.color = color
        self.selected = False
        self.targeted = False
    
    def is_clicked(self, mouse_pos: Tuple[int, int]) -> bool:
        """Check if the planet was clicked"""
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radius
    
    def rotate(self, angle_radians: float, center_x: float, center_y: float):
        """Rotate the planet around a center point by the given angle in radians"""
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
    
    def draw(self, screen: pygame.Surface):
        """Draw the planet with optional yellow outline if selected"""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.radius))
        
        # Draw yellow outline if selected
        if self.selected:
            yellow = (255, 255, 0)
            pygame.draw.circle(screen, yellow, (int(self.x), int(self.y)), int(self.radius) + 3, 2)


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
        # Create planets at random positions
        self.planets: List[Planet] = []
        # Blue planet
        blue_x = random.uniform(100, constants.SCREEN_WIDTH - 100)
        blue_y = random.uniform(100, constants.SCREEN_HEIGHT - 100)
        self.planets.append(Planet(blue_x, blue_y, "blue planet", 15.0, (0, 100, 255)))
        # Red planet
        red_x = random.uniform(100, constants.SCREEN_WIDTH - 100)
        red_y = random.uniform(100, constants.SCREEN_HEIGHT - 100)
        self.planets.append(Planet(red_x, red_y, "red planet", 15.0, (255, 50, 50)))
    
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
    
    def update(self, dt: float):
        """Update all stars (movement, rotation, and blinking)"""
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
        
        # Update planets (moves and rotates same as stars)
        for planet in self.planets:
            planet.x += dx
            planet.y += dy
            if rotation_angle_rad != 0:
                planet.rotate(rotation_angle_rad, self.center_x, self.center_y)
        
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
                          visible_polygon: List[Tuple[int, int]] = None) -> bool:
        """Check if any planet was clicked and handle selection
        
        Args:
            mouse_pos: Mouse position (x, y)
            show_all: If True, planets are always visible. If False, check visible_polygon
            visible_polygon: Polygon coordinates defining visible area
            
        Returns:
            True if a planet was clicked, False otherwise
        """
        from utils import point_in_polygon
        
        # Check all planets
        for planet in self.planets:
            # Check if planet is visible
            planet_visible = False
            if show_all:
                planet_visible = True
            elif visible_polygon:
                planet_visible = point_in_polygon((planet.x, planet.y), visible_polygon)
            
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
    
    def draw(self, screen: pygame.Surface, show_all: bool = False, visible_polygon: List[Tuple[int, int]] = None):
        """Draw stars and planet
        
        Args:
            screen: Surface to draw on
            show_all: If True, draw all stars. If False, only draw stars in visible_polygon
            visible_polygon: Polygon coordinates defining visible area (screen coordinates)
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
        
        # Draw planets if visible
        for planet in self.planets:
            planet_visible = False
            if show_all:
                planet_visible = True
            elif visible_polygon:
                # Check if planet center is in visible polygon
                planet_visible = point_in_polygon((planet.x, planet.y), visible_polygon)
            
            if planet_visible:
                planet.draw(screen)

