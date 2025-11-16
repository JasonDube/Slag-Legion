"""
Slag Legion 2.0 - Main Entry Point

This file has been refactored. The original monolithic code has been split into:
- constants.py: Game constants and configuration
- utils.py: Utility functions
- interactive.py: Interactive element system
- animation.py: Animation system
- sprite.py: Sprite system
- room.py: Room system
- region_content.py: Region content management
- action_handler.py: Action handler system
- room_config.py: Room configuration data
- game.py: Main game class and loop

To run the game, use: python game.py
Or import and use the Game class from game.py
"""

from game import main

if __name__ == '__main__':
    main()
