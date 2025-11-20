"""Starfield system"""
import pygame
import random
import math
from typing import List, Tuple
from core import constants


class Star:
    """Represents a single star"""
    
    def __init__(self, x: float, y: float, star_type: str = "warp_10", size: int = 1):
        self.x = x
        self.y = y
        self.star_type = star_type  # e.g., "warp_10"
        self.size = size  # Size in pixels (1 or 2)
        self.brightness = 1.0  # Full brightness for now
        self.has_grown = False  # Track if star has already grown
    
    def update(self, dt: float):
        """Update star (no animation for now)"""
        pass
    
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
        """Get star color - white for warp_10 stars"""
        # All stars are white for now
        return (255, 255, 255)


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
        """Generate random 1-pixel stars across the screen"""
        for _ in range(num_stars):
            x = random.uniform(0, constants.SCREEN_WIDTH)
            y = random.uniform(0, constants.SCREEN_HEIGHT)
            # All stars are warp_10 type, size 1 pixel
            self.stars.append(Star(x, y, star_type="warp_10", size=1))
    
    def _create_star_at_edge(self, edge: str) -> Star:
        """Create a new star at a specific edge of the screen
        
        Args:
            edge: 'left', 'right', 'top', 'bottom'
        """
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
        
        return Star(x, y, star_type="warp_10", size=1)
    
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
    
    def update(self, dt: float, player_world_x: float, player_world_y: float, 
               flight_speed: int = 0, visible_polygon: List[Tuple[int, int]] = None):
        """Update all stars (movement, rotation, and blinking) and planets
        
        Args:
            dt: Delta time
            player_world_x: Player's world X position
            player_world_y: Player's world Y position
            flight_speed: Current flight speed (0-100) for viewport-based star movement
            visible_polygon: Polygon coordinates defining visible viewport area
        """
        # Calculate movement delta
        dx = self.velocity_x * dt
        dy = self.velocity_y * dt
        
        # Calculate rotation angle in radians if rotating
        rotation_angle_rad = 0.0
        if self.rotation_velocity != 0:
            rotation_angle_rad = math.radians(self.rotation_velocity * dt)
        
        # Calculate viewport-based movement speed
        # Movement only starts at speed 10-20
        viewport_movement_speed = 0.0
        if flight_speed >= 10 and visible_polygon:
            # Scale speed from 10-20 to movement speed
            # At speed 10: very slow, at speed 20: moderate speed
            if flight_speed <= 20:
                # Linear scaling from 10-20 to 10-50 pixels/sec
                speed_factor = (flight_speed - 10) / 10.0  # 0.0 at speed 10, 1.0 at speed 20
                viewport_movement_speed = 10.0 + (speed_factor * 40.0)  # 10-50 pixels/sec
            else:
                # For speeds above 20, use the old formula
                speed_factor = (flight_speed / 100.0) ** 1.5
                viewport_movement_speed = speed_factor * 200.0  # Max 200 pixels/sec at speed 100
        
        # Track stars that exit viewport to spawn new ones behind them
        stars_exited_viewport = []
        # Track stars that need to grow and spawn new stars
        stars_to_grow = []
        
        # Update stars
        for star in self.stars:
            # Update blinking
            star.update(dt)
            
            # Check if star is in viewport for viewport-based movement
            in_viewport_before = False
            in_viewport_after = False
            if visible_polygon and viewport_movement_speed > 0:
                from modules.utils import point_in_polygon
                in_viewport_before = point_in_polygon((star.x, star.y), visible_polygon)
            
            if in_viewport_before:
                # Apply viewport-based movement based on star position
                # Stars above y=290 (y < 290) move UP
                # Stars at or below y=290 (y >= 290) move DOWN
                # Stars with x > 816 move RIGHT
                # Stars with x < 490 move LEFT
                # Stars can move in both directions simultaneously (e.g., up+right)
                viewport_dx = 0.0
                viewport_dy = 0.0
                
                # Track movement direction for spawning
                moved_up = False
                moved_down = False
                moved_left = False
                moved_right = False
                
                # Vertical movement
                if star.y < 290:  # Above center line - move up
                    viewport_dy = -viewport_movement_speed * dt
                    moved_up = True
                elif star.y >= 290:  # At or below center line - move down
                    viewport_dy = viewport_movement_speed * dt
                    moved_down = True
                
                # Horizontal movement
                if star.x > 816:  # Right side - move right
                    viewport_dx = viewport_movement_speed * dt
                    moved_right = True
                elif star.x < 490:  # Left side - move left
                    viewport_dx = -viewport_movement_speed * dt
                    moved_left = True
                
                # Store old y position to check for growth threshold
                old_y = star.y
                
                # Apply both movements (stars can move diagonally)
                star.x += viewport_dx
                star.y += viewport_dy
                
                # Check if star moving up/down reached growth threshold (y=295 or y=285)
                if not star.has_grown:
                    if moved_up and old_y >= 285 and star.y < 285:
                        # Star moving up crossed y=285 threshold
                        star.size = 2
                        star.has_grown = True
                        stars_to_grow.append(star)
                        print(f"Star at ({star.x:.1f}, {star.y:.1f}) grew (moved up, crossed y=285)")
                    elif moved_down and old_y <= 295 and star.y > 295:
                        # Star moving down crossed y=295 threshold
                        star.size = 2
                        star.has_grown = True
                        stars_to_grow.append(star)
                        print(f"Star at ({star.x:.1f}, {star.y:.1f}) grew (moved down, crossed y=295)")
                
                # Check if star is still in viewport after movement
                in_viewport_after = point_in_polygon((star.x, star.y), visible_polygon)
                
                # If star exited viewport, track it for spawning new star behind
                if not in_viewport_after:
                    stars_exited_viewport.append({
                        'star': star,
                        'moved_up': moved_up,
                        'moved_down': moved_down,
                        'moved_left': moved_left,
                        'moved_right': moved_right
                    })
            else:
                # Stars outside viewport: apply normal movement (for rotation, etc.)
                star.x += dx
                star.y += dy
            
            # Apply rotation if rotating (only affects stars outside viewport movement)
            if rotation_angle_rad != 0 and not in_viewport_before:
                star.rotate(rotation_angle_rad, self.center_x, self.center_y)
        
        # Create new stars behind stars that exited viewport
        if visible_polygon:
            for exited_star_info in stars_exited_viewport:
                # Determine where to spawn new star (opposite edge from movement direction)
                # Get viewport bounds
                viewport_xs = [p[0] for p in visible_polygon]
                viewport_ys = [p[1] for p in visible_polygon]
                viewport_min_x = min(viewport_xs)
                viewport_max_x = max(viewport_xs)
                viewport_min_y = min(viewport_ys)
                viewport_max_y = max(viewport_ys)
                
                # Spawn at opposite edge based on movement direction
                new_x = None
                new_y = None
                
                if exited_star_info['moved_up']:
                    # Star moved up, spawn at bottom of viewport
                    new_y = viewport_max_y + 5
                    new_x = random.uniform(viewport_min_x, viewport_max_x)
                elif exited_star_info['moved_down']:
                    # Star moved down, spawn at top of viewport
                    new_y = viewport_min_y - 5
                    new_x = random.uniform(viewport_min_x, viewport_max_x)
                
                if exited_star_info['moved_right']:
                    # Star moved right, spawn at left edge of viewport
                    new_x = viewport_min_x - 5
                    if new_y is None:
                        new_y = random.uniform(viewport_min_y, viewport_max_y)
                elif exited_star_info['moved_left']:
                    # Star moved left, spawn at right edge of viewport
                    new_x = viewport_max_x + 5
                    if new_y is None:
                        new_y = random.uniform(viewport_min_y, viewport_max_y)
                
                # If only one direction, use random for the other
                if new_x is None:
                    new_x = random.uniform(viewport_min_x, viewport_max_x)
                if new_y is None:
                    new_y = random.uniform(viewport_min_y, viewport_max_y)
                
                # Create new star (warp_10 type, size 1)
                new_star = Star(new_x, new_y, star_type="warp_10", size=1)
                self.stars.append(new_star)
        
        # Spawn new 1-pixel stars when stars grow (at y=295 or y=285)
        if visible_polygon and stars_to_grow:
            from modules.utils import point_in_polygon
            # Get viewport bounds
            viewport_xs = [p[0] for p in visible_polygon]
            viewport_ys = [p[1] for p in visible_polygon]
            viewport_min_x = min(viewport_xs)
            viewport_max_x = max(viewport_xs)
            viewport_min_y = min(viewport_ys)
            viewport_max_y = max(viewport_ys)
            
            # Calculate center of viewport (should be safe)
            center_x = (viewport_min_x + viewport_max_x) / 2
            center_y = (viewport_min_y + viewport_max_y) / 2
            
            # Spawn one new 1-pixel star in viewport for each star that grew
            for grown_star in stars_to_grow:
                # Try to place star within viewport polygon
                # Strategy: try random positions, but bias toward center area
                new_star = None
                for attempt in range(30):
                    if attempt < 20:
                        # First 20 attempts: random within bounds
                        new_x = random.uniform(viewport_min_x, viewport_max_x)
                        new_y = random.uniform(viewport_min_y, viewport_max_y)
                    else:
                        # Last 10 attempts: bias toward center (more likely to be in polygon)
                        # Use normal distribution centered on viewport center
                        offset_x = random.gauss(0, (viewport_max_x - viewport_min_x) / 4)
                        offset_y = random.gauss(0, (viewport_max_y - viewport_min_y) / 4)
                        new_x = center_x + offset_x
                        new_y = center_y + offset_y
                        # Clamp to bounds
                        new_x = max(viewport_min_x, min(viewport_max_x, new_x))
                        new_y = max(viewport_min_y, min(viewport_max_y, new_y))
                    
                    # Check if position is actually in the polygon
                    if point_in_polygon((new_x, new_y), visible_polygon):
                        new_star = Star(new_x, new_y, star_type="warp_10", size=1)
                        break
                
                # Final fallback: use center if it's in polygon, otherwise use grown star's position
                if new_star is None:
                    if point_in_polygon((center_x, center_y), visible_polygon):
                        new_star = Star(center_x, center_y, star_type="warp_10", size=1)
                    else:
                        # Use grown star's position if it's still in viewport
                        if point_in_polygon((grown_star.x, grown_star.y), visible_polygon):
                            new_star = Star(grown_star.x, grown_star.y, star_type="warp_10", size=1)
                        else:
                            # Last resort: find any point in polygon by checking polygon vertices
                            for vertex in visible_polygon:
                                if point_in_polygon(vertex, visible_polygon):
                                    new_star = Star(vertex[0], vertex[1], star_type="warp_10", size=1)
                                    break
                            # If all else fails, use first vertex
                            if new_star is None:
                                new_star = Star(visible_polygon[0][0], visible_polygon[0][1], star_type="warp_10", size=1)
                
                self.stars.append(new_star)
                # Verify the star is actually in the polygon
                in_poly = point_in_polygon((new_star.x, new_star.y), visible_polygon)
                print(f"Spawned new star at ({new_star.x:.1f}, {new_star.y:.1f}) when star at ({grown_star.x:.1f}, {grown_star.y:.1f}) grew. In polygon: {in_poly}")
        
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
        from modules.utils import point_in_polygon
        
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
                # Check if planet circle intersects with visible polygon
                # This handles cases where planet center is outside but part of planet is visible
                from modules.utils import circle_intersects_polygon
                planet_visible = circle_intersects_polygon(
                    (planet.screen_x, planet.screen_y), 
                    planet.radius, 
                    visible_polygon
                )
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
             current_sector: Tuple[int, int] = None, flight_speed: int = 0):
        """Draw stars and planets
        
        Args:
            screen: Surface to draw on
            show_all: If True, draw all stars. If False, only draw stars in visible_polygon
            visible_polygon: Polygon coordinates defining visible area (screen coordinates)
            current_sector: Current sector (x, y) - only draw planets in this sector
            flight_speed: Current flight speed (0-100) - passed but not used for drawing
        """
        from modules.utils import point_in_polygon
        
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
                # Draw star at its current size (1 or 2 pixels)
                pygame.draw.circle(screen, color, (int(star.x), int(star.y)), star.size)
        
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
                # Check if planet circle intersects with visible polygon
                # This handles cases where planet center is outside but part of planet is visible
                from modules.utils import circle_intersects_polygon
                planet_visible = circle_intersects_polygon(
                    (planet.screen_x, planet.screen_y), 
                    planet.radius, 
                    visible_polygon
                )
            else:
                # If no polygon but in sector, check if on screen
                planet_visible = (-50 <= planet.screen_x <= constants.SCREEN_WIDTH + 50 and 
                                 -50 <= planet.screen_y <= constants.SCREEN_HEIGHT + 50)
            
            if planet_visible:
                planet.draw(screen)

