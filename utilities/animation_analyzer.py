"""
Standalone Animation Analyzer
Independent tool for analyzing Lexi animations frame by frame.
700x700 black screen with controls to play/pause and step through frames.
"""
import pygame
import sys
import os
import glob
import json

# Add parent directory to path to import animation module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.animation import Animation

# Screen dimensions
SCREEN_SIZE = 700
SCREEN_WIDTH = SCREEN_SIZE
SCREEN_HEIGHT = SCREEN_SIZE

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)

# Animation base path
ANIMATION_BASE_PATH = "animations/right"
ANIMATION_FOLDER = "lexi_ambivalent"


def get_available_animations(base_path: str) -> list:
    """Get list of available animation folders"""
    full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), base_path)
    if not os.path.exists(full_path):
        return []
    
    animations = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        if os.path.isdir(item_path):
            # Check if it has frame files
            frame_files = glob.glob(os.path.join(item_path, "frame_*.png"))
            if frame_files:
                animations.append(item)
    
    return sorted(animations)


def load_animation_config(animation_path: str) -> dict:
    """Load animation config from JSON file, return defaults if not found"""
    config_file = os.path.join(animation_path, "animation_config.json")
    default_config = {
        "start_frame": 0,
        "end_frame": None,
        "fps": 10,
        "loop": True,
        "skip_first_frame": False,
        "sticky_frame": None
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**default_config, **config}
        except Exception as e:
            print(f"Warning: Could not load config from {config_file}: {e}")
            return default_config
    
    return default_config


def load_animation(animation_path: str) -> tuple:
    """Load animation frames and return (animation, frames_list, frame_file_paths, config)"""
    if not os.path.exists(animation_path):
        print(f"Error: Animation folder not found: {animation_path}")
        return None, [], [], {}
    
    # Load config
    config = load_animation_config(animation_path)
    
    # Get all frame files and sort them
    frame_files = sorted(glob.glob(os.path.join(animation_path, "frame_*.png")))
    
    if not frame_files:
        print(f"Error: No frames found in {animation_path}")
        return None, [], [], config
    
    # Determine which frames to load based on config
    start_idx = config.get("start_frame", 0)
    if config.get("skip_first_frame", False):
        start_idx = max(1, start_idx)
    
    end_idx = config.get("end_frame")
    if end_idx is None:
        end_idx = len(frame_files)
    else:
        end_idx = min(end_idx + 1, len(frame_files))
    
    if start_idx >= len(frame_files) or start_idx >= end_idx:
        print(f"Error: Invalid frame range (start: {start_idx}, end: {end_idx}, total: {len(frame_files)})")
        return None, [], [], config
    
    # Load frames and keep track of file paths
    frames = []
    frame_file_paths = []
    for frame_file in frame_files[start_idx:end_idx]:
        try:
            frame = pygame.image.load(frame_file).convert_alpha()
            frames.append(frame)
            frame_file_paths.append(frame_file)
        except Exception as e:
            print(f"Error loading frame {frame_file}: {e}")
            continue
    
    if not frames:
        print("Error: No frames loaded")
        return None, [], [], config
    
    # Create animation
    fps = config.get("fps", 10)
    loop = config.get("loop", True)
    animation = Animation("lexi_ambivalent", frames, fps=fps, loop=loop)
    
    return animation, frames, frame_file_paths, config


def save_animation_config(animation_path: str, config: dict, fps: int, loop: bool, sticky_frame: int = None) -> bool:
    """Save animation configuration to JSON file, creating it if it doesn't exist"""
    config_file = os.path.join(animation_path, "animation_config.json")
    
    try:
        # Load existing config if it exists
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        else:
            # Create default config
            existing_config = {
                "start_frame": 0,
                "end_frame": None,
                "fps": 10,
                "loop": True,
                "skip_first_frame": False,
                "sticky_frame": None
            }
        
        # Update with current values
        existing_config['fps'] = fps
        existing_config['loop'] = loop
        
        # Update sticky_frame if provided, otherwise keep existing or set to None
        if sticky_frame is not None:
            existing_config['sticky_frame'] = sticky_frame
        elif 'sticky_frame' not in existing_config:
            existing_config['sticky_frame'] = None
        
        # Ensure only one sticky_frame exists (remove duplicates if any)
        if existing_config['sticky_frame'] is not None:
            # Ensure it's a single integer, not a list
            if isinstance(existing_config['sticky_frame'], list):
                existing_config['sticky_frame'] = existing_config['sticky_frame'][0] if existing_config['sticky_frame'] else None
        
        # Save to file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving animation config: {e}")
        return False


def show_animation_selection_menu(screen, font, available_animations: list, current_animation: str) -> str:
    """Show animation selection menu and return selected animation name"""
    selected_index = 0
    if current_animation in available_animations:
        selected_index = available_animations.index(current_animation)
    
    input_text = ""
    filtered_animations = available_animations.copy()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return current_animation  # Cancel, return current
                elif event.key == pygame.K_RETURN:
                    if filtered_animations:
                        return filtered_animations[selected_index]
                elif event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(filtered_animations) if filtered_animations else 0
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(filtered_animations) if filtered_animations else 0
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                    # Filter animations based on input
                    if input_text:
                        filtered_animations = [a for a in available_animations if input_text.lower() in a.lower()]
                    else:
                        filtered_animations = available_animations.copy()
                    if selected_index >= len(filtered_animations):
                        selected_index = max(0, len(filtered_animations) - 1)
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode
                    # Filter animations based on input
                    filtered_animations = [a for a in available_animations if input_text.lower() in a.lower()]
                    if selected_index >= len(filtered_animations):
                        selected_index = max(0, len(filtered_animations) - 1)
        
        # Draw menu
        screen.fill(BLACK)
        
        title = font.render("Select Animation (Type to filter, UP/DOWN to select, ENTER to load, ESC to cancel)", True, WHITE)
        screen.blit(title, (10, 10))
        
        if input_text:
            filter_text = font.render(f"Filter: {input_text}", True, GRAY)
            screen.blit(filter_text, (10, 40))
        
        y_offset = 70
        for i, anim_name in enumerate(filtered_animations[:20]):  # Show max 20
            color = WHITE if i == selected_index else GRAY
            if i == selected_index:
                # Highlight selected
                pygame.draw.rect(screen, (50, 50, 50), (5, y_offset - 2, SCREEN_WIDTH - 10, 25))
            text = font.render(anim_name, True, color)
            screen.blit(text, (10, y_offset))
            y_offset += 25
        
        if len(filtered_animations) > 20:
            more_text = font.render(f"... and {len(filtered_animations) - 20} more", True, GRAY)
            screen.blit(more_text, (10, y_offset))
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)


def main():
    """Main animation analyzer loop"""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Animation Analyzer")
    clock = pygame.time.Clock()
    
    # Get available animations
    available_animations = get_available_animations(ANIMATION_BASE_PATH)
    current_animation_folder = ANIMATION_FOLDER
    
    # Load animation
    animation_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ANIMATION_BASE_PATH, current_animation_folder)
    animation, frames, frame_file_paths, config = load_animation(animation_path)
    
    if animation is None:
        print("Failed to load animation. Press any key to exit.")
        pygame.quit()
        sys.exit(1)
    
    print(f"Loaded animation: {current_animation_folder} ({len(frames)} frames)")
    print(f"Config: fps={config.get('fps', 10)}, loop={config.get('loop', True)}")
    print("\nControls:")
    print("  N - Load new animation")
    print("  A - Save all settings (FPS, loop, sticky_frame) to JSON")
    print("  SPACE - Play/Pause animation")
    print("  L - Toggle loop (loop once or continuously)")
    print("  +/- or UP/DOWN - Speed up/Slow down animation")
    print("  S - Set current frame as sticky_frame (only one allowed)")
    print("  RIGHT ARROW - Next frame")
    print("  LEFT ARROW - Previous frame")
    print("  DEL - Delete current frame")
    print("  ESC - Exit")
    
    # Manual frame control
    manual_mode = True
    current_frame_index = 0
    loop_enabled = config.get('loop', True)
    animation.loop = loop_enabled
    current_fps = config.get('fps', 10)
    animation.fps = current_fps
    
    # Font for displaying frame info
    font = pygame.font.Font(None, 24)
    menu_font = pygame.font.Font(None, 20)
    
    running = True
    last_time = pygame.time.get_ticks()
    
    while running:
        dt = (pygame.time.get_ticks() - last_time) / 1000.0
        last_time = pygame.time.get_ticks()
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_n:
                    # Load new animation
                    selected_animation = show_animation_selection_menu(screen, menu_font, available_animations, current_animation_folder)
                    if selected_animation and selected_animation != current_animation_folder:
                        # Reload animation
                        current_animation_folder = selected_animation
                        animation_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ANIMATION_BASE_PATH, current_animation_folder)
                        animation, frames, frame_file_paths, config = load_animation(animation_path)
                        
                        if animation is None:
                            print(f"Failed to load animation: {current_animation_folder}")
                            continue
                        
                        # Reset state
                        manual_mode = True
                        current_frame_index = 0
                        loop_enabled = config.get('loop', True)
                        animation.loop = loop_enabled
                        current_fps = config.get('fps', 10)
                        animation.fps = current_fps
                        
                        # Update window title
                        pygame.display.set_caption(f"Animation Analyzer - {current_animation_folder}")
                        print(f"Loaded animation: {current_animation_folder} ({len(frames)} frames)")
                elif event.key == pygame.K_SPACE:
                    # Toggle play/pause
                    if manual_mode:
                        # Switch to animation mode
                        manual_mode = False
                        animation.current_frame = current_frame_index
                        animation.play()
                        print("Animation playing...")
                    else:
                        # Switch to manual mode
                        manual_mode = True
                        animation.stop()
                        current_frame_index = animation.current_frame
                        print(f"Manual mode - Frame {current_frame_index}")
                elif event.key == pygame.K_RIGHT:
                    # Next frame
                    if manual_mode:
                        current_frame_index = (current_frame_index + 1) % len(frames)
                        print(f"Frame {current_frame_index}/{len(frames)-1}")
                    else:
                        # Switch to manual and advance
                        manual_mode = True
                        animation.stop()
                        current_frame_index = (animation.current_frame + 1) % len(frames)
                        print(f"Frame {current_frame_index}/{len(frames)-1}")
                elif event.key == pygame.K_LEFT:
                    # Previous frame
                    if manual_mode:
                        current_frame_index = (current_frame_index - 1) % len(frames)
                        if current_frame_index < 0:
                            current_frame_index = len(frames) - 1
                        print(f"Frame {current_frame_index}/{len(frames)-1}")
                    else:
                        # Switch to manual and go back
                        manual_mode = True
                        animation.stop()
                        current_frame_index = (animation.current_frame - 1) % len(frames)
                        if current_frame_index < 0:
                            current_frame_index = len(frames) - 1
                        print(f"Frame {current_frame_index}/{len(frames)-1}")
                elif event.key == pygame.K_l:
                    # Toggle loop
                    loop_enabled = not loop_enabled
                    animation.loop = loop_enabled
                    loop_status = "ON" if loop_enabled else "OFF"
                    print(f"Loop: {loop_status}")
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS or event.key == pygame.K_UP:
                    # Speed up (increase FPS)
                    current_fps = min(current_fps + 1, 60)  # Cap at 60 FPS
                    animation.fps = current_fps
                    print(f"FPS: {current_fps}")
                elif event.key == pygame.K_MINUS or event.key == pygame.K_DOWN:
                    # Slow down (decrease FPS)
                    current_fps = max(current_fps - 1, 1)  # Minimum 1 FPS
                    animation.fps = current_fps
                    print(f"FPS: {current_fps}")
                elif event.key == pygame.K_a:
                    # Save all settings to JSON
                    animation_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ANIMATION_BASE_PATH, current_animation_folder)
                    sticky_frame_value = config.get('sticky_frame', None)
                    
                    if save_animation_config(animation_path, config, current_fps, loop_enabled, sticky_frame_value):
                        print(f"All settings saved: FPS={current_fps}, Loop={loop_enabled}, StickyFrame={sticky_frame_value}")
                    else:
                        print("Failed to save settings")
                elif event.key == pygame.K_s:
                    # Set sticky_frame (only one allowed)
                    # Switch to manual mode if playing
                    if not manual_mode:
                        manual_mode = True
                        animation.stop()
                        current_frame_index = animation.current_frame
                    
                    # Update config with new sticky_frame (replaces any existing one)
                    config['sticky_frame'] = current_frame_index
                    animation_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ANIMATION_BASE_PATH, current_animation_folder)
                    
                    # Save immediately to ensure only one sticky_frame exists
                    if save_animation_config(animation_path, config, current_fps, loop_enabled, current_frame_index):
                        print(f"Sticky frame set to frame {current_frame_index} (only one sticky_frame allowed)")
                    else:
                        print("Failed to save sticky_frame")
                elif event.key == pygame.K_DELETE:
                    # Delete current frame
                    if len(frames) <= 1:
                        print("Cannot delete: Only one frame remaining")
                    else:
                        # Switch to manual mode if playing
                        if not manual_mode:
                            manual_mode = True
                            animation.stop()
                            current_frame_index = animation.current_frame
                        
                        # Get the file path to delete
                        frame_to_delete = frame_file_paths[current_frame_index]
                        
                        # Delete the file
                        try:
                            os.remove(frame_to_delete)
                            print(f"Deleted frame file: {os.path.basename(frame_to_delete)}")
                            
                            # Remove from lists only if file deletion succeeded
                            del frames[current_frame_index]
                            del frame_file_paths[current_frame_index]
                            
                            # Update animation frames
                            animation.frames = frames
                            
                            # Adjust current_frame_index
                            if current_frame_index >= len(frames):
                                current_frame_index = len(frames) - 1
                            
                            # Update animation's current frame
                            if animation.current_frame >= len(frames):
                                animation.current_frame = len(frames) - 1
                            
                            print(f"Frame deleted. Remaining: {len(frames)} frames. Current: {current_frame_index}/{len(frames)-1}")
                        except Exception as e:
                            print(f"Error deleting frame file: {e}")
        
        # Update animation if not in manual mode
        if not manual_mode:
            animation.update(dt)
            current_frame_index = animation.current_frame
        
        # Clear screen
        screen.fill(BLACK)
        
        # Get current frame to display
        if manual_mode:
            current_frame = frames[current_frame_index] if frames else None
        else:
            current_frame = animation.get_current_frame()
        
        # Draw frame centered
        if current_frame:
            frame_rect = current_frame.get_rect()
            # Center on screen
            x = (SCREEN_WIDTH - frame_rect.width) // 2
            y = (SCREEN_HEIGHT - frame_rect.height) // 2
            screen.blit(current_frame, (x, y))
        
        # Draw frame info
        mode_text = "MANUAL" if manual_mode else "PLAYING"
        loop_text = "LOOP" if loop_enabled else "ONCE"
        frame_text = f"{current_animation_folder} | Frame: {current_frame_index}/{len(frames)-1} | Mode: {mode_text} | Loop: {loop_text} | FPS: {current_fps}"
        text_surface = font.render(frame_text, True, WHITE)
        screen.blit(text_surface, (10, 10))
        
        # Draw controls hint
        controls_text = "N: New | A: Save All | SPACE: Play/Pause | L: Loop | +/-: Speed | S: Sticky | LEFT/RIGHT: Step | DEL: Delete | ESC: Exit"
        controls_surface = font.render(controls_text, True, GRAY)
        screen.blit(controls_surface, (10, SCREEN_HEIGHT - 30))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()

