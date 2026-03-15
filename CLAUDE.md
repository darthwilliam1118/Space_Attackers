# Space Attackers - Claude Code Guidelines

## Architecture
- Keep game logic strictly separated from rendering
- Classes like Ship, Alien, Bullet contain pure logic only (position, 
  velocity, health, collision bounds) with no direct Arcade/rendering calls
- The main Game/Window class handles all drawing
- This separation ensures unit tests never need a display

## Project Structure
- Source code in src
- Tests in tests/
- Assets in assets/images/ and assets/sounds/

## Testing
- Use pytest
- All logic classes must be instantiatable without a game window
- Do not load image/sound assets in __init__ — lazy load or inject them
- Run tests with: pytest --cov=src

## Dependencies
- Python 3.11+
- Arcade 3.x
- Do not introduce new dependencies without flagging it

## Code Style
- Type hints on all functions
- Keep classes focused and single-responsibility