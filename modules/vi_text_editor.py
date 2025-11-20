"""
Vi-like text editor for input box
Provides vi-style navigation and editing modes
"""
import pygame
from typing import List, Tuple, Optional


class ViTextEditor:
    """Vi-like text editor with normal and insert modes"""
    
    def __init__(self, font, box_width: int, box_height: int, padding: int = 5):
        self.font = font
        self.box_width = box_width
        self.box_height = box_height
        self.padding = padding
        
        # Text buffer - list of lines
        self.buffer: List[str] = [""]
        
        # Cursor position (line, column)
        self.cursor_line = 0
        self.cursor_col = 0
        
        # Viewport - which lines are visible
        self.viewport_start_line = 0
        self.viewport_end_line = 0
        self.viewport_start_col = 0  # Horizontal scroll offset (in characters, approximate)
        self._calculate_viewport()
        
        # Mode: 'normal', 'insert', or 'command'
        self.mode = 'normal'
        
        # Command mode state
        self.command_buffer = ""
        self.command_callback = None  # Callback for executing commands (e.g., :send)
        
        # Last command (for repeat commands like dd)
        self.last_command = None
    
    def _calculate_viewport(self):
        """Calculate how many lines fit in the viewport"""
        line_height = self.font.get_height() + 1
        max_lines = (self.box_height - self.padding * 2) // line_height
        self.viewport_end_line = self.viewport_start_line + max_lines
    
    def get_text(self) -> str:
        """Get the full text as a single string"""
        return "\n".join(self.buffer)
    
    def set_text(self, text: str):
        """Set the text buffer from a string"""
        if not text:
            self.buffer = [""]
        else:
            self.buffer = text.split("\n")
            if not self.buffer:
                self.buffer = [""]
        
        # Ensure cursor is within bounds
        self.cursor_line = min(self.cursor_line, len(self.buffer) - 1)
        self.cursor_col = min(self.cursor_col, len(self.buffer[self.cursor_line]))
        self._ensure_cursor_visible()
    
    def _ensure_cursor_visible(self):
        """Scroll viewport to keep cursor visible (both vertical and horizontal)"""
        line_height = self.font.get_height() + 1
        max_lines = (self.box_height - self.padding * 2) // line_height
        
        # Vertical scrolling
        if self.cursor_line >= self.viewport_end_line:
            self.viewport_start_line = self.cursor_line - max_lines + 1
            self.viewport_end_line = self.viewport_start_line + max_lines
        
        if self.cursor_line < self.viewport_start_line:
            self.viewport_start_line = self.cursor_line
            self.viewport_end_line = self.viewport_start_line + max_lines
        
        self.viewport_start_line = max(0, self.viewport_start_line)
        self.viewport_end_line = min(len(self.buffer), self.viewport_end_line)
        
        # Horizontal scrolling - use pixel-based calculation
        max_width = self.box_width - self.padding * 2
        current_line = self.buffer[self.cursor_line]
        
        # Get text from viewport start to cursor to check if it fits
        visible_text = current_line[self.viewport_start_col:self.cursor_col]
        if visible_text:
            text_surface = self.font.render(visible_text, True, (255, 255, 255))
            text_width = text_surface.get_width()
        else:
            text_width = 0
        
        # Check if cursor position (in pixels) is beyond right edge
        if text_width > max_width:
            # Cursor is beyond right edge - scroll right
            # Find the right viewport_start_col by working backwards from cursor
            # We want to show as much text as possible ending at cursor
            test_col = max(0, self.cursor_col - 1)
            best_col = test_col
            
            # Binary search for optimal viewport start
            low = 0
            high = self.cursor_col
            while low <= high:
                mid = (low + high) // 2
                test_text = current_line[mid:self.cursor_col]
                if test_text:
                    test_surf = self.font.render(test_text, True, (255, 255, 255))
                    if test_surf.get_width() <= max_width:
                        best_col = mid
                        low = mid + 1
                    else:
                        high = mid - 1
                else:
                    best_col = mid
                    break
            
            self.viewport_start_col = max(0, best_col)
        elif self.cursor_col < self.viewport_start_col:
            # Cursor is before viewport start - scroll left
            self.viewport_start_col = max(0, self.cursor_col)
        
        # Ensure we don't scroll past the end of the line unnecessarily
        line_len = len(current_line)
        if self.viewport_start_col > line_len:
            self.viewport_start_col = max(0, line_len)
    
    def handle_key(self, event) -> bool:
        """
        Handle a key event. Returns True if handled, False if not.
        In normal mode, handles vi commands. In insert mode, handles typing.
        In command mode, handles command input.
        """
        if event.type != pygame.KEYDOWN:
            return False
        
        if self.mode == 'normal':
            return self._handle_normal_mode(event)
        elif self.mode == 'insert':
            return self._handle_insert_mode(event)
        else:  # command mode
            return self._handle_command_mode(event)
    
    def _handle_normal_mode(self, event) -> bool:
        """Handle keys in normal mode (vi commands)"""
        key = event.key
        mods = pygame.key.get_mods()
        unicode = event.unicode if hasattr(event, 'unicode') else ''
        
        # Movement commands
        if key == pygame.K_h or (key == pygame.K_LEFT and not mods & pygame.KMOD_SHIFT):
            self._move_left()
            return True
        elif key == pygame.K_j or (key == pygame.K_DOWN and not mods & pygame.KMOD_SHIFT):
            self._move_down()
            return True
        elif key == pygame.K_k or (key == pygame.K_UP and not mods & pygame.KMOD_SHIFT):
            self._move_up()
            return True
        elif key == pygame.K_l or (key == pygame.K_RIGHT and not mods & pygame.KMOD_SHIFT):
            self._move_right()
            return True
        
        # Enter insert mode
        elif key == pygame.K_i:
            self.mode = 'insert'
            return True
        elif key == pygame.K_a and not (mods & pygame.KMOD_SHIFT):  # Append (insert after cursor)
            self._move_right()
            self.mode = 'insert'
            return True
        elif key == pygame.K_a and (mods & pygame.KMOD_SHIFT):  # Append to end of line (A)
            self.cursor_col = len(self.buffer[self.cursor_line])
            self.mode = 'insert'
            return True
        elif key == pygame.K_o and not (mods & pygame.KMOD_SHIFT):  # Open new line below
            self.buffer.insert(self.cursor_line + 1, "")
            self.cursor_line += 1
            self.cursor_col = 0
            self.mode = 'insert'
            return True
        elif key == pygame.K_o and (mods & pygame.KMOD_SHIFT):  # Open new line above (O)
            self.buffer.insert(self.cursor_line, "")
            self.cursor_col = 0
            self.mode = 'insert'
            return True
        
        # Line navigation
        elif key == pygame.K_0 or (key == pygame.K_HOME and not mods & pygame.KMOD_SHIFT):
            self.cursor_col = 0
            return True
        elif (key == pygame.K_4 and mods & pygame.KMOD_SHIFT) or (key == pygame.K_END and not mods & pygame.KMOD_SHIFT):
            self.cursor_col = len(self.buffer[self.cursor_line])
            return True
        
        # Delete commands
        elif key == pygame.K_x:  # Delete character under cursor
            if self.cursor_col < len(self.buffer[self.cursor_line]):
                line = self.buffer[self.cursor_line]
                self.buffer[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col + 1:]
            elif self.cursor_line < len(self.buffer) - 1:
                # Join with next line
                self.buffer[self.cursor_line] += self.buffer.pop(self.cursor_line + 1)
            return True
        elif key == pygame.K_d:
            # Check for dd (delete line) - we'll handle this with a state machine
            if self.last_command == 'd':
                # Delete current line
                if len(self.buffer) > 1:
                    self.buffer.pop(self.cursor_line)
                    if self.cursor_line >= len(self.buffer):
                        self.cursor_line = len(self.buffer) - 1
                    self.cursor_col = min(self.cursor_col, len(self.buffer[self.cursor_line]))
                else:
                    self.buffer = [""]
                    self.cursor_line = 0
                    self.cursor_col = 0
                self.last_command = None
            else:
                self.last_command = 'd'
            return True
        
        # Enter command mode with colon (semicolon with shift, or check unicode)
        elif (key == pygame.K_SEMICOLON and (mods & pygame.KMOD_SHIFT)) or \
             (unicode == ':'):
            self.mode = 'command'
            self.command_buffer = ""
            return True
        
        # Clear last command if it's not a repeat
        if key not in (pygame.K_d,):
            self.last_command = None
        
        return False
    
    def _handle_insert_mode(self, event) -> bool:
        """Handle keys in insert mode (typing)"""
        key = event.key
        
        # Exit insert mode with Esc
        if key == pygame.K_ESCAPE:
            self.mode = 'normal'
            return True  # Consume the event
        
        # Backspace
        elif key == pygame.K_BACKSPACE:
            if self.cursor_col > 0:
                # Delete character before cursor
                line = self.buffer[self.cursor_line]
                self.buffer[self.cursor_line] = line[:self.cursor_col - 1] + line[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                # Join with previous line
                prev_line_len = len(self.buffer[self.cursor_line - 1])
                self.buffer[self.cursor_line - 1] += self.buffer.pop(self.cursor_line)
                self.cursor_line -= 1
                self.cursor_col = prev_line_len
            self._ensure_cursor_visible()
            return True
        
        # Enter/Return - new line
        elif key == pygame.K_RETURN:
            # Split line at cursor
            line = self.buffer[self.cursor_line]
            self.buffer[self.cursor_line] = line[:self.cursor_col]
            self.buffer.insert(self.cursor_line + 1, line[self.cursor_col:])
            self.cursor_line += 1
            self.cursor_col = 0
            self._ensure_cursor_visible()
            return True
        
        # Regular character input
        elif event.unicode and event.unicode.isprintable():
            line = self.buffer[self.cursor_line]
            self.buffer[self.cursor_line] = line[:self.cursor_col] + event.unicode + line[self.cursor_col:]
            self.cursor_col += 1
            self._ensure_cursor_visible()  # This will trigger horizontal scrolling
            return True
        
        return False
    
    def _move_left(self):
        """Move cursor left"""
        if self.cursor_col > 0:
            self.cursor_col -= 1
        elif self.cursor_line > 0:
            self.cursor_line -= 1
            self.cursor_col = len(self.buffer[self.cursor_line])
        self._ensure_cursor_visible()
    
    def _move_right(self):
        """Move cursor right"""
        if self.cursor_col < len(self.buffer[self.cursor_line]):
            self.cursor_col += 1
        elif self.cursor_line < len(self.buffer) - 1:
            self.cursor_line += 1
            self.cursor_col = 0
        self._ensure_cursor_visible()
    
    def _move_up(self):
        """Move cursor up"""
        if self.cursor_line > 0:
            self.cursor_line -= 1
            self.cursor_col = min(self.cursor_col, len(self.buffer[self.cursor_line]))
            self._ensure_cursor_visible()
    
    def _move_down(self):
        """Move cursor down"""
        if self.cursor_line < len(self.buffer) - 1:
            self.cursor_line += 1
            self.cursor_col = min(self.cursor_col, len(self.buffer[self.cursor_line]))
            self._ensure_cursor_visible()
    
    def get_visible_lines(self) -> List[Tuple[int, str]]:
        """Get list of (line_index, line_text) for visible lines (clipped horizontally)"""
        visible = []
        max_width = self.box_width - self.padding * 2
        
        for i in range(self.viewport_start_line, min(self.viewport_end_line, len(self.buffer))):
            line = self.buffer[i]
            # Clip line to visible portion horizontally
            clipped_line = line[self.viewport_start_col:]
            
            # Further clip if line is too wide (in pixels)
            # We'll render and check pixel width
            test_surface = self.font.render(clipped_line, True, (255, 255, 255))
            if test_surface.get_width() > max_width:
                # Binary search for the right character count
                low = 0
                high = len(clipped_line)
                while low < high:
                    mid = (low + high + 1) // 2
                    test_text = clipped_line[:mid]
                    test_surf = self.font.render(test_text, True, (255, 255, 255))
                    if test_surf.get_width() <= max_width:
                        low = mid
                    else:
                        high = mid - 1
                clipped_line = clipped_line[:low]
            
            visible.append((i, clipped_line))
        return visible
    
    def get_cursor_screen_pos(self, box_x: int, box_y: int) -> Tuple[int, int]:
        """Get the screen position of the cursor (accounting for horizontal scroll)"""
        line_height = self.font.get_height() + 1
        max_width = self.box_width - self.padding * 2
        visible_lines = self.get_visible_lines()
        
        # Find cursor line in visible lines
        cursor_vis_line = None
        for idx, (line_idx, _) in enumerate(visible_lines):
            if line_idx == self.cursor_line:
                cursor_vis_line = idx
                break
        
        if cursor_vis_line is None:
            return (box_x + self.padding, box_y + self.padding)
        
        # Calculate x position based on column, accounting for horizontal scroll
        current_line = self.buffer[self.cursor_line]
        visible_start = self.viewport_start_col
        visible_end = self.cursor_col
        
        if visible_end <= visible_start:
            # Cursor is at or before viewport start
            x = box_x + self.padding
        else:
            # Get text from viewport start to cursor
            text_to_cursor = current_line[visible_start:visible_end]
            if text_to_cursor:
                text_surface = self.font.render(text_to_cursor, True, (255, 255, 255))
                text_width = text_surface.get_width()
            else:
                text_width = 0
            
            x = box_x + self.padding + text_width
            
            # Clamp cursor to stay within box bounds
            max_x = box_x + self.padding + max_width
            x = min(x, max_x)
        
        y = box_y + self.padding + cursor_vis_line * line_height
        
        return (x, y)
    
    def _handle_command_mode(self, event) -> bool:
        """Handle keys in command mode"""
        key = event.key
        
        # Execute command with Enter
        if key == pygame.K_RETURN:
            self._execute_command(self.command_buffer)
            self.mode = 'normal'
            self.command_buffer = ""
            return True
        
        # Cancel command mode with Esc
        elif key == pygame.K_ESCAPE:
            self.mode = 'normal'
            self.command_buffer = ""
            return True
        
        # Backspace
        elif key == pygame.K_BACKSPACE:
            if self.command_buffer:
                self.command_buffer = self.command_buffer[:-1]
            return True
        
        # Regular character input
        elif event.unicode and event.unicode.isprintable():
            self.command_buffer += event.unicode
            return True
        
        return False
    
    def _execute_command(self, command: str):
        """Execute a command mode command"""
        command = command.strip()
        if not command:
            return
        
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "send":
            # Send message to Lexi (via callback)
            if self.command_callback:
                text = self.get_text()
                self.command_callback("send", text)
        elif cmd == "help":
            # Show help (via callback)
            if self.command_callback:
                self.command_callback("help", None)
        # Add more commands here later
    
    def set_command_callback(self, callback):
        """Set callback function for executing commands (e.g., :send)"""
        self.command_callback = callback
    
    def get_command_buffer(self) -> str:
        """Get the current command buffer (for display)"""
        return self.command_buffer
    
    def get_mode_display(self) -> str:
        """Get the current mode for display"""
        if self.mode == 'insert':
            return '-- INSERT --'
        # Command mode is handled separately in drawing code
        return ''

