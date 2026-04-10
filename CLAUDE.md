# Space Attackers - Claude Code Guidelines

## Architecture
- Keep game logic strictly separated from rendering
- Classes like Ship, Alien, Bullet contain pure logic only (position, 
  velocity, health, collision bounds) with no direct Arcade/rendering calls
- The main Game/Window class handles all drawing
- This separation ensures unit tests never need a display

## Claude Code Behavior
- When implementing a major new feature, make a plan and present for approval before editing any files
- Ask any questions needed to resolve ambiguities or conflicts in the plan.
- Don't use unicode characters in debug output just regular ascii

## Code Quality Standards

- Formatter: Black (line length 100). Run `black .` before committing.
- Linter: Ruff. Run `ruff check .` and fix all errors before committing.
- Type hints: Use them on all function signatures.
- No unused imports, no bare `except:` clauses.
- Follow existing patterns in the codebase — don't introduce new ones without discussion.

## Before Submitting Any Code
1. `ruff check .` — must be clean
2. `black .` — must be clean  
3. Code must not break existing game state machine patterns

## Project Structure
- Source code in src
- Tests in tests/
- Assets in assets/images/ and assets/sounds/

## Feature Brief Index
- Background / star field: docs/features/background.md
- Particle effects:        docs/features/particles.md
- Text and HUD:            docs/features/text-and-hud.md
- Score popups:            docs/features/score-popup.md
- Player ship:             docs/features/player_ship.md
- Enemy grid:              docs/features/enemy_grid.md
- State machine:           docs/features/state_machine.md

## Testing
- Use pytest
- All logic classes must be instantiatable without a game window
- Do not load image/sound assets in __init__ — lazy load or inject them
- Run tests with: pytest --cov=src

## Dependencies
- Python 3.14
- Arcade 3.x
- Do not introduce new dependencies without flagging it

## Arcade 3.x — Critical API Notes

Claude Code's training data contains significant amounts of Arcade 2.x code
which is NOT compatible with Arcade 3.x. This project uses Arcade 3.3.3.
Always use the 3.x API. Key breaking changes to be aware of:

### Window and View
- arcade.Window signature changed — use keyword args:
  arcade.Window(width, height, title)
- View switching: self.window.show_view(view) — unchanged but
  on_show_view() replaces on_show()
- on_hide_view() replaces on_hide()

### Drawing
- All draw calls must be inside an explicit begin/end block in 3.x:
  def on_draw(self):
      self.clear()                  # replaces arcade.start_render()
      self.scene.draw()             # or sprite_list.draw()
- arcade.start_render() is REMOVED in 3.x — use self.clear() instead
- arcade.finish_render() is REMOVED — not needed

### SpriteList and Scene
- arcade.Scene is the preferred way to manage layered SpriteLists in 3.x
- Scene creation: arcade.Scene()
- Add a new empty list: scene.add_sprite_list("name")
- Add a sprite to a named list: scene.add_sprite("name", sprite)
- Draw all layers: scene.draw()
- Access a list: scene["name"]

### Sprites
- When constructing all sprites, use global config setting SPRITE_SCALE
- Sprite constructor: arcade.Sprite(path, scale=1.0) — path is now
  keyword preferred
- arcade.Sprite.textures is a list — assign self.texture to set current
- remove_from_sprite_lists() still works in 3.x
- SpriteList.update() no longer calls sprite.update() automatically in
  3.x — call sprite_list.update(delta_time) and ensure sprites accept
  delta_time in their update() signature, OR iterate and call manually

### Spritesheet loading
- arcade.load_spritesheet() signature in 3.x:
  arcade.load_spritesheet(
      file_path,
      sprite_width,
      sprite_height,
      columns,
      count
  )
  Returns a list of Texture objects

### Text
- arcade.draw_text() still works but arcade.Text object is preferred
- arcade.Text constructor in 3.x:
  arcade.Text(text, x, y, color, font_size, font_name=...,
              anchor_x="left", anchor_y="baseline", multiline=False,
              width=None)
- Call .draw() on the Text object inside on_draw()
- Update text content: text_obj.text = "new string"

### Input
- Key constants unchanged: arcade.key.LEFT, arcade.key.SPACE etc.
- on_key_press(key, modifiers) and on_key_release(key, modifiers)
  unchanged

### Sound
- arcade.load_sound() and arcade.play_sound() unchanged in 3.x

### Physics engines
- arcade.PhysicsEngineSimple constructor changed slightly — check docs
  if used

### General rule
- If in doubt about any Arcade API call, ask before writing it rather
  than guessing from 2.x memory. Arcade 3.x docs are at:
  https://api.arcade.academy/en/latest/
  
## Code Style
- Type hints on all functions
- Keep classes focused and single-responsibility

## Type Checking
- Pylance type checking set to basic
- All functions must have type hints on parameters and return values
- Fix any type errors introduced before committing

## Sprite Animation
- Use sprite sheets via arcade.load_spritesheet(), not individual frame files
- Animated sprites manage their own frame timing using delta_time
- Animation state tracked as string ("idle", "diving", "dying") on sprite
- Explosions are self-contained AnimatedSprite subclasses that call
  remove_from_sprite_lists() on final frame — no external tracking needed
- Add an "explosions" layer to Scene so they render above enemies and bullets
- All game animations and sounds should continue for a max of 2 seconds when PLAYER_KILLED including background, explosions, bullets and missiles.

## Fonts
- Load TTF fonts once at startup via arcade.load_font(resource_path(...))
- Use arcade.Text objects for HUD elements drawn every frame, not arcade.draw_text()
- Font name in arcade.Text is the font's internal name, not the filename
- KenVector Future and KenVector Future Thin are the target fonts for all game UI
  and are located in assets/fonts

## Arcade Performance Gotchas
- ShapeElementList is for STATIC geometry only — never use it for objects
  that move every frame. It requires a full GPU buffer rebuild on any
  change, causing microstutters. Use SpriteList instead.
- ProceduralStarField uses SpriteList with arcade.make_circle_texture()
  sprites — NOT ShapeElementList. Speeds stored in a parallel list since
  SpriteList doesn't support per-sprite metadata.

## Build
- Target: self-contained Windows .exe via PyInstaller
- All assets must be loaded using resource paths compatible with PyInstaller bundles
- Use a helper function for asset paths that handles both dev and bundled contexts