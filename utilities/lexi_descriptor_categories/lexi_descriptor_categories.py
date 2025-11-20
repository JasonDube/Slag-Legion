import pygame
import json
import os

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1300
WINDOW_HEIGHT = 700
BLACK = (0, 0, 0)
LIGHT_GREY = (200, 200, 200)
WHITE = (255, 255, 255)
DARK_GREY = (100, 100, 100)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
SELECTED_BLUE = (0, 100, 200)
RED = (255, 0, 0)
PINK = (255, 192, 203)

# Panel dimensions
LEFT_PANEL_WIDTH = 700
LEFT_PANEL_HEIGHT = 700
LEFT_PANEL_X = 0
LEFT_PANEL_Y = 0

RIGHT_PANEL_WIDTH = 600  # 1300 - 700
RIGHT_PANEL_HEIGHT = 700
RIGHT_PANEL_X = 700
RIGHT_PANEL_Y = 0

# Button dimensions
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 25
BUTTON_PADDING = 2

# Scrollbar dimensions
SCROLLBAR_WIDTH = 20

# Right detail panel (light blue area) - calculated after constants are defined
DELETE_BUTTON_SIZE = 25
RIGHT_DETAIL_PANEL_X = RIGHT_PANEL_X + SCROLLBAR_WIDTH + BUTTON_PADDING + BUTTON_WIDTH + BUTTON_PADDING + DELETE_BUTTON_SIZE + BUTTON_PADDING
RIGHT_DETAIL_PANEL_WIDTH = WINDOW_WIDTH - RIGHT_DETAIL_PANEL_X
RIGHT_DETAIL_PANEL_HEIGHT = RIGHT_PANEL_HEIGHT
RIGHT_DETAIL_PANEL_Y = RIGHT_PANEL_Y
SCROLLBAR_COLOR = (80, 80, 80)
SCROLLBAR_THUMB_COLOR = (120, 120, 120)
SCROLLBAR_DISABLED_COLOR = (60, 60, 60)  # Darker when disabled

# Get the project root directory (parent of utilities folder)
# This file is now in utilities/lexi_descriptor_categories/, so we need to go up two levels
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESCRIPTORS_FILE = os.path.join(PROJECT_ROOT, "lexi_descriptors.json")

# Get the utility's own folder (where this file and log will be stored)
UTILITY_FOLDER = os.path.dirname(os.path.abspath(__file__))


class LexiButton:
    def __init__(self, text, x, y, width=None):
        self.text = text
        if width is None:
            width = BUTTON_WIDTH
        self.rect = pygame.Rect(x, y, width, BUTTON_HEIGHT)
        self.font = pygame.font.Font(None, 18)
        self.selected = False
        self.assigned = False  # Whether this descriptor is assigned to a category
    
    def draw(self, screen):
        # Fill with pink
        pygame.draw.rect(screen, PINK, self.rect)
        
        # Draw outline - red if assigned, blue if selected, grey otherwise
        if self.assigned:
            outline_color = RED
            outline_width = 3
        elif self.selected:
            outline_color = SELECTED_BLUE
            outline_width = 3
        else:
            outline_color = DARK_GREY
            outline_width = 2
        pygame.draw.rect(screen, outline_color, self.rect, outline_width)
        
        # Draw text left-justified
        text_surface = self.font.render(self.text, True, BLACK)
        text_x = self.rect.x + 5  # Small padding from left edge
        text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        screen.blit(text_surface, (text_x, text_y))
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


# Keep DescriptorButton as alias for backward compatibility
DescriptorButton = LexiButton


class DialogButton:
    def __init__(self, text, x, y, width, height):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.Font(None, 24)
    
    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, DARK_GREY, self.rect, 2)
        
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class DeleteButton:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.font = pygame.font.Font(None, 20)
    
    def draw(self, screen):
        pygame.draw.rect(screen, (200, 100, 100), self.rect)
        pygame.draw.rect(screen, DARK_GREY, self.rect, 2)
        
        # Draw 'x' centered
        x_text = self.font.render("x", True, WHITE)
        text_rect = x_text.get_rect(center=self.rect.center)
        screen.blit(x_text, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class ArrowButton:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 25)
    
    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, DARK_GREY, self.rect, 2)
        
        # Draw right arrow using lines
        center_x = self.rect.centerx
        center_y = self.rect.centery
        arrow_size = 6
        
        # Arrow points: right point, top left, bottom left (pointing right)
        points = [
            (center_x + arrow_size, center_y),
            (center_x - arrow_size, center_y - arrow_size),
            (center_x - arrow_size, center_y + arrow_size)
        ]
        pygame.draw.polygon(screen, BLACK, points)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class NewCategoryDialog:
    def __init__(self, screen_width, screen_height):
        self.width = 400
        self.height = 150
        self.x = (screen_width - self.width) // 2
        self.y = (screen_height - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        self.input_text = ""
        self.input_active = True
        self.font = pygame.font.Font(None, 24)
        self.cursor_timer = 0
        self.cursor_visible = True
        
        # Input field
        input_padding = 10
        self.input_rect = pygame.Rect(
            self.x + input_padding,
            self.y + 40,
            self.width - input_padding * 2,
            30
        )
        
        # Buttons
        button_width = 80
        button_height = 30
        button_y = self.y + self.height - button_height - 10
        button_spacing = 20
        
        ok_x = self.x + self.width - button_width * 2 - button_spacing - 10
        cancel_x = self.x + self.width - button_width - 10
        
        self.ok_button = DialogButton("OK", ok_x, button_y, button_width, button_height)
        self.cancel_button = DialogButton("Cancel", cancel_x, button_y, button_width, button_height)
    
    def handle_event(self, event, dt):
        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    return "ok"
                elif event.key == pygame.K_ESCAPE:
                    return "cancel"
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.input_text += event.unicode
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.input_rect.collidepoint(event.pos):
                    self.input_active = True
                else:
                    self.input_active = False
                
                if self.ok_button.is_clicked(event.pos):
                    return "ok"
                elif self.cancel_button.is_clicked(event.pos):
                    return "cancel"
        
        return None
    
    def draw(self, screen):
        # Dialog background
        pygame.draw.rect(screen, (240, 240, 240), self.rect)
        pygame.draw.rect(screen, DARK_GREY, self.rect, 3)
        
        # Title
        title_font = pygame.font.Font(None, 28)
        title_text = title_font.render("New Category", True, BLACK)
        title_x = self.x + (self.width - title_text.get_width()) // 2
        screen.blit(title_text, (title_x, self.y + 10))
        
        # Input field
        input_bg_color = (255, 255, 255) if self.input_active else (250, 250, 250)
        pygame.draw.rect(screen, input_bg_color, self.input_rect)
        pygame.draw.rect(screen, DARK_GREY, self.input_rect, 2)
        
        # Input text
        if self.input_text:
            text_surface = self.font.render(self.input_text, True, BLACK)
            text_x = self.input_rect.x + 5
            text_y = self.input_rect.y + (self.input_rect.height - text_surface.get_height()) // 2
            screen.blit(text_surface, (text_x, text_y))
            
            # Cursor
            if self.input_active and self.cursor_visible:
                cursor_x = text_x + text_surface.get_width()
                cursor_rect = pygame.Rect(cursor_x, text_y, 2, text_surface.get_height())
                pygame.draw.rect(screen, BLACK, cursor_rect)
        elif self.input_active and self.cursor_visible:
            cursor_x = self.input_rect.x + 5
            cursor_y = self.input_rect.y + (self.input_rect.height - self.font.get_height()) // 2
            cursor_rect = pygame.Rect(cursor_x, cursor_y, 2, self.font.get_height())
            pygame.draw.rect(screen, BLACK, cursor_rect)
        
        # Buttons
        self.ok_button.draw(screen)
        self.cancel_button.draw(screen)


def load_lexi_descriptors():
    """Load Lexi's mood/state descriptors from JSON file."""
    try:
        with open(DESCRIPTORS_FILE, 'r') as f:
            data = json.load(f)
            descriptors = data.get("llm_descriptors", [])
            # Sort alphabetically
            descriptors.sort()
            return descriptors
    except FileNotFoundError:
        print(f"Warning: {DESCRIPTORS_FILE} not found. Returning empty list.")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Error parsing {DESCRIPTORS_FILE}. Returning empty list.")
        return []


def load_variation_keys():
    """Load variation keys from lexi_system.py variations dictionary."""
    # These are the keys from the variations dictionary in _match_descriptor_to_animation
    variation_keys = [
        "happy", "sad", "excited", "calm", "playful", "serious", "surprised",
        "thinking", "curious", "worried", "confused", "amused", "flirty",
        "sarcastic", "witty", "helpful", "friendly", "professional",
        "diplomatic", "sweet", "shocked", "thoughtful", "ambivalent",
        "detached", "neutral"
    ]
    # Sort alphabetically
    variation_keys.sort()
    return variation_keys


def load_existing_assignments(project_root):
    """Load existing category assignments from lexi_descriptor_animations.json.
    Returns: (category_assignments: dict, assigned_descriptors: set)
    """
    systems_dir = os.path.join(project_root, "systems")
    json_path = os.path.join(systems_dir, "lexi_descriptor_animations.json")
    
    category_assignments = {}
    assigned_descriptors = set()
    
    if not os.path.exists(json_path):
        print(f"No existing assignments file found at {json_path}")
        return category_assignments, assigned_descriptors
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            descriptor_mapping = json.load(f)
        
        # Reverse the mapping: {descriptor: {category, ...}} -> {category: [descriptors]}
        for descriptor, info in descriptor_mapping.items():
            category = info.get("category")
            if category:
                if category not in category_assignments:
                    category_assignments[category] = []
                category_assignments[category].append(descriptor)
                assigned_descriptors.add(descriptor)
        
        print(f"✓ Loaded {len(assigned_descriptors)} existing descriptor assignments")
        print(f"  Found {len(category_assignments)} categories with assignments")
        
    except Exception as e:
        print(f"Warning: Could not load existing assignments: {e}")
    
    return category_assignments, assigned_descriptors


def save_descriptor_animations_json(category_assignments, project_root):
    """Save descriptor-to-animation mapping to JSON file in systems folder.
    Always saves, but logs missing animation locations to locations_log.txt
    Returns (success: bool, error_message: str or None)
    """
    animations_base_path = os.path.join(project_root, "animations", "right")
    missing_locations = []
    
    # Check all categories for missing animation folders
    for category in category_assignments.keys():
        folder_name = f"lexi_{category}"
        folder_path = os.path.join(animations_base_path, folder_name)
        animation_location = f"animations/right/lexi_{category}"
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            missing_locations.append(animation_location)
    
    # Build the mapping: {descriptor: {category, animation_name, animation_location}}
    descriptor_mapping = {}
    
    for category, descriptors in category_assignments.items():
        animation_name = category  # Animation name is the same as category
        animation_location = f"animations/right/lexi_{category}"
        
        for descriptor in descriptors:
            descriptor_mapping[descriptor] = {
                "category": category,
                "animation_name": animation_name,
                "animation_location": animation_location
            }
    
    # Save to systems/lexi_descriptor_animations.json
    systems_dir = os.path.join(project_root, "systems")
    os.makedirs(systems_dir, exist_ok=True)
    json_path = os.path.join(systems_dir, "lexi_descriptor_animations.json")
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(descriptor_mapping, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved descriptor animations mapping to {json_path}")
        print(f"  Mapped {len(descriptor_mapping)} descriptors")
        
        # If there are missing locations, write them to log file
        if missing_locations:
            # Save log file in the same folder as this utility script
            utility_folder = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(utility_folder, "locations_log.txt")
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("Missing Animation Locations:\n")
                    f.write("=" * 50 + "\n\n")
                    for location in missing_locations:
                        f.write(f"{location}\n")
                print(f"  Missing locations logged to {log_path}")
                error_msg = "Not all animation locations present, see locations_log.txt"
                return True, error_msg
            except Exception as e:
                error_msg = f"JSON saved, but error writing log file: {e}"
                return True, error_msg
        
        return True, None
    except Exception as e:
        error_msg = f"Error saving JSON file: {e}"
        print(error_msg)
        return False, error_msg


def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Lexi Descriptor Categories")
    clock = pygame.time.Clock()
    
    # Load descriptors
    descriptors = load_lexi_descriptors()
    variation_keys = load_variation_keys()
    
    # Load existing category assignments from JSON
    existing_assignments, assigned_descriptors_set = load_existing_assignments(PROJECT_ROOT)
    
    # Track category assignments: {category_name: [list of descriptors]}
    category_assignments = existing_assignments.copy()
    
    # Add any categories from JSON that aren't in variation_keys
    for category in category_assignments.keys():
        if category not in variation_keys:
            variation_keys.append(category)
    variation_keys.sort()  # Re-sort after adding new categories
    
    # Remove assigned descriptors from the main descriptors list
    # (they'll be shown in their assigned categories instead)
    descriptors = [desc for desc in descriptors if desc not in assigned_descriptors_set]
    
    # Scroll offsets for both panels
    left_scroll_offset = 0
    right_scroll_offset = 0
    
    # Scrollbar dragging state
    left_scrollbar_dragging = False
    right_scrollbar_dragging = False
    
    # Dialog state
    dialog = None
    dialog_result = None
    
    # Buttons for assigned descriptors in light blue box
    assigned_descriptor_buttons = []
    last_selected_category_index = None  # Track when selection changes
    
    # Error message state
    error_message = None
    error_message_timer = 0.0
    
    # Save button state
    save_button_clicked = False
    save_button_click_timer = 0.0
    
    # Create buttons for descriptors in left panel (single column)
    descriptor_buttons = []
    descriptor_arrow_buttons = []
    start_x = LEFT_PANEL_X + SCROLLBAR_WIDTH + BUTTON_PADDING
    base_y = LEFT_PANEL_Y + BUTTON_PADDING
    ARROW_BUTTON_SIZE = 25
    
    for i, descriptor in enumerate(descriptors):
        y_pos = base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING)
        button = LexiButton(descriptor, start_x, y_pos)
        # Check if this descriptor is already assigned (shouldn't be, but just in case)
        assigned_to_any = any(descriptor in category_assignments.get(cat, []) for cat in category_assignments)
        button.assigned = assigned_to_any
        descriptor_buttons.append(button)
        
        # Create arrow button next to descriptor
        arrow_x = start_x + BUTTON_WIDTH + BUTTON_PADDING
        arrow_y = y_pos + (BUTTON_HEIGHT - ARROW_BUTTON_SIZE) // 2
        arrow_button = ArrowButton(arrow_x, arrow_y)
        descriptor_arrow_buttons.append(arrow_button)
    
    # Create buttons for variation keys in right panel (single column, left-justified)
    variation_buttons = []
    delete_buttons = []
    right_start_x = RIGHT_PANEL_X + SCROLLBAR_WIDTH + BUTTON_PADDING
    right_base_y = RIGHT_PANEL_Y + BUTTON_PADDING
    selected_category_index = None
    
    for i, variation_key in enumerate(variation_keys):
        y_pos = right_base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING)
        button = LexiButton(variation_key, right_start_x, y_pos)
        variation_buttons.append(button)
        
        # Create delete button next to the category button
        delete_x = right_start_x + BUTTON_WIDTH + BUTTON_PADDING
        delete_y = y_pos + (BUTTON_HEIGHT - DELETE_BUTTON_SIZE) // 2  # Center vertically
        delete_button = DeleteButton(delete_x, delete_y)
        delete_buttons.append(delete_button)
    
    def calculate_scrollbar_info(buttons, panel_height):
        """Calculate scrollbar info for a list of buttons"""
        if not buttons:
            return 0, 0, False
        
        total_height = buttons[-1].rect.bottom - buttons[0].rect.top + BUTTON_PADDING
        visible_height = panel_height - BUTTON_PADDING * 2
        max_scroll = max(0, total_height - visible_height)
        needs_scrollbar = max_scroll > 0
        return total_height, max_scroll, needs_scrollbar
    
    def get_left_scrollbar_rect():
        """Get the left scrollbar rectangle"""
        return pygame.Rect(LEFT_PANEL_X, LEFT_PANEL_Y, SCROLLBAR_WIDTH, LEFT_PANEL_HEIGHT)
    
    def get_right_scrollbar_rect():
        """Get the right scrollbar rectangle"""
        return pygame.Rect(RIGHT_PANEL_X, RIGHT_PANEL_Y, SCROLLBAR_WIDTH, RIGHT_PANEL_HEIGHT)
    
    def handle_scrollbar_click(pos, panel_x, panel_y, panel_height, buttons, current_offset):
        """Handle clicking on scrollbar"""
        scrollbar_rect = pygame.Rect(panel_x, panel_y, SCROLLBAR_WIDTH, panel_height)
        if scrollbar_rect.collidepoint(pos):
            total_height, max_scroll, needs_scrollbar = calculate_scrollbar_info(buttons, panel_height)
            if needs_scrollbar:
                relative_y = pos[1] - panel_y
                scroll_ratio = max(0, min(1, relative_y / panel_height))
                return int(scroll_ratio * max_scroll)
        return current_offset
    
    running = True
    dt = 0
    while running:
        dt = clock.tick(60) / 1000.0
        
        # Update dialog cursor if active
        if dialog and dialog.input_active:
            dialog.cursor_timer += dt
            if dialog.cursor_timer >= 0.5:
                dialog.cursor_timer = 0
                dialog.cursor_visible = not dialog.cursor_visible
        
        # Update error message timer
        if error_message and error_message_timer > 0:
            error_message_timer -= dt
            if error_message_timer <= 0:
                error_message = None
        
        # Update save button click timer
        if save_button_clicked and save_button_click_timer > 0:
            save_button_click_timer -= dt
            if save_button_click_timer <= 0:
                save_button_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif dialog:
                # Handle dialog events
                result = dialog.handle_event(event, dt)
                if result:
                    if result == "ok" and dialog.input_text.strip():
                        new_category = dialog.input_text.strip().lower()
                        if new_category not in variation_keys:
                            variation_keys.append(new_category)
                            variation_keys.sort()
                            # Recreate variation buttons and delete buttons
                            variation_buttons = []
                            delete_buttons = []
                            # Find new index of added category
                            new_index = variation_keys.index(new_category)
                            for i, variation_key in enumerate(variation_keys):
                                y_pos = right_base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING)
                                button = LexiButton(variation_key, right_start_x, y_pos)
                                # Select the newly added category
                                if i == new_index:
                                    button.selected = True
                                    selected_category_index = i
                                variation_buttons.append(button)
                                
                                delete_x = right_start_x + BUTTON_WIDTH + BUTTON_PADDING
                                delete_y = y_pos + (BUTTON_HEIGHT - DELETE_BUTTON_SIZE) // 2
                                delete_button = DeleteButton(delete_x, delete_y)
                                delete_buttons.append(delete_button)
                            right_scroll_offset = 0  # Reset scroll
                    dialog = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check scrollbar clicks
                    left_scrollbar_rect = get_left_scrollbar_rect()
                    right_scrollbar_rect = get_right_scrollbar_rect()
                    
                    if left_scrollbar_rect.collidepoint(event.pos):
                        left_scrollbar_dragging = True
                        left_scroll_offset = handle_scrollbar_click(
                            event.pos, LEFT_PANEL_X, LEFT_PANEL_Y, LEFT_PANEL_HEIGHT, 
                            descriptor_buttons, left_scroll_offset
                        )
                    elif right_scrollbar_rect.collidepoint(event.pos):
                        right_scrollbar_dragging = True
                        right_scroll_offset = handle_scrollbar_click(
                            event.pos, RIGHT_PANEL_X, RIGHT_PANEL_Y, RIGHT_PANEL_HEIGHT,
                            variation_buttons, right_scroll_offset
                        )
                    else:
                        # Check button clicks (adjust for scroll offset)
                        # Check arrow button clicks first
                        for i, arrow_button in enumerate(descriptor_arrow_buttons):
                            adjusted_y = base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - left_scroll_offset
                            arrow_adjusted_y = adjusted_y + (BUTTON_HEIGHT - ARROW_BUTTON_SIZE) // 2
                            arrow_adjusted_rect = pygame.Rect(
                                arrow_button.rect.x,
                                arrow_adjusted_y,
                                arrow_button.rect.width,
                                arrow_button.rect.height
                            )
                            if arrow_adjusted_rect.collidepoint(event.pos):
                                # Check if a category is selected
                                if selected_category_index is not None and selected_category_index < len(variation_keys):
                                    selected_category = variation_keys[selected_category_index]
                                    descriptor = descriptors[i]
                                    
                                    # Initialize category assignments if needed
                                    if selected_category not in category_assignments:
                                        category_assignments[selected_category] = []
                                    
                                    # Add descriptor to category if not already assigned
                                    if descriptor not in category_assignments[selected_category]:
                                        category_assignments[selected_category].append(descriptor)
                                        
                                        # Mark descriptor as assigned
                                        descriptor_buttons[i].assigned = True
                                        
                                        # Move descriptor to end of list
                                        descriptors.pop(i)
                                        descriptors.append(descriptor)
                                        
                                        # Recreate descriptor buttons and arrow buttons
                                        descriptor_buttons = []
                                        descriptor_arrow_buttons = []
                                        for j, desc in enumerate(descriptors):
                                            y_pos = base_y + j * (BUTTON_HEIGHT + BUTTON_PADDING)
                                            btn = LexiButton(desc, start_x, y_pos)
                                            # Check if this descriptor is assigned to any category
                                            assigned_to_any = any(desc in category_assignments.get(cat, []) for cat in category_assignments)
                                            btn.assigned = assigned_to_any
                                            descriptor_buttons.append(btn)
                                            
                                            arrow_x = start_x + BUTTON_WIDTH + BUTTON_PADDING
                                            arrow_y = y_pos + (BUTTON_HEIGHT - ARROW_BUTTON_SIZE) // 2
                                            arrow_btn = ArrowButton(arrow_x, arrow_y)
                                            descriptor_arrow_buttons.append(arrow_btn)
                                        
                                        left_scroll_offset = 0  # Reset scroll
                                        print(f"Assigned '{descriptor}' to category '{selected_category}'")
                                break
                        
                        for i, button in enumerate(descriptor_buttons):
                            adjusted_y = base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - left_scroll_offset
                            adjusted_rect = pygame.Rect(
                                button.rect.x,
                                adjusted_y,
                                button.rect.width,
                                button.rect.height
                            )
                            if adjusted_rect.collidepoint(event.pos):
                                print(f"Clicked: {button.text}")
                        
                        # Check save button click
                        save_button_width = 100
                        save_button_height = 30
                        save_button_x = WINDOW_WIDTH - save_button_width - 10
                        save_button_y = WINDOW_HEIGHT - save_button_height - 10
                        save_button_rect = pygame.Rect(save_button_x, save_button_y, save_button_width, save_button_height)
                        if save_button_rect.collidepoint(event.pos):
                            # Visual feedback - button clicked
                            save_button_clicked = True
                            save_button_click_timer = 0.3  # Show clicked state for 0.3 seconds
                            
                            # Save JSON file with validation
                            success, error_msg = save_descriptor_animations_json(category_assignments, PROJECT_ROOT)
                            if error_msg:
                                error_message = error_msg
                                error_message_timer = 5.0  # Show error for 5 seconds
                            else:
                                error_message = None
                                error_message_timer = 0.0
                        
                        for i, button in enumerate(variation_buttons):
                            adjusted_y = right_base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - right_scroll_offset
                            adjusted_rect = pygame.Rect(
                                button.rect.x,
                                adjusted_y,
                                button.rect.width,
                                button.rect.height
                            )
                            if adjusted_rect.collidepoint(event.pos):
                                # Deselect previous selection
                                if selected_category_index is not None and selected_category_index < len(variation_buttons):
                                    variation_buttons[selected_category_index].selected = False
                                # Select this button
                                button.selected = True
                                selected_category_index = i
                                print(f"Selected category: {button.text}")
                                break
                        
                        # Check delete button clicks
                        for i, delete_button in enumerate(delete_buttons):
                            adjusted_y = right_base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - right_scroll_offset
                            delete_adjusted_y = adjusted_y + (BUTTON_HEIGHT - DELETE_BUTTON_SIZE) // 2
                            delete_adjusted_rect = pygame.Rect(
                                delete_button.rect.x,
                                delete_adjusted_y,
                                delete_button.rect.width,
                                delete_button.rect.height
                            )
                            if delete_adjusted_rect.collidepoint(event.pos):
                                # Delete the category
                                if i < len(variation_keys):
                                    variation_keys.pop(i)
                                    # Clear selection if deleted item was selected
                                    if selected_category_index == i:
                                        selected_category_index = None
                                    elif selected_category_index is not None and selected_category_index > i:
                                        selected_category_index -= 1
                                    # Recreate buttons
                                    variation_buttons = []
                                    delete_buttons = []
                                    for j, variation_key in enumerate(variation_keys):
                                        y_pos = right_base_y + j * (BUTTON_HEIGHT + BUTTON_PADDING)
                                        button = LexiButton(variation_key, right_start_x, y_pos)
                                        # Restore selection if applicable
                                        if selected_category_index == j:
                                            button.selected = True
                                        variation_buttons.append(button)
                                        
                                        delete_x = right_start_x + BUTTON_WIDTH + BUTTON_PADDING
                                        delete_y = y_pos + (BUTTON_HEIGHT - DELETE_BUTTON_SIZE) // 2
                                        delete_button = DeleteButton(delete_x, delete_y)
                                        delete_buttons.append(delete_button)
                                    right_scroll_offset = 0  # Reset scroll
                                break
                elif event.button == 3:  # Right click
                    # Check if right-clicking in right panel (excluding scrollbar)
                    if RIGHT_PANEL_X + SCROLLBAR_WIDTH <= event.pos[0] < RIGHT_PANEL_X + RIGHT_PANEL_WIDTH:
                        if RIGHT_PANEL_Y <= event.pos[1] < RIGHT_PANEL_Y + RIGHT_PANEL_HEIGHT:
                            # Open dialog to create new category
                            dialog = NewCategoryDialog(WINDOW_WIDTH, WINDOW_HEIGHT)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    left_scrollbar_dragging = False
                    right_scrollbar_dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if left_scrollbar_dragging:
                    total_height, max_scroll, needs_scrollbar = calculate_scrollbar_info(
                        descriptor_buttons, LEFT_PANEL_HEIGHT
                    )
                    if needs_scrollbar:
                        relative_y = event.pos[1] - LEFT_PANEL_Y
                        scroll_ratio = max(0, min(1, relative_y / LEFT_PANEL_HEIGHT))
                        left_scroll_offset = int(scroll_ratio * max_scroll)
                elif right_scrollbar_dragging:
                    total_height, max_scroll, needs_scrollbar = calculate_scrollbar_info(
                        variation_buttons, RIGHT_PANEL_HEIGHT
                    )
                    if needs_scrollbar:
                        relative_y = event.pos[1] - RIGHT_PANEL_Y
                        scroll_ratio = max(0, min(1, relative_y / RIGHT_PANEL_HEIGHT))
                        right_scroll_offset = int(scroll_ratio * max_scroll)
            elif event.type == pygame.MOUSEWHEEL:
                # Determine which panel the mouse is over
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                if LEFT_PANEL_X <= mouse_x < LEFT_PANEL_X + LEFT_PANEL_WIDTH:
                    total_height, max_scroll, needs_scrollbar = calculate_scrollbar_info(
                        descriptor_buttons, LEFT_PANEL_HEIGHT
                    )
                    if needs_scrollbar:
                        left_scroll_offset = max(0, min(max_scroll, left_scroll_offset - event.y * 20))
                elif RIGHT_PANEL_X <= mouse_x < RIGHT_PANEL_X + RIGHT_PANEL_WIDTH:
                    total_height, max_scroll, needs_scrollbar = calculate_scrollbar_info(
                        variation_buttons, RIGHT_PANEL_HEIGHT
                    )
                    if needs_scrollbar:
                        right_scroll_offset = max(0, min(max_scroll, right_scroll_offset - event.y * 20))
        
        # Calculate scrollbar info
        left_total, left_max_scroll, left_needs_scrollbar = calculate_scrollbar_info(
            descriptor_buttons, LEFT_PANEL_HEIGHT
        )
        right_total, right_max_scroll, right_needs_scrollbar = calculate_scrollbar_info(
            variation_buttons, RIGHT_PANEL_HEIGHT
        )
        
        # Debug: Print scrollbar info (can remove later)
        # print(f"Left: total={left_total}, max_scroll={left_max_scroll}, needs={left_needs_scrollbar}, buttons={len(descriptor_buttons)}")
        # print(f"Right: total={right_total}, max_scroll={right_max_scroll}, needs={right_needs_scrollbar}, buttons={len(variation_buttons)}")
        
        # Clamp scroll offsets
        left_scroll_offset = max(0, min(left_max_scroll, left_scroll_offset))
        right_scroll_offset = max(0, min(right_max_scroll, right_scroll_offset))
        
        # Draw
        screen.fill(BLACK)
        
        # Draw left panel
        left_panel_rect = pygame.Rect(LEFT_PANEL_X, LEFT_PANEL_Y, LEFT_PANEL_WIDTH, LEFT_PANEL_HEIGHT)
        pygame.draw.rect(screen, LIGHT_GREY, left_panel_rect)
        
        # Draw left scrollbar (always show track, but only show thumb if needed)
        scrollbar_rect = get_left_scrollbar_rect()
        scrollbar_color = SCROLLBAR_COLOR if left_needs_scrollbar else SCROLLBAR_DISABLED_COLOR
        pygame.draw.rect(screen, scrollbar_color, scrollbar_rect)
        
        if left_needs_scrollbar:
            visible_height = LEFT_PANEL_HEIGHT - BUTTON_PADDING * 2
            thumb_height = max(20, int((visible_height / left_total) * LEFT_PANEL_HEIGHT))
            thumb_y = LEFT_PANEL_Y + int((left_scroll_offset / left_max_scroll) * (LEFT_PANEL_HEIGHT - thumb_height)) if left_max_scroll > 0 else LEFT_PANEL_Y
            thumb_rect = pygame.Rect(LEFT_PANEL_X, thumb_y, SCROLLBAR_WIDTH, thumb_height)
            pygame.draw.rect(screen, SCROLLBAR_THUMB_COLOR, thumb_rect)
        
        # Draw descriptor buttons and arrow buttons (left panel) with scroll offset
        clip_rect = pygame.Rect(LEFT_PANEL_X + SCROLLBAR_WIDTH, LEFT_PANEL_Y, LEFT_PANEL_WIDTH - SCROLLBAR_WIDTH, LEFT_PANEL_HEIGHT)
        screen.set_clip(clip_rect)
        for i, button in enumerate(descriptor_buttons):
            adjusted_y = base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - left_scroll_offset
            if LEFT_PANEL_Y <= adjusted_y + button.rect.height and adjusted_y <= LEFT_PANEL_Y + LEFT_PANEL_HEIGHT:
                # Temporarily adjust position for drawing
                original_y = button.rect.y
                button.rect.y = adjusted_y
                button.draw(screen)
                button.rect.y = original_y
                
                # Draw corresponding arrow button
                if i < len(descriptor_arrow_buttons):
                    arrow_adjusted_y = adjusted_y + (BUTTON_HEIGHT - ARROW_BUTTON_SIZE) // 2
                    original_arrow_y = descriptor_arrow_buttons[i].rect.y
                    descriptor_arrow_buttons[i].rect.y = arrow_adjusted_y
                    descriptor_arrow_buttons[i].draw(screen)
                    descriptor_arrow_buttons[i].rect.y = original_arrow_y
        screen.set_clip(None)
        
        # Draw right scrollbar (always show track, but only show thumb if needed)
        scrollbar_rect = get_right_scrollbar_rect()
        scrollbar_color = SCROLLBAR_COLOR if right_needs_scrollbar else SCROLLBAR_DISABLED_COLOR
        pygame.draw.rect(screen, scrollbar_color, scrollbar_rect)
        
        if right_needs_scrollbar:
            visible_height = RIGHT_PANEL_HEIGHT - BUTTON_PADDING * 2
            thumb_height = max(20, int((visible_height / right_total) * RIGHT_PANEL_HEIGHT))
            thumb_y = RIGHT_PANEL_Y + int((right_scroll_offset / right_max_scroll) * (RIGHT_PANEL_HEIGHT - thumb_height)) if right_max_scroll > 0 else RIGHT_PANEL_Y
            thumb_rect = pygame.Rect(RIGHT_PANEL_X, thumb_y, SCROLLBAR_WIDTH, thumb_height)
            pygame.draw.rect(screen, SCROLLBAR_THUMB_COLOR, thumb_rect)
        
        # Draw right detail panel (light blue area)
        detail_panel_rect = pygame.Rect(
            RIGHT_DETAIL_PANEL_X,
            RIGHT_DETAIL_PANEL_Y,
            RIGHT_DETAIL_PANEL_WIDTH,
            RIGHT_DETAIL_PANEL_HEIGHT
        )
        pygame.draw.rect(screen, LIGHT_BLUE, detail_panel_rect)
        pygame.draw.rect(screen, DARK_BLUE, detail_panel_rect, 3)
        
        # Update assigned descriptor buttons when category selection changes
        if selected_category_index != last_selected_category_index:
            last_selected_category_index = selected_category_index
            if selected_category_index is not None and selected_category_index < len(variation_keys):
                selected_category = variation_keys[selected_category_index]
                assigned_descriptors = category_assignments.get(selected_category, [])
                
                # Recreate assigned descriptor buttons
                assigned_descriptor_buttons = []
                detail_padding = 10
                detail_y = RIGHT_DETAIL_PANEL_Y + detail_padding
                
                for descriptor in assigned_descriptors:
                    button = LexiButton(descriptor, RIGHT_DETAIL_PANEL_X + detail_padding, detail_y, BUTTON_WIDTH)
                    assigned_descriptor_buttons.append(button)
                    detail_y += BUTTON_HEIGHT + BUTTON_PADDING
            else:
                assigned_descriptor_buttons = []
        
        # Also update when a descriptor is assigned (check if current selection has more descriptors)
        if selected_category_index is not None and selected_category_index < len(variation_keys):
            selected_category = variation_keys[selected_category_index]
            assigned_descriptors = category_assignments.get(selected_category, [])
            if len(assigned_descriptors) != len(assigned_descriptor_buttons):
                # Recreate buttons
                assigned_descriptor_buttons = []
                detail_padding = 10
                detail_y = RIGHT_DETAIL_PANEL_Y + detail_padding
                
                for descriptor in assigned_descriptors:
                    button = LexiButton(descriptor, RIGHT_DETAIL_PANEL_X + detail_padding, detail_y, BUTTON_WIDTH)
                    assigned_descriptor_buttons.append(button)
                    detail_y += BUTTON_HEIGHT + BUTTON_PADDING
        
        # Draw assigned descriptor buttons in the light blue box
        for button in assigned_descriptor_buttons:
            button.draw(screen)
        
        # Draw variation key buttons and delete buttons (right panel) with scroll offset
        clip_rect = pygame.Rect(RIGHT_PANEL_X + SCROLLBAR_WIDTH, RIGHT_PANEL_Y, RIGHT_PANEL_WIDTH - SCROLLBAR_WIDTH, RIGHT_PANEL_HEIGHT)
        screen.set_clip(clip_rect)
        for i, button in enumerate(variation_buttons):
            adjusted_y = right_base_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - right_scroll_offset
            if RIGHT_PANEL_Y <= adjusted_y + button.rect.height and adjusted_y <= RIGHT_PANEL_Y + RIGHT_PANEL_HEIGHT:
                # Temporarily adjust position for drawing
                original_y = button.rect.y
                button.rect.y = adjusted_y
                button.draw(screen)
                button.rect.y = original_y
                
                # Draw corresponding delete button
                if i < len(delete_buttons):
                    delete_adjusted_y = adjusted_y + (BUTTON_HEIGHT - DELETE_BUTTON_SIZE) // 2
                    original_delete_y = delete_buttons[i].rect.y
                    delete_buttons[i].rect.y = delete_adjusted_y
                    delete_buttons[i].draw(screen)
                    delete_buttons[i].rect.y = original_delete_y
        screen.set_clip(None)
        
        # Draw save button (bottom right)
        save_button_width = 100
        save_button_height = 30
        save_button_x = WINDOW_WIDTH - save_button_width - 10
        save_button_y = WINDOW_HEIGHT - save_button_height - 10
        save_button_rect = pygame.Rect(save_button_x, save_button_y, save_button_width, save_button_height)
        
        # Change color when clicked
        button_color = (200, 150, 200) if save_button_clicked else PINK
        pygame.draw.rect(screen, button_color, save_button_rect)
        pygame.draw.rect(screen, DARK_GREY, save_button_rect, 2)
        save_font = pygame.font.Font(None, 20)
        save_text = save_font.render("Save JSON", True, BLACK)
        save_text_rect = save_text.get_rect(center=save_button_rect.center)
        screen.blit(save_text, save_text_rect)
        
        # Draw error message if present
        if error_message:
            error_font = pygame.font.Font(None, 24)
            # Create error message surface with background
            error_lines = error_message.split('\n') if '\n' in error_message else [error_message]
            max_width = max(error_font.size(line)[0] for line in error_lines)
            error_height = len(error_lines) * 30 + 20
            error_surface = pygame.Surface((max_width + 40, error_height))
            error_surface.fill((255, 200, 200))  # Light red background
            pygame.draw.rect(error_surface, RED, error_surface.get_rect(), 3)
            
            # Draw text on error surface
            for i, line in enumerate(error_lines):
                text_surf = error_font.render(line, True, BLACK)
                error_surface.blit(text_surf, (20, 10 + i * 30))
            
            # Center error message on screen
            error_x = (WINDOW_WIDTH - error_surface.get_width()) // 2
            error_y = (WINDOW_HEIGHT - error_surface.get_height()) // 2
            screen.blit(error_surface, (error_x, error_y))
        
        # Draw dialog if active
        if dialog:
            dialog.draw(screen)
        
        pygame.display.flip()
    
    pygame.quit()


if __name__ == "__main__":
    main()

