"""Game constants and configuration"""
import pygame

# Screen dimensions
SCREEN_WIDTH = 1300
SCREEN_HEIGHT = 700

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Define regions as tuples: ((top_left_x, top_left_y), (bottom_right_x, bottom_right_y))
REGIONS = {
    'left_top_region': ((0, 0), (360, 76)),
    'left_middle_region': ((0, 77), (360, 460)),
    'left_bottom_right_region': ((141, 461), (360, 700)),
    'left_bottom_left_a_region': ((0, 461), (140, 622)),
    'left_bottom_left_b_region': ((0, 623), (140, 700)),
    'central_top_region': ((361, 0), (942, 76)),
    'central_middle_region': ((361, 77), (942, 622)),
    'central_bottom_region': ((361, 623), (942, 700)),
    'right_top_region': ((943, 0), (1300, 76)),
    'right_bottom_region': ((943, 77), (1300, 700))
}

# Room configuration
ROOM_IMAGE_PATH = 'region_images/central_middle/'
ROOM_IMAGE_POSITION = (420, 121)  # Standard position for all room images

# Room masks (polygon coordinates for screen masking)
# These are screen coordinates
MASK_FOR_CONTROL_ROOM = [
    (424, 214),
    (490, 231),
    (815, 232),
    (881, 216),
    (879, 366),
    (799, 343),
    (504, 344),
    (424, 369)
]

# Debug viewport polygon (red outline for debugging)
# These are screen coordinates - same as MASK_FOR_CONTROL_ROOM
DEBUG_VIEWPORT = [
    (424, 214),
    (490, 231),
    (815, 232),
    (881, 216),
    (879, 366),
    (799, 343),
    (504, 344),
    (424, 369)
]

# Game settings
FPS = 60
DEBUG_KEY = pygame.K_F1
ESCAPE_KEY = pygame.K_ESCAPE

