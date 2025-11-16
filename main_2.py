import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH = 1300
HEIGHT = 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flight Mechanics")

# World space settings
# Each sector is screen-sized (1300x700), with 500x500 sectors
WORLD_WIDTH = WIDTH * 500  # 1300 * 500 = 650,000
WORLD_HEIGHT = HEIGHT * 500  # 700 * 500 = 350,000
SECTORS_X = 500
SECTORS_Y = 500
SECTOR_WIDTH = WORLD_WIDTH // SECTORS_X  # 1300 (screen width)
SECTOR_HEIGHT = WORLD_HEIGHT // SECTORS_Y  # 700 (screen height)

# World position (theoretical coordinates in world space)
# Start at center of world: (325000, 175000) which is sector (250, 250)
world_x = WORLD_WIDTH // 2  # 325000
world_y = WORLD_HEIGHT // 2  # 175000

# Current sector (calculated from world position)
current_sector_x = 250
current_sector_y = 250

# Circle in starting sector (world coordinates)
CIRCLE_WORLD_X = WORLD_WIDTH // 2  # Center of starting sector
CIRCLE_WORLD_Y = WORLD_HEIGHT // 2  # Center of starting sector
CIRCLE_RADIUS = 30

# Selection and targeting
circle_selected = False
circle_targeted = False
mouse_x = 0
mouse_y = 0

# Colors
GREY = (128, 128, 128)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
BLUE = (0, 0, 255)

# Box dimensions
BOX_WIDTH = 500
BOX_HEIGHT = 200

# Calculate box position to center it
BOX_X = (WIDTH - BOX_WIDTH) // 2
BOX_Y = (HEIGHT - BOX_HEIGHT) // 2

# Movement speed
MOVE_SPEED = 300  # pixels per second

# Rotation speed
ROTATION_SPEED = 90  # degrees per second

# Laser speed
LASER_SPEED = 500  # pixels per second

# Enemy settings
ENEMY_SIZE = 40
ENEMY_SPEED = 100  # pixels per second
ENEMY_SLOW_SPEED = 30  # pixels per second for slow movement
ENEMY_MAX_HEALTH = 5
ENEMY_SHOOT_CHANCE = 0.1  # 10% chance to target box

# Target settings
TARGET_SIZE = 20
TARGET_X = BOX_X + BOX_WIDTH // 2 - TARGET_SIZE // 2
TARGET_Y = BOX_Y + BOX_HEIGHT - TARGET_SIZE // 2

# Enemy projectile settings
ENEMY_PROJECTILE_SPEED = 200  # pixels per second
ENEMY_SHOOT_INTERVAL = 0.5  # seconds between shots

# Initialize font for FPS counter
font = pygame.font.Font(None, 36)

# Center point for rotation
CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

class Star:
    def __init__(self, x, y, size, twinkle_speed):
        self.x = x
        self.y = y
        self.size = size
        self.twinkle_speed = twinkle_speed
        self.angle = random.uniform(0, 2 * math.pi)
        self.brightness = random.uniform(0.3, 1.0)
        self.min_brightness = 0.2
        self.max_brightness = 1.0
    
    def update(self, dt):
        # Animate twinkling using sine wave
        self.angle += self.twinkle_speed * dt
        # Map sine wave (-1 to 1) to brightness range
        self.brightness = (self.min_brightness + 
                          (self.max_brightness - self.min_brightness) * 
                          (math.sin(self.angle) + 1) / 2)
    
    def move(self, dx, dy):
        """Move the star by the given delta"""
        self.x += dx
        self.y += dy
    
    def rotate(self, angle_radians, center_x, center_y):
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
    
    def is_off_screen(self):
        """Check if star is off screen"""
        return (self.x < -10 or self.x > WIDTH + 10 or 
                self.y < -10 or self.y > HEIGHT + 10)
    
    def draw(self, surface):
        # Calculate color based on brightness
        color_value = int(255 * self.brightness)
        color = (color_value, color_value, color_value)
        
        # Draw star as a small circle
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)

class Laser:
    def __init__(self, start_x, start_y, target_x, target_y):
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        
        # Calculate direction vector
        dx = target_x - start_x
        dy = target_y - start_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            self.vx = (dx / distance) * LASER_SPEED
            self.vy = (dy / distance) * LASER_SPEED
        else:
            self.vx = 0
            self.vy = 0
        
        self.reached_target = False
    
    def update(self, dt):
        """Update laser position and check if it reached the target"""
        if not self.reached_target:
            # Move toward target
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            # Check if reached target (within a small threshold)
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance_to_target = math.sqrt(dx * dx + dy * dy)
            
            if distance_to_target < 5:  # Threshold for reaching center
                self.reached_target = True
    
    def draw(self, surface):
        """Draw the laser as a 4x4 red rectangle"""
        if not self.reached_target:
            # Draw laser as a small red square
            pygame.draw.rect(surface, RED, (int(self.x) - 2, int(self.y) - 2, 4, 4))
    
    def get_rect(self):
        """Get a rect for collision detection"""
        return pygame.Rect(int(self.x) - 2, int(self.y) - 2, 4, 4)

class EnemyProjectile:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        
        # Calculate direction vector
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            self.vx = (dx / distance) * ENEMY_PROJECTILE_SPEED
            self.vy = (dy / distance) * ENEMY_PROJECTILE_SPEED
        else:
            self.vx = 0
            self.vy = 0
        
        self.size = 4
        self.active = True
    
    def update(self, dt):
        """Update projectile position"""
        if self.active:
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            # Check if off screen
            if (self.x < -10 or self.x > WIDTH + 10 or 
                self.y < -10 or self.y > HEIGHT + 10):
                self.active = False
    
    def get_rect(self):
        """Get collision rectangle"""
        return pygame.Rect(int(self.x) - 2, int(self.y) - 2, self.size, self.size)
    
    def draw(self, surface):
        """Draw projectile as orange square"""
        if self.active:
            pygame.draw.rect(surface, ORANGE, 
                           (int(self.x) - 2, int(self.y) - 2, self.size, self.size))

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.base_size = ENEMY_SIZE
        self.size = ENEMY_SIZE
        self.health = ENEMY_MAX_HEALTH
        self.alive = True
        
        # Behavior state
        self.behavior_state = "attack_1_go_to_target"
        self.color = ORANGE  # ORANGE or BLUE
        
        # Size scaling
        self.size_scale = 1.0
        self.initial_distance_to_target = 0
        self.distance_traveled = 0
        
        # Movement
        self.vx = 0
        self.vy = 0
        
        # Targeting state (for old random behavior)
        self.targeting_box = False
        self.shoot_timer = 0
    
    def is_partially_in_box(self):
        """Check if any part of enemy overlaps with the box"""
        enemy_rect = self.get_rect()
        box_rect = pygame.Rect(BOX_X, BOX_Y, BOX_WIDTH, BOX_HEIGHT)
        return enemy_rect.colliderect(box_rect)
    
    def update(self, dt):
        """Update enemy position and movement"""
        if not self.alive:
            return
        
        # Handle behavior states
        if self.behavior_state == "attack_1_go_to_target":
            # Move toward target
            target_center_x = TARGET_X + TARGET_SIZE // 2
            target_center_y = TARGET_Y + TARGET_SIZE // 2
            enemy_center_x = self.x + self.base_size * self.size_scale // 2
            enemy_center_y = self.y + self.base_size * self.size_scale // 2
            
            dx = target_center_x - enemy_center_x
            dy = target_center_y - enemy_center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Check if enemy is in the box
            in_box = self.is_partially_in_box()
            
            # Only scale size when in the box
            if in_box:
                # Initialize distance tracking when first entering box
                if self.initial_distance_to_target == 0:
                    self.initial_distance_to_target = distance
                
                # Calculate size scale based on progress (1.0 to 3.0)
                if self.initial_distance_to_target > 0:
                    progress = 1.0 - (distance / self.initial_distance_to_target)
                    progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
                    self.size_scale = 1.0 + (progress * 2.0)  # Scale from 1.0 to 3.0
                    self.size = int(self.base_size * self.size_scale)
            else:
                # Keep normal size when outside box
                self.size_scale = 1.0
                self.size = self.base_size
                # Reset distance tracking when leaving box
                self.initial_distance_to_target = 0
            
            if distance > 0:
                self.vx = (dx / distance) * ENEMY_SPEED
                self.vy = (dy / distance) * ENEMY_SPEED
            else:
                self.vx = 0
                self.vy = 0
            
            # Check if reached target
            if enemy_center_y >= target_center_y and abs(dx) < TARGET_SIZE + 10:
                self.behavior_state = "attack_1_drop_down"
                self.vx = 0
                self.vy = ENEMY_SPEED  # Move down
        
        elif self.behavior_state == "attack_1_drop_down":
            # Continue moving down
            self.vx = 0
            self.vy = ENEMY_SPEED
            
            # Check if below box
            if self.y > BOX_Y + BOX_HEIGHT + 50:
                # Turn blue and teleport
                self.color = BLUE
                self.behavior_state = "attack_1_teleport"
                # Reset size to normal
                self.size_scale = 1.0
                self.size = self.base_size
                # Teleport to right edge
                self.x = WIDTH - self.size - 10
                self.y = HEIGHT // 2 - self.size // 2
                self.vx = 0
                self.vy = 0
        
        elif self.behavior_state == "attack_1_teleport":
            # Already teleported, now move to center
            self.behavior_state = "attack_1_move_to_center"
            # Calculate direction to center
            center_x = BOX_CENTER_X
            center_y = BOX_CENTER_Y
            enemy_center_x = self.x + self.size // 2
            enemy_center_y = self.y + self.size // 2
            
            dx = center_x - enemy_center_x
            dy = center_y - enemy_center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance > 0:
                self.vx = (dx / distance) * ENEMY_SLOW_SPEED
                self.vy = (dy / distance) * ENEMY_SLOW_SPEED
            else:
                self.vx = 0
                self.vy = 0
        
        elif self.behavior_state == "attack_1_move_to_center":
            # Move slowly toward center
            center_x = BOX_CENTER_X
            center_y = BOX_CENTER_Y
            enemy_center_x = self.x + self.size // 2
            enemy_center_y = self.y + self.size // 2
            
            dx = center_x - enemy_center_x
            dy = center_y - enemy_center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance > 5:
                self.vx = (dx / distance) * ENEMY_SLOW_SPEED
                self.vy = (dy / distance) * ENEMY_SLOW_SPEED
            else:
                # Reached center, stop
                self.vx = 0
                self.vy = 0
        
        # Move enemy
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Keep enemy on screen (don't bounce, just clamp)
        self.x = max(0, min(WIDTH - self.size, self.x))
        self.y = max(0, min(HEIGHT - self.size, self.y))
        
        # Update shoot timer
        self.shoot_timer += dt
    
    def can_shoot(self):
        """Check if enemy can shoot (must be orange, partially in box, and shoot timer ready)"""
        return (self.color != BLUE and 
                self.is_partially_in_box() and 
                self.shoot_timer >= ENEMY_SHOOT_INTERVAL)
    
    def shoot(self):
        """Create a projectile toward the target"""
        if self.can_shoot():
            self.shoot_timer = 0
            enemy_center_x = self.x + self.size // 2
            enemy_center_y = self.y + self.size // 2
            target_center_x = TARGET_X + TARGET_SIZE // 2
            target_center_y = TARGET_Y + TARGET_SIZE // 2
            return EnemyProjectile(enemy_center_x, enemy_center_y, 
                                  target_center_x, target_center_y)
        return None
    
    def take_damage(self):
        """Take damage from a laser hit"""
        self.health -= 1
        if self.health <= 0:
            self.alive = False
    
    def get_rect(self):
        """Get the enemy's collision rectangle"""
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)
    
    def draw(self, surface):
        """Draw the enemy as a filled square (orange or blue)"""
        if self.alive:
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))

def draw_arrowhead(surface, color, position, angle, arrow_size=12):
    """Draw just an arrowhead (no tail) pointing in the given direction"""
    # Arrowhead points - using smaller angle for more pointed tip
    # π/10 = 18 degrees per side, making a 36-degree total angle (more pointed)
    tip = position
    arrow1 = (
        tip[0] - arrow_size * math.cos(angle - math.pi / 10),
        tip[1] - arrow_size * math.sin(angle - math.pi / 10)
    )
    arrow2 = (
        tip[0] - arrow_size * math.cos(angle + math.pi / 10),
        tip[1] - arrow_size * math.sin(angle + math.pi / 10)
    )
    
    # Draw arrowhead triangle
    pygame.draw.polygon(surface, color, [tip, arrow1, arrow2])

def get_closest_box_side(enemy_x, enemy_y):
    """Determine which side of the box the enemy is closest to
    Returns: 'left', 'right', 'top', 'bottom', or None if inside box
    """
    # Check if enemy is inside the box
    if (BOX_X <= enemy_x <= BOX_X + BOX_WIDTH and 
        BOX_Y <= enemy_y <= BOX_Y + BOX_HEIGHT):
        return None
    
    # Calculate distances to each side (perpendicular distance)
    # For left/right: use x distance, but clamp y to box range
    clamped_y = max(BOX_Y, min(BOX_Y + BOX_HEIGHT, enemy_y))
    dist_left = math.sqrt((enemy_x - BOX_X) ** 2 + (enemy_y - clamped_y) ** 2)
    dist_right = math.sqrt((enemy_x - (BOX_X + BOX_WIDTH)) ** 2 + (enemy_y - clamped_y) ** 2)
    
    # For top/bottom: use y distance, but clamp x to box range
    clamped_x = max(BOX_X, min(BOX_X + BOX_WIDTH, enemy_x))
    dist_top = math.sqrt((enemy_x - clamped_x) ** 2 + (enemy_y - BOX_Y) ** 2)
    dist_bottom = math.sqrt((enemy_x - clamped_x) ** 2 + (enemy_y - (BOX_Y + BOX_HEIGHT)) ** 2)
    
    # Find minimum distance
    min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
    
    if min_dist == dist_left:
        return 'left'
    elif min_dist == dist_right:
        return 'right'
    elif min_dist == dist_top:
        return 'top'
    else:
        return 'bottom'

def create_star_at_edge(edge):
    """Create a new star at a specific edge of the screen
    edge: 'left', 'right', 'top', 'bottom'
    """
    size = random.randint(1, 3)
    twinkle_speed = random.uniform(0.5, 2.0)
    
    if edge == 'left':
        x = -10
        y = random.randint(0, HEIGHT)
    elif edge == 'right':
        x = WIDTH + 10
        y = random.randint(0, HEIGHT)
    elif edge == 'top':
        x = random.randint(0, WIDTH)
        y = -10
    else:  # bottom
        x = random.randint(0, WIDTH)
        y = HEIGHT + 10
    
    return Star(x, y, size, twinkle_speed)

# Create stars
NUM_STARS = 200
stars = []
for _ in range(NUM_STARS):
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    size = random.randint(1, 3)
    twinkle_speed = random.uniform(0.5, 2.0)
    stars.append(Star(x, y, size, twinkle_speed))

# Calculate box center and bottom corners for lasers
BOX_CENTER_X = BOX_X + BOX_WIDTH // 2
BOX_CENTER_Y = BOX_Y + BOX_HEIGHT // 2
BOX_BOTTOM_LEFT_X = BOX_X
BOX_BOTTOM_LEFT_Y = BOX_Y + BOX_HEIGHT
BOX_BOTTOM_RIGHT_X = BOX_X + BOX_WIDTH
BOX_BOTTOM_RIGHT_Y = BOX_Y + BOX_HEIGHT

# Lasers list
lasers = []

# Enemy projectiles list
enemy_projectiles = []

# Create enemy at top right of screen
enemy = Enemy(WIDTH - ENEMY_SIZE - 20, 20)

# Main game loop
running = True
clock = pygame.time.Clock()
dt = 0
active_mode = None  # 'movement', 'rotation', or None

while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                # Fire lasers from bottom corners
                lasers.append(Laser(BOX_BOTTOM_LEFT_X, BOX_BOTTOM_LEFT_Y, 
                                   BOX_CENTER_X, BOX_CENTER_Y))
                lasers.append(Laser(BOX_BOTTOM_RIGHT_X, BOX_BOTTOM_RIGHT_Y, 
                                   BOX_CENTER_X, BOX_CENTER_Y))
            elif event.key == pygame.K_t:
                # Target selected object
                if circle_selected:
                    circle_targeted = True
        elif event.type == pygame.MOUSEMOTION:
            # Track mouse position only within the box
            mouse_pos = pygame.mouse.get_pos()
            if (BOX_X <= mouse_pos[0] <= BOX_X + BOX_WIDTH and 
                BOX_Y <= mouse_pos[1] <= BOX_Y + BOX_HEIGHT):
                mouse_x = mouse_pos[0]
                mouse_y = mouse_pos[1]
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_pos = pygame.mouse.get_pos()
                # Check if click is within the box
                if (BOX_X <= mouse_pos[0] <= BOX_X + BOX_WIDTH and 
                    BOX_Y <= mouse_pos[1] <= BOX_Y + BOX_HEIGHT):
                    # Convert screen click to world coordinates
                    click_world_x = world_x + (mouse_pos[0] - WIDTH // 2)
                    click_world_y = world_y + (mouse_pos[1] - HEIGHT // 2)
                    
                    # Check if click is on circle
                    dx = click_world_x - CIRCLE_WORLD_X
                    dy = click_world_y - CIRCLE_WORLD_Y
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    if distance <= CIRCLE_RADIUS:
                        circle_selected = True
                    else:
                        circle_selected = False
                        circle_targeted = False
    
    # Calculate delta time and FPS for smooth animation
    milliseconds = clock.tick(60)
    dt = milliseconds / 1000.0  # Convert to seconds
    fps = 1000.0 / milliseconds if milliseconds > 0 else 0  # Calculate FPS
    
    # Get keyboard input
    keys = pygame.key.get_pressed()
    dx = 0
    dy = 0
    rotation_angle = 0
    
    # Check if any movement key is pressed
    movement_pressed = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
    # Check if any rotation key is pressed
    rotation_pressed = keys[pygame.K_q] or keys[pygame.K_e]
    
    # Reset active mode if all keys are released
    if not movement_pressed and not rotation_pressed:
        active_mode = None
    
    # Set active mode if no mode is active and a key is pressed
    if active_mode is None:
        if movement_pressed:
            active_mode = 'movement'
        elif rotation_pressed:
            active_mode = 'rotation'
    
    # Only process input for the active mode
    if active_mode == 'movement':
        # Calculate movement direction (stars move opposite to key press)
        # Only one key works at a time - priority: W, S, A, D
        if keys[pygame.K_w]:  # Move up - stars move down
            dy = MOVE_SPEED * dt
        elif keys[pygame.K_s]:  # Move down - stars move up
            dy = -MOVE_SPEED * dt
        elif keys[pygame.K_a]:  # Move left - stars move right
            dx = MOVE_SPEED * dt
        elif keys[pygame.K_d]:  # Move right - stars move left
            dx = -MOVE_SPEED * dt
    elif active_mode == 'rotation':
        # Calculate rotation (Q = clockwise/right, E = counter-clockwise/left)
        # Only one key works at a time - priority: Q, E
        if keys[pygame.K_q]:  # Rotate right (clockwise)
            rotation_angle = math.radians(ROTATION_SPEED * dt)
        elif keys[pygame.K_e]:  # Rotate left (counter-clockwise)
            rotation_angle = -math.radians(ROTATION_SPEED * dt)
    
    # Update world position based on movement
    # Movement is opposite to star movement (camera effect)
    if dx != 0 or dy != 0:
        world_x -= dx  # Move opposite to star movement
        world_y -= dy
        
        # Wrap world position (toroidal topology)
        world_x = world_x % WORLD_WIDTH
        world_y = world_y % WORLD_HEIGHT
        # Handle negative values
        if world_x < 0:
            world_x += WORLD_WIDTH
        if world_y < 0:
            world_y += WORLD_HEIGHT
        
        # Calculate current sector from world position (with wrapping)
        current_sector_x = int(world_x // SECTOR_WIDTH) % SECTORS_X
        current_sector_y = int(world_y // SECTOR_HEIGHT) % SECTORS_Y
    
    # Move stars
    for star in stars:
        star.move(dx, dy)
        star.update(dt)
    
    # Rotate stars around center
    if rotation_angle != 0:
        for star in stars:
            star.rotate(rotation_angle, CENTER_X, CENTER_Y)
    
    # Remove stars that went off screen and create new ones
    stars_to_remove = []
    for star in stars:
        if star.is_off_screen():
            stars_to_remove.append(star)
    
    for star in stars_to_remove:
        stars.remove(star)
        # Determine which edge(s) to spawn from based on movement direction
        # Stars move opposite to key press, so spawn from opposite edge(s)
        # Handle diagonal movement by spawning from both edges
        edges_to_spawn = []
        
        if dx > 0:  # Moving left (A key) - stars move right, spawn from left
            edges_to_spawn.append('left')
        elif dx < 0:  # Moving right (D key) - stars move left, spawn from right
            edges_to_spawn.append('right')
        
        if dy > 0:  # Moving up (W key) - stars move down, spawn from top
            edges_to_spawn.append('top')
        elif dy < 0:  # Moving down (S key) - stars move up, spawn from bottom
            edges_to_spawn.append('bottom')
        
        # If no movement, spawn from random edge
        if not edges_to_spawn:
            edges_to_spawn = [random.choice(['left', 'right', 'top', 'bottom'])]
        
        # Spawn from all determined edges
        for edge in edges_to_spawn:
            stars.append(create_star_at_edge(edge))
    
    # Maintain minimum star count
    while len(stars) < NUM_STARS:
        # Spawn from edge(s) opposite to movement, or random if not moving
        edges_to_spawn = []
        
        if dx > 0:
            edges_to_spawn.append('left')
        elif dx < 0:
            edges_to_spawn.append('right')
        
        if dy > 0:
            edges_to_spawn.append('top')
        elif dy < 0:
            edges_to_spawn.append('bottom')
        
        if not edges_to_spawn:
            edges_to_spawn = [random.choice(['left', 'right', 'top', 'bottom'])]
        
        # Spawn from all determined edges
        for edge in edges_to_spawn:
            stars.append(create_star_at_edge(edge))
    
    # Update lasers and remove ones that reached target
    for laser in lasers:
        laser.update(dt)
    
    # Check laser-enemy collisions
    if enemy.alive:
        enemy_rect = enemy.get_rect()
        lasers_to_remove = []
        for laser in lasers:
            if not laser.reached_target:
                laser_rect = laser.get_rect()
                if enemy_rect.colliderect(laser_rect):
                    enemy.take_damage()
                    lasers_to_remove.append(laser)
        
        # Remove lasers that hit the enemy
        for laser in lasers_to_remove:
            if laser in lasers:
                lasers.remove(laser)
    
    # Remove lasers that reached the target
    lasers = [laser for laser in lasers if not laser.reached_target]
    
    # Update enemy
    if enemy.alive:
        enemy.update(dt)
        # Try to shoot if can shoot (orange and in box)
        if enemy.can_shoot():
            projectile = enemy.shoot()
            if projectile:
                enemy_projectiles.append(projectile)
    
    # Update enemy projectiles
    for projectile in enemy_projectiles:
        projectile.update(dt)
    
    # Remove inactive enemy projectiles
    enemy_projectiles = [p for p in enemy_projectiles if p.active]
    
    # Check enemy projectile-target collisions
    target_rect = pygame.Rect(TARGET_X, TARGET_Y, TARGET_SIZE, TARGET_SIZE)
    for projectile in enemy_projectiles:
        if projectile.active:
            proj_rect = projectile.get_rect()
            if target_rect.colliderect(proj_rect):
                projectile.active = False
                # Target hit - could add game over or damage logic here
    
    # Fill the screen with grey
    screen.fill(GREY)
    
    # Draw stars
    for star in stars:
        star.draw(screen)
    
    # Draw lasers
    for laser in lasers:
        laser.draw(screen)
    
    # Draw enemy
    if enemy.alive:
        enemy.draw(screen)
    
    # Draw enemy projectiles
    for projectile in enemy_projectiles:
        projectile.draw(screen)
    
    # Draw the black box outline in the center (on top of stars)
    pygame.draw.rect(screen, BLACK, (BOX_X, BOX_Y, BOX_WIDTH, BOX_HEIGHT), 4)
    
    # Draw target cube at center of bottom edge
    pygame.draw.rect(screen, BLACK, (TARGET_X, TARGET_Y, TARGET_SIZE, TARGET_SIZE))
    
    # Draw enemy indicator arrow if enemy is alive and outside the box
    if enemy.alive:
        enemy_center_x = enemy.x + enemy.size // 2
        enemy_center_y = enemy.y + enemy.size // 2
        closest_side = get_closest_box_side(enemy_center_x, enemy_center_y)
        
        if closest_side is not None:
            # Determine arrow position on the inner edge of the box based on enemy position
            arrow_offset = 8  # Distance from inner edge
            if closest_side == 'left':
                arrow_x = BOX_X + arrow_offset
                # Position arrow vertically based on enemy, clamped to box height
                arrow_y = max(BOX_Y + 10, min(BOX_Y + BOX_HEIGHT - 10, enemy_center_y))
            elif closest_side == 'right':
                arrow_x = BOX_X + BOX_WIDTH - arrow_offset
                arrow_y = max(BOX_Y + 10, min(BOX_Y + BOX_HEIGHT - 10, enemy_center_y))
            elif closest_side == 'top':
                arrow_x = max(BOX_X + 10, min(BOX_X + BOX_WIDTH - 10, enemy_center_x))
                arrow_y = BOX_Y + arrow_offset
            else:  # bottom
                arrow_x = max(BOX_X + 10, min(BOX_X + BOX_WIDTH - 10, enemy_center_x))
                arrow_y = BOX_Y + BOX_HEIGHT - arrow_offset
            
            # Calculate angle pointing toward enemy
            dx = enemy_center_x - arrow_x
            dy = enemy_center_y - arrow_y
            angle = math.atan2(dy, dx)
            
            # Draw arrowhead pointing toward enemy
            draw_arrowhead(screen, RED, (arrow_x, arrow_y), angle, 12)
    
    # Draw circle in starting sector (convert world coords to screen coords)
    # Screen center represents current world position
    circle_screen_x = (CIRCLE_WORLD_X - world_x) + WIDTH // 2
    circle_screen_y = (CIRCLE_WORLD_Y - world_y) + HEIGHT // 2
    
    # Only draw if circle is on screen
    if (-CIRCLE_RADIUS <= circle_screen_x <= WIDTH + CIRCLE_RADIUS and 
        -CIRCLE_RADIUS <= circle_screen_y <= HEIGHT + CIRCLE_RADIUS):
        # Draw circle
        pygame.draw.circle(screen, BLACK, (int(circle_screen_x), int(circle_screen_y)), CIRCLE_RADIUS)
        
        # Draw selection indicator if selected
        if circle_selected:
            pygame.draw.circle(screen, WHITE, (int(circle_screen_x), int(circle_screen_y)), CIRCLE_RADIUS + 3, 2)
    
    # Draw arrowhead pointing to targeted circle (if targeted and not visible in box)
    if circle_targeted:
        # Check if circle is visible in the box
        circle_in_box = (BOX_X - CIRCLE_RADIUS <= circle_screen_x <= BOX_X + BOX_WIDTH + CIRCLE_RADIUS and
                        BOX_Y - CIRCLE_RADIUS <= circle_screen_y <= BOX_Y + BOX_HEIGHT + CIRCLE_RADIUS)
        
        if not circle_in_box:
            # Determine which side of box is closest to circle using world coordinates
            box_world_left = world_x - BOX_WIDTH // 2
            box_world_right = world_x + BOX_WIDTH // 2
            box_world_top = world_y - BOX_HEIGHT // 2
            box_world_bottom = world_y + BOX_HEIGHT // 2
            
            # Calculate distances to each side
            dist_left = abs(CIRCLE_WORLD_X - box_world_left)
            dist_right = abs(CIRCLE_WORLD_X - box_world_right)
            dist_top = abs(CIRCLE_WORLD_Y - box_world_top)
            dist_bottom = abs(CIRCLE_WORLD_Y - box_world_bottom)
            
            min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
            
            # Position arrow on inner edge of box
            arrow_offset = 8
            if min_dist == dist_left:
                arrow_x = BOX_X + arrow_offset
                # Position based on circle's screen position, clamped to box
                arrow_y = max(BOX_Y + 10, min(BOX_Y + BOX_HEIGHT - 10, circle_screen_y))
            elif min_dist == dist_right:
                arrow_x = BOX_X + BOX_WIDTH - arrow_offset
                arrow_y = max(BOX_Y + 10, min(BOX_Y + BOX_HEIGHT - 10, circle_screen_y))
            elif min_dist == dist_top:
                arrow_x = max(BOX_X + 10, min(BOX_X + BOX_WIDTH - 10, circle_screen_x))
                arrow_y = BOX_Y + arrow_offset
            else:  # bottom
                arrow_x = max(BOX_X + 10, min(BOX_X + BOX_WIDTH - 10, circle_screen_x))
                arrow_y = BOX_Y + BOX_HEIGHT - arrow_offset
            
            # Calculate angle pointing toward circle
            dx = circle_screen_x - arrow_x
            dy = circle_screen_y - arrow_y
            angle = math.atan2(dy, dx)
            
            # Draw arrowhead pointing toward circle
            draw_arrowhead(screen, RED, (arrow_x, arrow_y), angle, 12)
    
    # Draw FPS counter in top right corner
    fps_text = font.render(f"FPS: {int(fps)}", True, BLACK)
    fps_rect = fps_text.get_rect()
    fps_rect.topright = (WIDTH - 10, 10)
    screen.blit(fps_text, fps_rect)
    
    # Draw sector information below FPS
    sector_text = font.render(f"Sector: ({current_sector_x}, {current_sector_y})", True, BLACK)
    sector_rect = sector_text.get_rect()
    sector_rect.topright = (WIDTH - 10, 50)
    screen.blit(sector_text, sector_rect)
    
    # Update the display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
sys.exit()

