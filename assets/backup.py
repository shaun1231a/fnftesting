import pygame, sys, json, random, os, xml.etree.ElementTree as ET, re

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
bigfont = pygame.font.Font(None, 72)

# --- Constants ---
ARROWS = ["left", "down", "up", "right"]
opponent_x = WIDTH//4 - 150
arrow_spacing = 80
arrow_positions_left = {dir_name: opponent_x + i*arrow_spacing for i, dir_name in enumerate(ARROWS)}

player_x = WIDTH - WIDTH//4 - 100
arrow_positions_right = {dir_name: player_x + i*arrow_spacing for i, dir_name in enumerate(ARROWS)}

SPAWN_AHEAD_TIME = 1000  # ms before note hits target

difficulties = ["easy", "normal", "hard"]
selected_difficulty_index = 1
selected_difficulty = difficulties[selected_difficulty_index]

PERFECT_WINDOW = 25
GOOD_WINDOW = 50
MISS_WINDOW = 100

WHITE = (255,255,255)
GRAY = (100,100,100)
BLACK = (0,0,0)
GREEN = (0,255,0)
RED = (255,80,80)
BLUE = (100,150,255)
YELLOW = (255,255,0)
NotePurple = (126, 106, 181)
NoteGreen = (87, 191, 111)
NoteBlue = (109, 192, 199)
NoteRed = (190, 118, 131)

miss_sound = pygame.mixer.Sound("sounds/miss1.mp3")

pause_sound = pygame.mixer.Sound("sounds/pause.mp3")
pause_sound.set_volume(0.3)  # quieter background hum while paused
pause_channel = None

pause_start_time = None
pause_accumulated = 0  # total time spent paused

NOTE_SIZE = (80, 80)
bf_idle_timer = 0
IDLE_DELAY = 500

CAMERA_OFFSET_X = 120  # how far the camera moves left/right
CAMERA_OFFSET_Y = 20  # optional vertical movement
camera_x = 0
camera_y = 0

# --- Load images ---
w1bg_image = pygame.image.load("images/week1/bg.png").convert()
w1bg_image = pygame.transform.scale(w1bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w2bg_image = pygame.image.load("images/week2/halloween_bg.png").convert()
w2bg_image = pygame.transform.scale(w2bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w3bg_image = pygame.image.load("images/week3/bg.png").convert()
w3bg_image = pygame.transform.scale(w3bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w4bg_image = pygame.image.load("images/week4/bg.png").convert()
w4bg_image = pygame.transform.scale(w4bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w5bg_image = pygame.image.load("images/week5/bg.png").convert()
w5bg_image = pygame.transform.scale(w5bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w6bg_image = pygame.image.load("images/week6/bg.png").convert()
w6bg_image = pygame.transform.scale(w6bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
w6bg2_image = pygame.image.load("images/week6/bg2.png").convert()
w6bg2_image = pygame.transform.scale(w6bg2_image, (WIDTH * 1.3, HEIGHT * 1.3))
w7bg_image = pygame.image.load("images/week7/bg.png").convert()
w7bg_image = pygame.transform.scale(w7bg_image, (WIDTH * 1.3, HEIGHT * 1.3))
menuBg_image = pygame.image.load("images/menuBG.png").convert()
menuBg_image = pygame.transform.scale(menuBg_image, (WIDTH, HEIGHT))

CAMERA_POSITIONS = {
    "bf": (300, 0),
    "gf": (0, 0),
    "dad": (-50, 0),
    "spooky": (0, 0),
    "pico": (0, 0),
    "mom": (0, 0),
    "parents": (0, 0),
    "senpai": (0, 0),
    "spirit": (0, 200),
    "tankman": (0, 0)
}

# --- Load icons ---
bf_icon = pygame.image.load("images/icons/icon-bf.png").convert_alpha()
dad_icon = pygame.image.load("images/icons/icon-dad.png").convert_alpha()
tankman_icon = pygame.image.load("images/icons/icon-tankman.png").convert_alpha()
spooky_icon = pygame.image.load("images/icons/icon-spooky.png").convert_alpha()
pico_icon = pygame.image.load("images/icons/icon-pico.png").convert_alpha()
mom_icon = pygame.image.load("images/icons/icon-mom.png").convert_alpha()
parents_icon = pygame.image.load("images/icons/icon-parents.png").convert_alpha()
senpai_icon = pygame.image.load("images/icons/icon-senpai.png").convert_alpha()
spirit_icon = pygame.image.load("images/icons/icon-spirit.png").convert_alpha()
ICON_SIZE = (70, 70)
bf_icon = pygame.transform.scale(bf_icon, ICON_SIZE)
dad_icon = pygame.transform.scale(dad_icon, ICON_SIZE)
tankman_icon = pygame.transform.scale(tankman_icon, ICON_SIZE)
spooky_icon = pygame.transform.scale(spooky_icon, ICON_SIZE)
pico_icon = pygame.transform.scale(pico_icon, ICON_SIZE)
mom_icon = pygame.transform.scale(mom_icon, ICON_SIZE)
parents_icon = pygame.transform.scale(parents_icon, ICON_SIZE)
senpai_icon = pygame.transform.scale(senpai_icon, ICON_SIZE)
spirit_icon = pygame.transform.scale(spirit_icon, ICON_SIZE)

game_state = "alive"
death_triggered = False
# --- Health ---
health = 0.5
HEALTH_BAR_WIDTH = 300
HEALTH_BAR_HEIGHT = 15
HEALTH_BAR_X = WIDTH//2 - HEALTH_BAR_WIDTH//2
HEALTH_CHANGE_PERFECT = 0.02
HEALTH_CHANGE_GOOD = 0.01
HEALTH_CHANGE_HOLD = 0.001
HEALTH_CHANGE_MISS = -0.05

def update_health(hit_type):
    global health, game_state, fade_timer
    if hit_type == "Perfect": health += HEALTH_CHANGE_PERFECT
    elif hit_type == "Good": health += HEALTH_CHANGE_GOOD
    elif hit_type == "Hold": health += HEALTH_CHANGE_HOLD
    elif hit_type == "Miss": health += HEALTH_CHANGE_MISS
    health = max(0, min(1, health))
    if health <= 0 and not getattr(bf_char, "dead", False):
        bf_char.dead = True
        game_state = "death"

def draw_healthbar():
    pygame.draw.rect(screen, RED, (HEALTH_BAR_X, HEALTH_BAR_Y, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
    green_width = int(HEALTH_BAR_WIDTH * health)
    pygame.draw.rect(screen, GREEN, (HEALTH_BAR_X + (HEALTH_BAR_WIDTH - green_width), HEALTH_BAR_Y, green_width, HEALTH_BAR_HEIGHT))
    divider_x = HEALTH_BAR_X + int(HEALTH_BAR_WIDTH * (1 - health))
    icon_y = HEALTH_BAR_Y - (ICON_SIZE[1] - HEALTH_BAR_HEIGHT) // 2
    screen.blit(active_icon, (divider_x - ICON_SIZE[0] + 5, icon_y))
    screen.blit(bf_icon, (divider_x - 5, icon_y))


# --- Load note assets ---
NOTE_COLOR_NAMES = {
    "up": "green",
    "down": "blue",
    "left": "purple",
    "right": "red"
}


def load_note_assets(xml_path, image_path):
    sheet = pygame.image.load(image_path).convert_alpha()
    tree = ET.parse(xml_path)
    root = tree.getroot()

    note_images = {"player": {}, "opponent": {}}

    # Initialize all types
    for owner in ["player", "opponent"]:
        note_images[owner]["static"] = {d: None for d in ARROWS}
        note_images[owner]["press"] = {d: None for d in ARROWS}
        note_images[owner]["instance"] = {d: None for d in ARROWS}

    for sub in root.findall("SubTexture"):
        name = sub.attrib["name"].lower()
        x, y, w, h = int(sub.attrib["x"]), int(sub.attrib["y"]), int(sub.attrib["width"]), int(sub.attrib["height"])
        frame = sheet.subsurface(pygame.Rect(x, y, w, h))
        frame = pygame.transform.smoothscale(frame, NOTE_SIZE)

        for d in ARROWS:
            color_name = NOTE_COLOR_NAMES[d]

            # Moving note ("instance")
            if f"{color_name} instance 10000" in name:
                note_images["player"]["instance"][d] = frame
                note_images["opponent"]["instance"][d] = frame

            # Pressed overlay
            elif f"{d} press" in name:
                note_images["player"]["press"][d] = frame
                note_images["opponent"]["press"][d] = frame

            elif f"arrow static instance 1" in name and d == "left":
                note_images["player"]["static"]["left"] = frame
                note_images["opponent"]["static"]["left"] = frame
            elif f"arrow static instance 2" in name and d == "down":
                note_images["player"]["static"]["down"] = frame
                note_images["opponent"]["static"]["down"] = frame
            elif f"arrow static instance 3" in name and d == "up":
                note_images["player"]["static"]["right"] = frame
                note_images["opponent"]["static"]["right"] = frame
            elif f"arrow static instance 4" in name and d == "right":
                note_images["player"]["static"]["up"] = frame
                note_images["opponent"]["static"]["up"] = frame

    return note_images

def load_pixel_notes(xml_path, image_path):
    import xml.etree.ElementTree as ET

    pixel_notes = {
        "player": {"static": {}, "press": {}, "instance": {}},
        "opponent": {"static": {}, "press": {}, "instance": {}}
    }

    sheet = pygame.image.load(image_path).convert_alpha()
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # For reference:
    # staticLeft0001 -> static
    # noteLeft0001 -> instance (moving)
    # pressedLeft0001/0002 -> press
    # confirmLeft0001/0002 -> press (confirm)
    for sub in root.findall("SubTexture"):
        name = sub.attrib["name"].lower()
        x, y, w, h = int(sub.attrib["x"]), int(sub.attrib["y"]), int(sub.attrib["width"]), int(sub.attrib["height"])
        frame = sheet.subsurface(pygame.Rect(x, y, w, h)).convert_alpha()
        frame = pygame.transform.scale(frame, NOTE_SIZE)

        # Determine direction
        if "left" in name:
            d = "left"
        elif "down" in name:
            d = "down"
        elif "up" in name:
            d = "up"
        elif "right" in name:
            d = "right"
        else:
            continue

        # Determine type
        if "static" in name:
            for owner in pixel_notes:
                pixel_notes[owner]["static"][d] = frame
        elif "note" in name:
            for owner in pixel_notes:
                pixel_notes[owner]["instance"][d] = frame
        elif "pressed" in name or "confirm" in name:
            for owner in pixel_notes:
                pixel_notes[owner]["press"][d] = frame

    return pixel_notes

pixel_note_images = load_pixel_notes("notes/arrows-pixels.xml", "assets/notes/arrows-pixels.png")
note_images = load_note_assets("notes/NOTE_assets.xml", "assets/notes/NOTE_assets.png")


def load_note_splashes(xml_path, image_path):
    sheet = pygame.image.load(image_path).convert_alpha()
    tree = ET.parse(xml_path)
    root = tree.getroot()

    splashes = {color: [] for color in ["blue", "green", "purple", "red"]}

    for sub in root.findall("SubTexture"):
        name = sub.attrib["name"].lower()
        x, y, w, h = int(sub.attrib["x"]), int(sub.attrib["y"]), int(sub.attrib["width"]), int(sub.attrib["height"])
        frame = sheet.subsurface(pygame.Rect(x, y, w, h)).convert_alpha()

        for color in splashes.keys():
            if color in name:
                splashes[color].append(frame)
                break

    return splashes

note_splashes = load_note_splashes("notes/noteSplashes.xml", "assets/notes/noteSplashes.png")
active_splashes = []

# --- Character classes ---
import pygame
import xml.etree.ElementTree as ET
import re

class Boyfriend:
    def __init__(self, x, y, style="normal", scale=1.0, name_mapping=None):
        # --- Determine file paths based on style ---
        if style == "pixel":
            image_path = "characters/boyfriend/bfPixel.png"
            xml_path = "characters/boyfriend/bfPixel.xml"
        else:
            image_path = "characters/boyfriend/BOYFRIEND.png"
            xml_path = "characters/boyfriend/BOYFRIEND.xml"

        self.style = style
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()
        self.animations = {}

        if name_mapping is None:
            name_mapping = {
                "idle": "idle",
                "up": "up",
                "down": "down",
                "left": "left",
                "right": "right"
            }
        self.name_mapping = name_mapping

        # --- Load frames ---
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0, y0, w, h = int(sub.attrib["x"]), int(sub.attrib["y"]), int(sub.attrib["width"]), int(sub.attrib["height"])
            frame = sheet.subsurface(pygame.Rect(x0, y0, w, h))

            if scale != 1.0 and style == "pixel":
                frame = pygame.transform.scale(frame, (int(w * scale), int(h * scale)))
            elif scale != 1.0 and style == "normal":
                frame = pygame.transform.smoothscale(frame, (int(w * scale), int(h * scale)))

            if "shaking" in name and "idle" in name:
                continue  # skip shaking idle frames

            # --- Idle frames ---
            if "idle" in name:
                self.animations.setdefault("idle", []).append(frame)
            # --- Dead loop (idle2) ---
            if "dead loop" in name:
                self.animations.setdefault("idle2", []).append(frame)

            if style == "normal":
                # --- Normal BF directions ---
                match_note = re.match(r"bf note (up|down|left|right)0000", name)
                if match_note:
                    dir_name = match_note.group(1)
                    self.animations.setdefault(dir_name, []).append(frame)
                # --- Normal BF miss ---
                match_miss = re.match(r"bf note (up|down|left|right) miss\d+", name)
                if match_miss:
                    dir_name = match_miss.group(1)
                    anim_name = f"BF NOTE {dir_name.upper()} MISS0000"
                    self.animations.setdefault(anim_name, []).append(frame)

            elif style == "pixel":
                # --- Pixel BF directions ---
                if "note" in name and "miss" not in name:  # hit frames
                    if "down note" in name:
                        self.animations.setdefault("down", []).append(frame)
                    elif "up note" in name:
                        self.animations.setdefault("up", []).append(frame)
                    elif "left note" in name:
                        self.animations.setdefault("left", []).append(frame)
                    elif "right note" in name:
                        self.animations.setdefault("right", []).append(frame)
                # --- Pixel BF miss frames ---
                elif "miss" in name:
                    if "down miss" in name:
                        self.animations.setdefault("down_miss", []).append(frame)
                    elif "up miss" in name:
                        self.animations.setdefault("up_miss", []).append(frame)
                    elif "left miss" in name:
                        self.animations.setdefault("left_miss", []).append(frame)
                    elif "right miss" in name:
                        self.animations.setdefault("right_miss", []).append(frame)

        # --- ADDITION: Pixel death animation loading ---
        if style == "pixel":
            death_image_path = "characters/boyfriend/bfPixelsDEAD.png"
            death_xml_path = "characters/boyfriend/bfPixelsDEAD.xml"

            if os.path.exists(death_image_path) and os.path.exists(death_xml_path):
                death_sheet = pygame.image.load(death_image_path).convert_alpha()
                death_tree = ET.parse(death_xml_path)
                death_root = death_tree.getroot()

                death_frames = []
                for sub in death_root.findall("SubTexture"):
                    name = sub.attrib["name"].lower()
                    if "retry confirm" in name:  # only load retry confirm frames
                        x0, y0, w, h = int(sub.attrib["x"]), int(sub.attrib["y"]), int(sub.attrib["width"]), int(sub.attrib["height"])
                        frame = death_sheet.subsurface(pygame.Rect(x0, y0, w, h))
                        if scale != 1.0:
                            frame = pygame.transform.scale(frame, (int(w * scale), int(h * scale)))
                        death_frames.append(frame)

                if death_frames:
                    self.animations["idle2"] = death_frames

        # --- Initialize ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.dead = False
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def play_note(self, direction, hit=True):
        """
        Play a note animation for a given direction.
        direction: "up", "down", "left", "right"
        hit: True if hit note, False if missed
        """
        if self.style == "pixel":
            key = direction if hit else f"{direction}_miss"
        else:
            key = direction.upper() if hit else f"BF NOTE {direction.upper()} MISS0000"
        self.play(key)

class Girlfriend:
    def __init__(self, x, y, style="normal", scale=0.7):
        # Determine file paths based on style
        if style == "pixel":
            image_path = "characters/girlfriend/gfPixel.png"
            xml_path = "characters/girlfriend/gfPixel.xml"
        else:
            image_path = "characters/girlfriend/gf.png"
            xml_path = "characters/girlfriend/gf.xml"

        self.style = style
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.frames = []
        max_height = 0
        temp_frames = []

        # Exclude frames differently if needed
        exclude_keywords = ["blowing", "fear", "cheer", "sad", "hair", "note"] if style == "normal" else []

        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            if any(keyword in name for keyword in exclude_keywords):
                continue

            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])
            rotated = sub.attrib.get("rotated", "false").lower() == "true"

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))
            if rotated:
                frame_surface = pygame.transform.rotate(frame_surface, 90)

            if scale != 1.0 and style == "pixel":
                frame_surface = pygame.transform.scale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale), int(frame_surface.get_height() * scale)))
            elif scale != 1.0 and style == "normal":
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale), int(frame_surface.get_height() * scale)))

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append(frame_surface)

        # Align frames to baseline
        for frame_surface in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h
            aligned_surface = pygame.Surface((frame_surface.get_width(), max_height), pygame.SRCALPHA)
            aligned_surface.blit(frame_surface, (0, offset_y))
            self.frames.append(aligned_surface)

        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 60
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class DaddyDearest:
    def __init__(self, image_path, xml_path, x, y, scale=0.8):
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}

        max_height = 0
        temp_frames = []

        # First pass: load all frames (rotated or not)
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])
            rotated = sub.attrib.get("rotated", "false").lower() == "true"

            if rotated:
                # Create original sized surface
                frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
                frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))
                # Rotate 90 degrees clockwise
                frame_surface = pygame.transform.rotate(frame_surface, 90)  # use -90 for FNF format

            else:
                frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
                frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if scale != 1.0:
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale), int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface))

        # Second pass: align all frames to the same baseline
        for name, frame_surface in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h  # amount to shift down so feet align

            # Create aligned surface
            aligned_surface = pygame.Surface(
                (frame_surface.get_width(), max_height), pygame.SRCALPHA
            )
            aligned_surface.blit(frame_surface, (0, offset_y))

            # Assign to animation dictionary
            if "idle" in name:
                self.animations["idle"].append(aligned_surface)
            elif "singup" in name:
                self.animations["up"].append(aligned_surface)
            elif "singdown" in name:
                self.animations["down"].append(aligned_surface)
            elif "singleft" in name:
                self.animations["left"].append(aligned_surface)
            elif "singright" in name:
                self.animations["right"].append(aligned_surface)

        # Animation control
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames: return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Spooky:
    def __init__(self, image_path, xml_path, x, y, scale=0.8):
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}

        max_height = 0
        temp_frames = []

        # First pass: load all frames (rotated or not)
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if scale != 1.0:
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale), int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface))

        # Second pass: align all frames to the same baseline
        for name, frame_surface in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h  # amount to shift down so feet align

            # Create aligned surface
            aligned_surface = pygame.Surface(
                (frame_surface.get_width(), max_height), pygame.SRCALPHA
            )
            aligned_surface.blit(frame_surface, (0, offset_y))

            # Assign to animation dictionary
            if "idle" in name:
                self.animations["idle"].append(aligned_surface)
            elif "singup" in name:
                self.animations["up"].append(aligned_surface)
            elif "singdown" in name:
                self.animations["down"].append(aligned_surface)
            elif "singleft" in name:
                self.animations["left"].append(aligned_surface)
            elif "singright" in name:
                self.animations["right"].append(aligned_surface)

        # Animation control
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames: return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Pico:
    def __init__(self, image_path, xml_path, x, y, scale=1.0):
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}

        max_height = 0
        temp_frames = []

        # --- Load all frames, handling rotation ---
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])
            rotated = sub.attrib.get("rotated", "false").lower() == "true"

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if rotated:
                frame_surface = pygame.transform.rotate(frame_surface, 90)
            frame_surface = pygame.transform.flip(frame_surface, True, False)

            if scale != 1.0:
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale),
                     int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface))

        # --- Align all frames to same baseline ---
        for name, frame_surface in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h

            aligned_surface = pygame.Surface(
                (frame_surface.get_width(), max_height), pygame.SRCALPHA
            )
            aligned_surface.blit(frame_surface, (0, offset_y))

            # --- Assign to correct animation list ---
            if "idle" in name:
                self.animations["idle"].append(aligned_surface)
            elif "up" in name:
                self.animations["up"].append(aligned_surface)
            elif "down" in name:
                self.animations["down"].append(aligned_surface)
            elif "left" in name:
                self.animations["left"].append(aligned_surface)
            elif "right" in name:
                self.animations["right"].append(aligned_surface)

        # --- Animation control ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Mom:
    def __init__(self, image_path, xml_path, x, y, scale=1.0):
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}
        max_height = 0
        temp_frames = []

        # --- Parse XML and extract frames ---
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])

            # --- Optional offset (used for vertical alignment) ---
            frameX = int(sub.attrib.get("frameX", 0))
            frameY = int(sub.attrib.get("frameY", 0))

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if scale != 1.0:
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale),
                     int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface, frameY))

        # --- Align to consistent baseline ---
        for name, frame_surface, frameY in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h - frameY

            aligned = pygame.Surface(
                (frame_surface.get_width(), max_height), pygame.SRCALPHA
            )
            aligned.blit(frame_surface, (0, offset_y))

            if "idle" in name:
                self.animations["idle"].append(aligned)
            elif "up" in name:
                self.animations["up"].append(aligned)
            elif "down" in name:
                self.animations["down"].append(aligned)
            elif "left" in name:
                self.animations["left"].append(aligned)
            elif "right" in name:
                self.animations["right"].append(aligned)

        # --- Animation controls ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Parents:
    def __init__(self, image_path, xml_path, x, y, scale=1.0, who="mom"):
        """
        who: "mom" or "dad" — determines which parent's frames to use.
        """
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Prepare animation dicts for both parents
        self.all_anims = {
            "mom": {"idle": [], "up": [], "down": [], "left": [], "right": []},
            "dad": {"idle": [], "up": [], "down": [], "left": [], "right": []}
        }

        max_height = 0
        temp_frames = []

        # --- Parse XML ---
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])
            frameX = int(sub.attrib.get("frameX", 0))
            frameY = int(sub.attrib.get("frameY", 0))

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if scale != 1.0:
                frame_surface = pygame.transform.smoothscale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale),
                     int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface, frameY))

        # --- Sort frames into correct parent + direction ---
        for name, frame_surface, frameY in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h - frameY

            aligned = pygame.Surface((frame_surface.get_width(), max_height), pygame.SRCALPHA)
            aligned.blit(frame_surface, (0, offset_y))

            if "mom" in name:
                self.all_anims["mom"]["down" if "down" in name else
                "up" if "up" in name else
                "left" if "left" in name else
                "right" if "right" in name else "idle"].append(aligned)
            elif "dad" in name:
                self.all_anims["dad"]["down" if "down" in name else
                "up" if "up" in name else
                "left" if "left" in name else
                "right" if "right" in name else "idle"].append(aligned)
            elif "parent christmas idle" in name:
                # Assign shared idle frames to both parents
                for p in ["mom", "dad"]:
                    self.all_anims[p]["idle"].append(aligned)

        # --- Choose which parent to show ---
        self.who = who.lower()
        self.animations = self.all_anims[self.who]

        # --- Animation controls ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Senpai:
    def __init__(self, image_path, xml_path, x, y, scale=1.0, song_name="senpai"):
        self.song_name = song_name.lower()
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Prepare animation dictionary
        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}
        temp_frames = []
        max_height = 0

        # --- Parse XML and collect frames ---
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            x0 = int(sub.attrib["x"])
            y0 = int(sub.attrib["y"])
            w = int(sub.attrib["width"])
            h = int(sub.attrib["height"])
            frameX = int(sub.attrib.get("frameX", 0))
            frameY = int(sub.attrib.get("frameY", 0))

            # --- Determine if this frame should be used ---
            if self.song_name == "senpai":
                if "angry senpai" in name:
                    continue
            elif self.song_name == "roses":
                if "angry senpai" not in name:
                    continue

            frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))

            if scale != 1.0:
                frame_surface = pygame.transform.scale(
                    frame_surface,
                    (int(frame_surface.get_width() * scale),
                     int(frame_surface.get_height() * scale))
                )

            max_height = max(max_height, frame_surface.get_height())
            temp_frames.append((name, frame_surface, frameY))

        # --- Align frames to baseline ---
        for name, frame_surface, frameY in temp_frames:
            h = frame_surface.get_height()
            offset_y = max_height - h - frameY
            aligned = pygame.Surface((frame_surface.get_width(), max_height), pygame.SRCALPHA)
            aligned.blit(frame_surface, (0, offset_y))

            if "idle" in name:
                self.animations["idle"].append(aligned)
            elif "up" in name:
                self.animations["up"].append(aligned)
            elif "down" in name:
                self.animations["down"].append(aligned)
            elif "left" in name:
                self.animations["left"].append(aligned)
            elif "right" in name:
                self.animations["right"].append(aligned)

        # --- Animation controls ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        # fallback in case no frames loaded
        if self.animations[self.current]:
            self.image = self.animations[self.current][0]
        else:
            self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Spirit:
    def __init__(self, image_path, txt_path, x, y, scale=1.0):
        sheet = pygame.image.load(image_path).convert_alpha()
        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}

        # --- Read and parse txt ---
        with open(txt_path, "r") as f:
            lines = f.readlines()

        max_height = 0
        temp_frames = []

        for line in lines:
            line = line.strip()
            if not line or "=" not in line:
                continue
            # split into name and coordinates
            name_part, coords_part = line.split("=")
            name = name_part.strip().lower()  # e.g., "idle spirit_0"
            coords = [int(i) for i in coords_part.strip().split()]
            x0, y0, w, h = coords

            frame = sheet.subsurface(pygame.Rect(x0, y0, w, h))

            # Scale frame if needed
            if scale != 1.0:
                frame = pygame.transform.scale(frame, (int(w * scale), int(h * scale)))

            max_height = max(max_height, frame.get_height())
            temp_frames.append((name, frame))

        # Align frames to baseline
        for name, frame in temp_frames:
            h = frame.get_height()
            aligned = pygame.Surface((frame.get_width(), max_height), pygame.SRCALPHA)
            offset_y = max_height - h
            aligned.blit(frame, (0, offset_y))

            # Assign to animations dict
            if "idle" in name:
                self.animations["idle"].append(aligned)
            elif "up" in name:
                self.animations["up"].append(aligned)
            elif "down" in name:
                self.animations["down"].append(aligned)
            elif "left" in name:
                self.animations["left"].append(aligned)
            elif "right" in name:
                self.animations["right"].append(aligned)

        # --- Animation controls ---
        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        if self.animations[self.current]:
            self.image = self.animations[self.current][0]
        else:
            self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Tankman:
    def __init__(self, image_path, xml_path, x, y, scale=0.8):
        sheet = pygame.image.load(image_path).convert_alpha()
        tree = ET.parse(xml_path)
        root = tree.getroot()

        self.animations = {"idle": [], "up": [], "down": [], "left": [], "right": []}
        max_height = 0
        temp_frames = []

        # First pass: load all frames
        for sub in root.findall("SubTexture"):
            name = sub.attrib["name"].lower()
            w, h = int(sub.attrib["width"]), int(sub.attrib["height"])
            x0, y0 = int(sub.attrib["x"]), int(sub.attrib["y"])

            frame = pygame.Surface((w, h), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(x0, y0, w, h))
            frame = pygame.transform.rotate(frame, 180)
            frame = pygame.transform.flip(frame, False, True)

            if scale != 1.0:
                frame = pygame.transform.smoothscale(frame, (int(w*scale), int(h*scale)))

            max_height = max(max_height, frame.get_height())
            temp_frames.append((name, frame))

        # Second pass: align frames to baseline
        for name, frame in temp_frames:
            h = frame.get_height()
            offset_y = max_height - h
            aligned = pygame.Surface((frame.get_width(), max_height), pygame.SRCALPHA)
            aligned.blit(frame, (0, offset_y))

            if "idle" in name:
                self.animations["idle"].append(aligned)
            elif "up" in name:
                self.animations["up"].append(aligned)
            elif "down" in name:
                self.animations["down"].append(aligned)
            elif "left" in name:
                self.animations["left"].append(aligned)
            elif "right" in name:
                self.animations["right"].append(aligned)

        self.current = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 100
        self.image = self.animations[self.current][0]
        self.rect = self.image.get_rect(center=(x, y))

    def play(self, anim):
        if anim != self.current and anim in self.animations and self.animations[anim]:
            self.current = anim
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, dt):
        frames = self.animations[self.current]
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# --- Notes ---
ARROW_COLORS = {"left":NotePurple,"down":NoteBlue,"up":NoteGreen,"right":NoteRed}
class Note:
    def __init__(self,direction,spawn_time,owner, style="normal"):
        self.direction=direction
        self.spawn_time=spawn_time
        self.owner=owner
        self.hit=False
        self.start_y=-NOTE_SIZE[1]
        self.target_y=TARGET_Y
        self.y=self.start_y
        self.x=arrow_positions_right[direction] if owner=="player" else arrow_positions_left[direction]
        self.entered_hit_zone = False
        self.stored_y = self.y
        self.style = style

        # Choose which image set to use
        if self.style == "pixel":
            self.image = pixel_note_images[owner]["instance"][direction]
        else:
            self.image = note_images[owner]["instance"][direction]

    def update(self, song_time):
        progress = (song_time - (self.spawn_time - SPAWN_AHEAD_TIME)) / SPAWN_AHEAD_TIME

        if preferences["upscroll"]:
            self.y = self.start_y - (self.start_y - self.target_y) * progress
        else:
            self.y = self.start_y + (self.target_y - self.start_y) * progress

        # Check if entered hit zone
        if not self.entered_hit_zone:
            if (not preferences["upscroll"] and self.y >= self.target_y) or \
                    (preferences["upscroll"] and self.y <= self.target_y):
                self.entered_hit_zone = True

        # For opponent notes
        if self.owner == "opponent" and not self.hit and not getattr(self, "animation_played", False):
            if (not preferences["upscroll"] and self.y >= TARGET_Y) or (preferences["upscroll"] and self.y <= TARGET_Y):
                active_opponent_char.play(self.direction)
                self.animation_played = True

    def draw(self):
        if self.style == "pixel":
            img = pixel_note_images[self.owner]["instance"][self.direction]
        else:
            img = note_images[self.owner]["instance"][self.direction]
        screen.blit(img,img.get_rect(center=(self.x,self.y)))

    def check_hit(self, key_pressed_now, song_time):
        if self.hit:
            return 0, None

        points = 0
        hit_type = None
        time_diff = abs(song_time - self.spawn_time)

        if key_pressed_now and time_diff <= MISS_WINDOW:
            if time_diff <= PERFECT_WINDOW:
                points += 300
                hit_type = "Perfect"
            elif time_diff <= GOOD_WINDOW:
                points += 150
                hit_type = "Good"
            else:
                points += 50
                hit_type = "Bad"

            self.hit = True

        return points, hit_type

class HoldNote(Note):
    def __init__(self, direction, spawn_time, owner, sustain_length, style="normal"):
        super().__init__(direction, spawn_time, owner)
        self.sustain_length = sustain_length
        self.head_hit = False
        self.trail_height = (self.sustain_length / SPAWN_AHEAD_TIME) * (TARGET_Y - self.start_y)
        self.completed = False
        self.style = style

        # Choose which image set to use
        if self.style == "pixel":
            self.image = pixel_note_images[owner]["instance"][direction]
        else:
            self.image = note_images[owner]["instance"][direction]

    def update(self, song_time, key_held=False, dt=16):
        scroll_speed = (TARGET_Y - self.start_y) / SPAWN_AHEAD_TIME
        if preferences["upscroll"]:
            scroll_speed = -scroll_speed

        # --- Player logic ---
        if self.owner == "player":
            if not self.head_hit:
                progress = (song_time - (self.spawn_time - SPAWN_AHEAD_TIME)) / SPAWN_AHEAD_TIME
                if preferences["upscroll"]:
                    self.y = self.start_y - (self.start_y - self.target_y) * progress
                else:
                    self.y = self.start_y + (self.target_y - self.start_y) * progress
            else:
                # Keep head at TARGET_Y for downscroll, or at start_y for upscroll
                self.y = TARGET_Y if not preferences["upscroll"] else self.start_y
                if key_held:
                    self.trail_height -= abs(scroll_speed) * dt
                    if self.trail_height <= 0:
                        self.trail_height = 0
                        self.completed = True
                else:
                    self.trail_height = 0
                    self.completed = True

        # --- Opponent logic ---
        if self.owner == "opponent":
            progress = (song_time - (self.spawn_time - SPAWN_AHEAD_TIME)) / SPAWN_AHEAD_TIME
            self.y = self.start_y + (self.target_y - self.start_y) * min(progress, 1.0)

            if not self.head_hit and self.y >= TARGET_Y:
                self.y = TARGET_Y
                self.head_hit = True
                active_opponent_char.play(self.direction)

            if self.head_hit and self.trail_height > 0:
                self.trail_height -= scroll_speed * dt
                if self.trail_height <= 0:
                    self.trail_height = 0
                    self.completed = True

            if not self.hit and not getattr(self, "animation_played", False):
                if (not preferences["upscroll"] and self.y >= TARGET_Y) or (preferences["upscroll"] and self.y <= TARGET_Y):
                    active_opponent_char.play(self.direction)
                    self.animation_played = True

    def draw(self):
        # draw trail
        if self.trail_height > 0:
            if preferences["upscroll"]:
                tail_rect = pygame.Rect(
                    self.x - NOTE_SIZE[0] // 6,
                    self.y,  # top of trail is at head
                    NOTE_SIZE[0] // 3,
                    self.trail_height
                )
            else:
                tail_rect = pygame.Rect(
                    self.x - NOTE_SIZE[0] // 6,
                    self.y - self.trail_height,
                    NOTE_SIZE[0] // 3,
                    self.trail_height
                )
            pygame.draw.rect(screen, ARROW_COLORS[self.direction], tail_rect)

        # draw head
        if self.style == "pixel":
            img = pixel_note_images[self.owner]["instance"][self.direction]
        else:
            img = note_images[self.owner]["instance"][self.direction]
        screen.blit(img, img.get_rect(center=(self.x, self.y)))

    def check_hit(self, key_pressed_now, key_held, song_time):
        points = 0
        combo_hit = False
        time_diff = abs(song_time - self.spawn_time)
        if preferences["upscroll"]:
            in_hit_window = self.y <= TARGET_Y + MISS_WINDOW
        else:
            in_hit_window = self.y >= TARGET_Y - MISS_WINDOW
        # Head hit
        if not self.head_hit and key_pressed_now and time_diff <= MISS_WINDOW:
            self.head_hit = True
            combo_hit = True
            points += 300

        # Hold scoring
        if self.head_hit and key_held:
            hold_start = self.spawn_time
            hold_end = self.spawn_time + self.sustain_length
            if hold_start <= song_time <= hold_end:
                points += 1

        return points, combo_hit

class NoteSplash:
    def __init__(self, x, y, frames):
        self.x = x
        self.y = y
        self.frames = frames
        self.frame_index = 0
        self.finished = False
        self.frame_timer = 0


    def update(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= 30:
            self.frame_index += 1
            self.frame_timer = 0
            if self.frame_index >= len(self.frames):
                self.finished = True

    def draw(self, surface):
        if not self.finished:
            img = self.frames[self.frame_index]
            # shrink to 70% of original size
            scaled_img = pygame.transform.scale(img, (int(img.get_width() * 0.7), int(img.get_height() * 0.7)))
            surface.blit(scaled_img, (self.x - scaled_img.get_width() // 2, self.y - scaled_img.get_height() // 2))
# map classes
class week2Stage:
    def __init__(self, image_path, xml_path, x=0, y=0, scale=1.0):
        self.x = x
        self.y = y
        self.scale = scale

        # Load the full atlas image
        self.atlas = pygame.image.load(image_path).convert_alpha()

        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Get first frame (base background)
        first_frame = root.find('SubTexture')
        self.rect = pygame.Rect(
            int(first_frame.get('x', 0)),
            int(first_frame.get('y', 0)),
            int(first_frame.get('width', 0)),
            int(first_frame.get('height', 0))
        )

        # Crop the frame
        self.image = self.atlas.subsurface(self.rect)

        # Scale if needed
        if scale != 1.0:
            w = int(self.rect.width * scale)
            h = int(self.rect.height * scale)
            self.image = pygame.transform.scale(self.image, (w, h))

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))

# --- Helpers ---
def draw_static_arrows():
    keys = pygame.key.get_pressed()

    # Select source set based on style
    source = pixel_note_images if note_style == "pixel" else note_images

    for d in ARROWS:
        # Determine Y based on upscroll
        draw_y = TARGET_Y if not preferences["upscroll"] else 70  # top of screen

        # --- Player static arrows ---
        img_static = source["player"]["static"].get(d)
        if img_static:
            screen.blit(
                img_static,
                (arrow_positions_right[d] - img_static.get_width() // 2,
                 draw_y - img_static.get_height() // 2)
            )

        # --- Player pressed arrows ---
        if keys[player_keys[d]]:
            img_pressed = source["player"]["press"].get(d)
            if img_pressed:
                screen.blit(
                    img_pressed,
                    (arrow_positions_right[d] - img_pressed.get_width() // 2,
                     draw_y - img_pressed.get_height() // 2)
                )

        # --- Opponent static arrows ---
        img_ai = source["opponent"]["static"].get(d)
        if img_ai:
            screen.blit(
                img_ai,
                (arrow_positions_left[d] - img_ai.get_width() // 2,
                 draw_y - img_ai.get_height() // 2)
            )

# --- Beatmap loading ---
def load_beatmap(song_name):
    import gzip, zipfile
    from io import BytesIO

    song_folder = os.path.join("songs", song_name)
    possible_files = [
        os.path.join(song_folder, f"{song_name}-chart.json"),
        os.path.join(song_folder, "chart.json"),
        os.path.join(song_folder, f"{song_name}.json"),
        os.path.join(song_folder, f"{song_name}.fnfc")
    ]
    chart_path = next((f for f in possible_files if os.path.exists(f)), None)
    if not chart_path:
        raise FileNotFoundError(f"No chart for {song_name}")

    with open(chart_path, "rb") as file:
        data = file.read()

    if data[:2] == b'\x1f\x8b':  # gzip
        chart = json.loads(gzip.decompress(data).decode("utf-8"))
    elif data[:2] == b'PK':  # zip
        with zipfile.ZipFile(BytesIO(data)) as z:
            json_file = next(n for n in z.namelist() if n.endswith(".json"))
            chart = json.loads(z.read(json_file).decode("utf-8"))
    else:
        chart = json.loads(data.decode("utf-8", errors="ignore"))

    # --- Extract camera events ---
    events = chart.get("events", [])
    camera_events = []
    for e in events:
        if e.get("e") == "FocusCamera":
            v = e.get("v", 0)
            # If v is a dict with "char", use it; else assume v itself is the char index
            char_index = v.get("char") if isinstance(v, dict) else v
            camera_events.append({"time": e["t"], "char": char_index})
    chart["camera_events"] = camera_events

    return chart

# --- States ---
STATE_MENU, STATE_SONG_SELECT, STATE_PLAYING, STATE_RESULTS, STATE_OPTIONS, STATE_OPTIONSCONTROLS, STATE_PAUSED = "menu","song_select","playing","results","options", "controls", "paused"
state=STATE_MENU
selected_menu,menu_items,selected_song,songs=0,["Start Game","Options","Quit"],0,["bopeebo","fresh","dadbattle", "spookeez", "south", "ugh","guns","stress"]
options_tabs = ["Preferences", "Controls"]
highlighted_tab = 0       # which tab the cursor is on
opened_tab = None         # which tab is currently opened (None if just in tab selection)
preferences = {
    "ghost_tapping": False,
    "upscroll": False
}
results={}
notes=[]
score=combo=perfects=goods=misses=0
start_time=0
song_started=False

TARGET_Y = 70 if preferences["upscroll"] else HEIGHT - 70
if not preferences["upscroll"]:
    HEALTH_BAR_Y = 20
else:
    HEALTH_BAR_Y = HEIGHT - 70

# --- Player keybinds ---
player_keys={"left":pygame.K_LEFT,"down":pygame.K_DOWN,"up":pygame.K_UP,"right":pygame.K_RIGHT}
option_selected=0
waiting_for_key=False
directions=["left","down","up","right"]
KEYBINDS_FILE= "../keybinds.json"
if os.path.exists(KEYBINDS_FILE):
    try:
        with open(KEYBINDS_FILE,"r") as f:
            saved_keys=json.load(f)
            for k,v in saved_keys.items():
                player_keys[k]=getattr(pygame,v,player_keys[k])
    except: pass

# --- Reset game ---
def reset_game(song_name,difficulty="easy"):
    global notes, score, combo, perfects, goods, misses, start_time, song_started, health, countdown_seconds, countdown_start, camera_events_index, camera_events, camera_x_target, camera_focus_char, miss_sound, active_opponent_char, active_icon, game_state, death_triggered, bf_idle_timer, bf_char, gf_char, note_style
    chart_data=load_beatmap(song_name)
    # Choose active opponent character
    if songs[selected_song] in TANKMAN_SONGS:
        active_opponent_char = tankman_char
        active_icon = tankman_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"
    elif songs[selected_song] == "thorns":
        active_opponent_char = spirit_char
        active_icon = spirit_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="pixel", scale=4.1)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="pixel", scale=4)
        note_style = "pixel"
    elif songs[selected_song] in SENPAI_SONGS:
        senpai_char = Senpai(image_path="characters/senpai/senpai.png", xml_path="characters/senpai/senpai.xml", x=WIDTH // 2 - 150, y=HEIGHT - 275, scale=4, song_name=songs[selected_song])  # <- This is the key
        active_opponent_char = senpai_char
        active_icon = senpai_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="pixel", scale=4.1)
        gf_char = Girlfriend(x=gf_char.rect.centerx + 25, y=gf_char.rect.centery + 50, style="pixel", scale=4)
        note_style = "pixel"
    elif songs[selected_song] in PARENTS_SONGS:
        active_opponent_char = parents_char
        active_icon = parents_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"
    elif songs[selected_song] in MOM_SONGS:
        active_opponent_char = mom_char
        active_icon = mom_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"
    elif songs[selected_song] in PICO_SONGS:
        active_opponent_char = pico_char
        active_icon = pico_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"
    elif songs[selected_song] in SPOOKY_SONGS:
        active_opponent_char = spooky_char
        active_icon = spooky_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"
    else:
        active_opponent_char = dad_char
        active_icon = dad_icon
        bf_char = Boyfriend(x=bf_char.rect.centerx, y=bf_char.rect.centery, style="normal", scale=0.8)
        gf_char = Girlfriend(x=gf_char.rect.centerx, y=gf_char.rect.centery, style="normal", scale=0.7)
        note_style = "normal"

    if preferences["upscroll"]:
        for note in notes:
            note.start_y = HEIGHT + NOTE_SIZE[1]  # start offscreen at bottom
            note.target_y = TARGET_Y  # static arrows at top
    else:
        for note in notes:
            note.start_y = -NOTE_SIZE[1]  # start offscreen at top
            note.target_y = TARGET_Y  # normal downscroll
    notes=[]
    if "notes" in chart_data and difficulty in chart_data["notes"]:
        for n in chart_data["notes"][difficulty]:
            t=n.get("t",0); d_val=n.get("d",0); sustain=n.get("l",0)
            if d_val in d_map:
                dirn,owner=d_map[d_val]
                if sustain>0: notes.append(HoldNote(dirn,t,owner,sustain, style=note_style))
                else: notes.append(Note(dirn,t,owner, style=note_style))
    music_path=f"assets/songs/{song_name}/{song_name}.mp3"
    if not os.path.exists(music_path): raise FileNotFoundError(f"Missing audio: {music_path}")
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.load(music_path)
    miss_sound.set_volume(0.2)
    score=combo=perfects=goods=misses=0
    health = 0.5
    countdown_seconds = 3  # how many seconds the countdown lasts
    countdown_start = None  # will store the pygame.time.get_ticks() when countdown begins
    camera_x_target = 0
    camera_events_index = 0
    camera_events = chart_data.get("camera_events", [])
    camera_focus_char = 1  # default camera focus
    start_time=pygame.time.get_ticks()
    song_started=False
    bf_char.rect.x = WIDTH // 2 + 280
    bf_char.rect.y = HEIGHT - 300  # normal Y position

    global pause_accumulated
    pause_accumulated = 0

    # After resetting the game or starting the countdown
    bf_char.play("idle")  # Reset BF to normal idle frame
    bf_idle_timer = 0  # reset idle timer
    death_triggered = False  # make sure the death sequence can trigger next time
    game_state = "alive"
    bf_char.dead = False

    if preferences["upscroll"]:
        for note in notes:
            note.start_y = HEIGHT + NOTE_SIZE[1]  # start offscreen at bottom
            note.target_y = 70  # target near top of screen
    else:
        for note in notes:
            note.start_y = -NOTE_SIZE[1]  # start offscreen at top
            note.target_y = TARGET_Y  # normal target

# --- Direction mapping ---
d_map={0:("left","player"),1:("down","player"),2:("up","player"),3:("right","player"),
       4:("left","opponent"),5:("down","opponent"),6:("up","opponent"),7:("right","opponent")}

# --- States ---
STATE_MENU, STATE_SONG_SELECT, STATE_PLAYING, STATE_RESULTS, STATE_OPTIONS = "menu","song_select","playing","results","options"
state = STATE_MENU
selected_menu, menu_items, selected_song, songs = 0, ["Start Game","Options","Quit"], 0, ["bopeebo", "fresh", "dadbattle", "spookeez", "south", "pico", "philly-nice", "blammed", "satin-panties", "high", "milf", "cocoa", "eggnog", "senpai", "roses", "thorns", "ugh", "guns", "stress"]
DAD_SONGS = {"bopeebo", "fresh", "dadbattle"}
SPOOKY_SONGS = {"spookeez", "south"}
PICO_SONGS = {"pico", "philly-nice", "blammed"}
MOM_SONGS = {"satin-panties", "high", "milf"}
PARENTS_SONGS = {"cocoa", "eggnog"}
SENPAI_SONGS = {"senpai", "roses"}
TANKMAN_SONGS = {"ugh", "guns", "stress"}
results = {}
notes = []
score = combo = perfects = goods = misses = 0
start_time = 0
song_started = False
# --- Countdown before song starts ---
countdown_seconds = 3  # how many seconds the countdown lasts
countdown_start = None  # will store the pygame.time.get_ticks() when countdown begins

def draw_background_layers(screen, camera_x, camera_y, selected_song):
    bg_layers = []

    if selected_song in (16, 17, 18):
        bg_layers = [(w7bg_image, 0.3)]
    elif selected_song == 15:
        bg_layers = [(w6bg2_image, 0.4)]
    elif selected_song in (13, 14):
        bg_layers = [(w6bg_image, 0.4)]
    elif selected_song in (11, 12):
        bg_layers = [(w5bg_image, 0.5)]
    elif selected_song in (8, 9, 10):
        bg_layers = [(w4bg_image, 0.6)]
    elif selected_song in (5, 6, 7):
        bg_layers = [(w3bg_image, 0.5)]
    elif selected_song in (3, 4):
        halloween_stage.draw(screen)
        return
    else:
        bg_layers = [(w1bg_image, 0.4)]

    # Draw each layer with parallax
    for img, parallax in bg_layers:
        offset_x = -camera_x * parallax
        offset_y = -camera_y * parallax

        # Repeat image horizontally to avoid empty edges
        width = img.get_width()
        x_pos = offset_x % width - width
        while x_pos < WIDTH:
            screen.blit(img, (x_pos, offset_y))
            x_pos += width


# --- Player keybinds ---
player_keys = {"left":pygame.K_LEFT,"down":pygame.K_DOWN,"up":pygame.K_UP,"right":pygame.K_RIGHT}
option_selected = 0
waiting_for_key = False
directions = ["left","down","up","right"]
KEYBINDS_FILE = "../keybinds.json"
if os.path.exists(KEYBINDS_FILE):
    try:
        with open(KEYBINDS_FILE,"r") as f:
            saved_keys = json.load(f)
            for k,v in saved_keys.items():
                player_keys[k] = getattr(pygame,v,player_keys[k])
    except: pass

# --- Main loop ---
running = True
bf_char = Boyfriend(
    x=WIDTH//2 + 150,
    y=HEIGHT - 150,
    style="normal",
    scale=0.8)

gf_char = Girlfriend(
    x=WIDTH//2 + 100,
    y=HEIGHT - 300,
    style="normal",
    scale=0.8)

dad_char = DaddyDearest(
    "characters/daddydearest/daddyDearest.png",
    "assets/characters/daddydearest/daddyDearest.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 300, scale=0.7,)

spooky_char = Spooky(
    "characters/spooky/SpookyKids.png",
    "assets/characters/spooky/SpookyKids.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 250, scale=0.7,)

pico_char = Pico(
    "characters/pico/Pico_Basic.png",
    "assets/characters/pico/Pico_Basic.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 150, scale=0.7)

mom_char = Mom(
    "characters/mom/Mom.png",
    "assets/characters/mom/Mom.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 300, scale=0.7,)

parents_char = Parents(
    "characters/parents/parents.png",
    "assets/characters/parents/parents.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 300, scale=0.7,)

senpai_char = Senpai(
    "characters/senpai/senpai.png",
    "assets/characters/senpai/senpai.xml",
    x=WIDTH//2 - 100, y=HEIGHT - 300, scale=4,)

spirit_char = Spirit(
    image_path="characters/spirit/spirit.png",
    txt_path="characters/spirit/spirit.txt",
    x=WIDTH//2 - 150, y=HEIGHT - 400, scale=4)

tankman_char = Tankman(
    "characters/tankman/tankmanCaptain.png",
    "assets/characters/tankman/tankmanCaptain.xml",
    x=WIDTH//2 - 150, y=HEIGHT - 250, scale=0.7,)

halloween_stage = week2Stage("images/week2/halloween_bg.png",
                             "assets/images/week2/halloween_bg.xml",
                             x=-150, y=0, scale=0.65)

bf_hit_animation_timer = 0
dad_hit_animation_timer = 0
spooky_hit_animation_timer = 0
pico_hit_animation_timer = 0
mom_hit_animation_timer = 0
parents_hit_animation_timer = 0
senpai_hit_animation_timer = 0
spirit_hit_animation_timer = 0
tankman_hit_animation_timer = 0

def draw_with_camera(surface, obj, obj_rect, parallax=1.0):
    """
    Draw an object with camera adjustment.
    parallax <1 moves slower (background), parallax =1 moves normally.
    """
    draw_x = obj_rect.x - camera_x * parallax
    draw_y = obj_rect.y  # fixed vertical position
    surface.blit(obj, (draw_x, draw_y))

if preferences["upscroll"]:
    for note in notes:
        note.start_y = HEIGHT + NOTE_SIZE[1]
        note.target_y = 70  # move static arrows to top

def trigger_death():
    global game_state, music_path
    game_state = "death"

    # Stop all sound & music
    pygame.mixer.music.stop()
    music_path= f"sounds/death.mp3"
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play()

    # Play death start animation
    bf_char.play("idle2")

    # Reposition BF so he's visible (raise him up a bit)
    bf_char.rect.y = HEIGHT - 500
    bf_char.rect.x = WIDTH - 500

while running:
    dt = clock.tick(60)
    #screen.fill(BLACK)
    keys_down_events = []

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            sys.exit()
        if event.type == pygame.KEYDOWN:
            keys_down_events.append(event.key)
        if event.type == pygame.KEYDOWN:
            # --- Menu navigation ---
            if state == STATE_MENU:
                if event.key == pygame.K_UP: selected_menu = (selected_menu - 1) % len(menu_items)
                if event.key == pygame.K_DOWN: selected_menu = (selected_menu + 1) % len(menu_items)
                if event.key == pygame.K_RETURN:
                    if menu_items[selected_menu] == "Start Game": state = STATE_SONG_SELECT
                    elif menu_items[selected_menu] == "Options": state = STATE_OPTIONS
                    elif menu_items[selected_menu] == "Quit": pygame.quit(); sys.exit()
            elif state == STATE_SONG_SELECT:
                if event.key == pygame.K_UP: selected_song = (selected_song - 1) % len(songs)
                if event.key == pygame.K_DOWN: selected_song = (selected_song + 1) % len(songs)
                if event.key == pygame.K_LEFT:
                    selected_difficulty_index = (selected_difficulty_index - 1) % len(difficulties)
                    selected_difficulty = difficulties[selected_difficulty_index]
                if event.key == pygame.K_RIGHT:
                    selected_difficulty_index = (selected_difficulty_index + 1) % len(difficulties)
                    selected_difficulty = difficulties[selected_difficulty_index]
                if event.key == pygame.K_RETURN:
                    reset_game(songs[selected_song], selected_difficulty)
                    state = STATE_PLAYING
                if event.key == pygame.K_ESCAPE:
                    state = STATE_MENU
            elif state == STATE_PLAYING:
                if event.key == pygame.K_ESCAPE:
                    if game_state == "alive":
                        pause_snapshot = screen.copy()
                        state = STATE_PAUSED
                        # Fade out main song
                        pygame.mixer.music.fadeout(500)  # 0.5 second fade
                        pause_sound = pygame.mixer.Sound("sounds/pause.mp3")
                        pause_sound.set_volume(0.2)
                        # Start pause music, looping
                        pause_channel = pause_sound.play(loops=-1, fade_ms=500)
                        pause_selected = 0
                        pygame.mixer.music.pause()
                        pause_start_time = pygame.time.get_ticks()
                        for note in notes:
                            note.stored_y = note.y  # freeze their visual position
                    elif game_state == "death":
                        state = STATE_MENU
                        pygame.mixer.music.stop()
                if game_state == "death":
                    if event.key == pygame.K_RETURN:
                        reset_game(songs[selected_song], selected_difficulty)
                        state = STATE_PLAYING
                        game_state = "alive"
                if event.key in player_keys and game_state == "alive":
                    direction = player_keys[event.key]
                    bf_char.play(direction)
                    bf_hit_animation_timer = pygame.time.get_ticks()
            elif state == STATE_RESULTS:
                if event.key == pygame.K_RETURN:
                    state = STATE_MENU
            elif state == STATE_PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        pause_selected = (pause_selected - 1) % len(pause_items)
                    elif event.key == pygame.K_DOWN:
                        pause_selected = (pause_selected + 1) % len(pause_items)
                    elif event.key == pygame.K_RETURN:
                        if pause_selected == 0:  # Resume
                            state = STATE_PLAYING
                            pause_channel.stop()
                            for note in notes:
                                note.stored_y = note.y
                            # Resume music at the correct position
                            pygame.mixer.music.play(
                                start=song_time / 1000.0)  # song_time is in ms, play expects seconds
                            pause_accumulated += pygame.time.get_ticks() - pause_start_time
                            for note in notes:
                                note.y = note.stored_y  # restore frozen positions
                            pause_start_time = None

                        elif pause_selected == 1:  # Restart
                            reset_game(songs[selected_song], selected_difficulty)
                            pause_channel.stop()
                            state = STATE_PLAYING
                        elif pause_selected == 2:  # Quit
                            pause_channel.stop()
                            pygame.mixer.music.stop()
                            state = STATE_MENU
                    elif event.key == pygame.K_ESCAPE:
                        state = STATE_PLAYING
                        pause_channel.stop()
                        for note in notes:
                            note.stored_y = note.y
                        # Resume music at the correct position
                        pygame.mixer.music.play(
                            start=song_time / 1000.0)  # song_time is in ms, play expects seconds
                        pause_accumulated += pygame.time.get_ticks() - pause_start_time
                        for note in notes:
                            note.y = note.stored_y  # restore frozen positions
                        pause_start_time = None

            elif state == STATE_OPTIONS:
                if waiting_for_key:
                    player_keys[directions[option_selected]] = event.key
                    waiting_for_key = False
                    try:
                        save_dict = {k: pygame.key.name(v) for k, v in player_keys.items()}
                        with open(KEYBINDS_FILE, "w") as f:
                            json.dump(save_dict, f)
                    except:
                        pass
                else:
                    if opened_tab is None:
                        # Navigate tabs
                        if event.key == pygame.K_UP:
                            highlighted_tab = (highlighted_tab - 1) % len(options_tabs)
                        elif event.key == pygame.K_DOWN:
                            highlighted_tab = (highlighted_tab + 1) % len(options_tabs)
                        elif event.key == pygame.K_RETURN:
                            opened_tab = options_tabs[highlighted_tab]
                        elif event.key == pygame.K_ESCAPE:
                            state = STATE_MENU
                    else:
                        # Inside a tab
                        if opened_tab == "Controls":
                            if event.key == pygame.K_UP:
                                option_selected = (option_selected - 1) % 4
                            elif event.key == pygame.K_DOWN:
                                option_selected = (option_selected + 1) % 4
                            elif event.key == pygame.K_RETURN:
                                waiting_for_key = True
                        elif opened_tab == "Preferences":
                            if event.key == pygame.K_UP:
                                option_selected = (option_selected - 1) % len(preferences)
                            elif event.key == pygame.K_DOWN:
                                option_selected = (option_selected + 1) % len(preferences)
                            elif event.key == pygame.K_RETURN:
                                # Toggle the selected preference
                                key = list(preferences.keys())[option_selected]
                                preferences[key] = not preferences[key]

                        # Preferences can have future navigation
                        if event.key == pygame.K_ESCAPE:
                            opened_tab = None

            # --- KEYUP handler (place this inside the event loop, not nested under KEYDOWN) ---
        elif event.type == pygame.KEYUP and state == STATE_PLAYING:
            if event.key in player_keys.values():
                pressed = pygame.key.get_pressed()
                any_held = any(pressed[k] for k in player_keys.values())
                if not any_held:
                    bf_idle_timer = pygame.time.get_ticks() + IDLE_DELAY

    if state == STATE_PLAYING:
        if 'pause_snapshot' in globals():
            del pause_snapshot

        if game_state == "death":
            screen.fill(BLACK)
            if not death_triggered:
                trigger_death()
                death_triggered = True  # ensures it runs only once

            # Keep him visible (raised)
            bf_char.rect.y = HEIGHT - 500
            bf_char.rect.x = WIDTH - 500
            bf_char.update(dt)
            bf_char.draw(screen)

        elif game_state == "alive":
            draw_background_layers(screen, camera_x, camera_y, selected_song)
            # --- Start music ---
            if not song_started:
                if countdown_start is None:
                    countdown_start = pygame.time.get_ticks()

                # Update and draw characters
                gf_char.update(dt)
                bf_char.update(dt)
                active_opponent_char.update(dt)
                draw_with_camera(screen, gf_char.image, gf_char.rect)
                draw_with_camera(screen, active_opponent_char.image, active_opponent_char.rect)
                draw_with_camera(screen, bf_char.image, bf_char.rect)
                draw_static_arrows()

                # --- Countdown logic ---
                elapsed = pygame.time.get_ticks() - countdown_start
                remaining = countdown_seconds - elapsed // 1000

                # Pretend the song started countdown_seconds * 1000 ms ago
                # e.g. for 3-second countdown, song_time starts at -3000
                fake_song_time = elapsed - countdown_seconds * 1000

                # Update and draw notes with fake negative time
                for note in notes:
                    note.update(fake_song_time)
                    note.draw()

                # Draw countdown text
                if remaining > 0:
                    countdown_text = bigfont.render(str(remaining), True, WHITE)
                else:
                    countdown_text = bigfont.render("Go!", True, WHITE)
                screen.blit(countdown_text, (
                    WIDTH // 2 - countdown_text.get_width() // 2,
                    HEIGHT // 2 - countdown_text.get_height() // 2
                ))

                # --- Start the song when countdown ends ---
                if remaining <= 0 and not song_started:
                    pygame.mixer.music.play()
                    song_started = True
                    start_time = pygame.time.get_ticks()
                    bf_hit_animation_timer = start_time
                    dad_hit_animation_timer = start_time

                pygame.display.flip()
                continue

            song_time = pygame.time.get_ticks() - start_time - pause_accumulated
            keys = pygame.key.get_pressed()

            # --- CAMERA FOCUS HANDLING ---
            if camera_events_index < len(camera_events):
                event = camera_events[camera_events_index]
                if song_time >= event["time"]:
                    char_focus = event["char"]
                    camera_events_index += 1
            else:
                char_focus = 1  # default to opponent

            # Choose camera anchor based on who's focused
            if char_focus == 1:
                focus_x, focus_y = CAMERA_POSITIONS.get("dad", (0, 200))
            else:
                focus_x, focus_y = CAMERA_POSITIONS.get("bf", (0, 200))

            # Smooth LERP movement
            camera_x += (focus_x - camera_x) * 0.1
            camera_y += (focus_y - camera_y) * 0.1

            # --- Helper functions ---
            def play_bf_animation(note_dir):
                bf_char.play(f"{note_dir.lower()}")

            def play_opponent_animation(note_dir):
                active_opponent_char.play(note_dir.lower() if note_dir.lower() in active_opponent_char.animations else "idle")

            # --- Update notes loop ---
            new_notes = []
            player_notes_by_dir = {d: [] for d in ARROWS}
            for note in notes:
                if note.owner == "player":
                    player_notes_by_dir[note.direction].append(note)

            closest_notes = {}
            for dir_name, note_list in player_notes_by_dir.items():
                if note_list:
                    note_list.sort(key=lambda n: abs(n.y - TARGET_Y))
                    closest_notes[dir_name] = note_list[0]

            for note in notes:
                key_pressed_now = player_keys[note.direction] in keys_down_events if note.owner == "player" else False
                key_held = keys[player_keys[note.direction]] if note.owner == "player" else False

                color_map = {
                    "up": "green",
                    "down": "blue",
                    "left": "purple",
                    "right": "red"
                }

                # --- HOLD NOTES ---
                if isinstance(note, HoldNote):
                    note.update(song_time, key_held, dt)
                    gained, combo_hit = note.check_hit(key_pressed_now, key_held, song_time)
                    score += gained

                    if combo_hit:
                        combo += 1
                        perfects += 1
                        update_health("Perfect")
                        if key_pressed_now or key_held:
                            play_bf_animation(note.direction)
                            bf_hit_animation_timer = pygame.time.get_ticks()
                            bf_idle_timer = 0

                    if note.head_hit and key_held:
                        play_bf_animation(note.direction)

                    if not note.completed:
                        if (not preferences["upscroll"] and note.y > HEIGHT + NOTE_SIZE[1]) or \
                                (preferences["upscroll"] and note.y < -NOTE_SIZE[1]):
                            if not note.head_hit:  # only if never started holding
                                misses += 1
                                score -= 100
                                combo = 0
                                miss_sound.play()
                                note.head_hit = True
                                update_health("Miss")
                                bf_char.play_note(note.direction, hit=False)
                                bf_idle_timer = pygame.time.get_ticks() + IDLE_DELAY

                    if not note.completed:
                        new_notes.append(note)

                # --- NORMAL NOTES ---
                else:
                    pre_countdown_time = max(0, countdown_seconds * 1000 - (pygame.time.get_ticks() - countdown_start))
                    note_time_for_update = song_time - pre_countdown_time
                    note.update(max(0, note_time_for_update))

                    if note.owner == "player":
                        if closest_notes.get(note.direction) is note:
                            gained, hit_type = note.check_hit(key_pressed_now, song_time)
                            score += gained
                            if hit_type == "Perfect":
                                combo += 1;
                                perfects += 1
                            elif hit_type == "Good":
                                combo += 1;
                                goods += 1
                            if hit_type:
                                splash = NoteSplash(
                                    x=note.x + NOTE_SIZE[0] // 2 - 20,  # center on note
                                    y=HEIGHT - 70,
                                    frames=note_splashes[color_map[note.direction]]  # the frames for that color
                                )
                                active_splashes.append(splash)
                                play_bf_animation(note.direction)
                                bf_hit_animation_timer = pygame.time.get_ticks()
                                bf_idle_timer = 0
                                update_health(hit_type)

                        # Missed normal note
                        if note.entered_hit_zone:
                            if (not preferences["upscroll"] and note.y > HEIGHT + NOTE_SIZE[1]) or \
                                    (preferences["upscroll"] and note.y < -NOTE_SIZE[1]):
                                misses += 1
                                score -= 100
                                combo = 0
                                note.hit = True
                                miss_sound.play()
                                update_health("Miss")
                                bf_char.play_note(note.direction, hit=False)
                                bf_idle_timer = pygame.time.get_ticks() + IDLE_DELAY

                        if not note.hit:
                            new_notes.append(note)

                    else:  # Opponent note
                        if not note.hit and note.y >= TARGET_Y:
                            note.hit = True
                            active_opponent_char.play(note.direction)
                            dad_hit_animation_timer = pygame.time.get_ticks()
                        if not note.hit:
                            new_notes.append(note)

            # --- GHOST TAPPING HANDLING ---
            for direction, key in player_keys.items():
                if key in keys_down_events:
                    note_in_range = any(
                        note.owner == "player" and note.direction == direction and abs(note.y - TARGET_Y) <= MISS_WINDOW
                        for note in notes
                    )

                    if not preferences.get("ghost_tapping", False):
                        # Ghost tapping OFF → penalize
                        if not note_in_range:
                            score -= 10
                            miss_sound.play()
                            update_health("Miss")
                            bf_char.play_note(note.direction, hit=False)
                            bf_idle_timer = pygame.time.get_ticks() + IDLE_DELAY
                    else:
                        # Ghost tapping ON → allow instant animation (no waiting)
                        if not note_in_range:
                            play_bf_animation(direction)
                            bf_idle_timer = pygame.time.get_ticks() + IDLE_DELAY

            notes = new_notes

            if bf_idle_timer > 0 and pygame.time.get_ticks() >= bf_idle_timer:
                bf_char.play("idle")
                bf_idle_timer = 0

            if not preferences["upscroll"]:
                active_hold_notes = [
                    n for n in notes
                    if n.owner == "opponent"
                       and isinstance(n, HoldNote)
                       and not n.completed
                       and HEIGHT - 120 <= n.y <= HEIGHT
                ]

                active_normal_notes = [
                    n for n in notes
                    if n.owner == "opponent"
                       and not isinstance(n, HoldNote)
                       and not n.hit
                       and HEIGHT - 120 <= n.y <= HEIGHT
                ]
            else:
                active_hold_notes = [
                    n for n in notes
                    if n.owner == "opponent"
                       and isinstance(n, HoldNote)
                       and not n.completed
                       and 120 <= n.y <= 0
                ]

                active_normal_notes = [
                    n for n in notes
                    if n.owner == "opponent"
                       and not isinstance(n, HoldNote)
                       and not n.hit
                       and 120 <= n.y <= 0
                ]

            OPPONENT_IDLE_TIMER = 400

            # Decide direction or idle
            if active_hold_notes:
                note_dir = active_hold_notes[0].direction
                last_opponent_anim_time = pygame.time.get_ticks()
            elif active_normal_notes:
                note_dir = active_normal_notes[0].direction
                last_opponent_anim_time = pygame.time.get_ticks()
            else:
                # Only go idle if grace period expired
                if pygame.time.get_ticks() - dad_hit_animation_timer > OPPONENT_IDLE_TIMER:
                    note_dir = "idle"
                else:
                    note_dir = active_opponent_char.current  # keep current anim

            # Only change animations when needed
            if note_dir != active_opponent_char.current:
                active_opponent_char.play(note_dir)

            # --- Draw ---
            gf_char.update(dt)
            bf_char.update(dt)
            active_opponent_char.update(dt)
            draw_with_camera(screen, gf_char.image, gf_char.rect)
            draw_with_camera(screen, active_opponent_char.image, active_opponent_char.rect)
            draw_with_camera(screen, bf_char.image, bf_char.rect)
            draw_static_arrows()
            for note in notes: note.draw()
            for splash in active_splashes[:]:
                splash.update(dt)
                if splash.finished:
                    active_splashes.remove(splash)
            # Draw splashes
            for splash in active_splashes:
                splash.draw(screen)
            draw_healthbar()
            score_text = font.render(f"Score: {score}", True, WHITE)
            combo_text = font.render(f"Combo: {combo}", True, WHITE)
            if not preferences["upscroll"]:
                screen.blit(score_text, (WIDTH / 2 - 50, HEIGHT / 7 - 40))
                screen.blit(combo_text, (WIDTH / 2 - 50, HEIGHT / 7 - 15))
            else:
                screen.blit(score_text, (WIDTH / 2 - 50, HEIGHT - 40))
                screen.blit(combo_text, (WIDTH / 2 - 50, HEIGHT - 15))

            # --- Song end check ---
            if not pygame.mixer.music.get_busy() and song_started:
                total = perfects + goods + misses
                accuracy = (perfects * 1 + goods * 0.7) / max(1, total)
                results = {"Score": score, "Perfect": perfects, "Good": goods, "Miss": misses,
                           "Accuracy": round(accuracy * 100, 1)}
                state = STATE_RESULTS

    elif state==STATE_MENU:
        screen.blit(menuBg_image,(0,0))
        title = bigfont.render("FNF",True,BLACK)
        screen.blit(title,(WIDTH//2-title.get_width()//2,100))
        for i,item in enumerate(menu_items):
            color=RED if i==selected_menu else BLACK
            text=font.render(item,True,color)
            screen.blit(text,(WIDTH//2-text.get_width()//2,300+i*50))

    elif state == STATE_SONG_SELECT:
        # --- SONG SELECT DRAWING ---
        screen.blit(menuBg_image, (0, 0))
        title = bigfont.render("Select Song", True, BLACK)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        # smooth scroll animation offset
        scroll_speed = 0.15  # lower = smoother/slower transition
        if not hasattr(pygame, "_scroll_offset"):
            pygame._scroll_offset = float(selected_song)
        pygame._scroll_offset += (selected_song - pygame._scroll_offset) * scroll_speed

        # compute center index (round so it snaps to nearest while animating)
        center_index = int(round(pygame._scroll_offset))

        # range of visible songs: 1 above, 3 below of the center_index
        start = max(0, center_index - 1)
        end = min(len(songs), center_index + 4)  # +4 so we get 1 above + 3 below (end is exclusive)
        visible_range = range(start, end)

        opponent_icons = {
            "bopeebo": dad_icon,
            "fresh": dad_icon,
            "dadbattle": dad_icon,
            "spookeez": spooky_icon,
            "south": spooky_icon,
            "pico": pico_icon,
            "philly-nice": pico_icon,
            "blammed": pico_icon,
            "satin-panties": mom_icon,
            "high": mom_icon,
            "milf": mom_icon,
            "cocoa": parents_icon,
            "eggnog": parents_icon,
            "senpai": senpai_icon,
            "roses": senpai_icon,
            "thorns": spirit_icon,
            "ugh": tankman_icon,
            "guns": tankman_icon,
            "stress": tankman_icon,
        }

        for i in visible_range:
            song = songs[i]

            # smooth Y position based on offset (use _scroll_offset float for smooth movement)
            y = 300 + (i - pygame._scroll_offset) * 70

            # Text color (red if selected)
            color = RED if i == selected_song else BLACK

            # variable width based on text length (render with chosen color)
            text = font.render(song, True, color)
            text_width = text.get_width()
            rect_width = text_width + 40  # padding
            rect_x = WIDTH // 2 - rect_width // 2
            rect_y = int(y)
            rect = pygame.Rect(rect_x, rect_y, rect_width, 40)

            # Draw background rect (light gray)
            pygame.draw.rect(screen, (200, 200, 200), rect, border_radius=6)

            # Outline if selected
            if i == selected_song:
                pygame.draw.rect(screen, (0, 120, 255), rect, 3, border_radius=6)

            # Draw icon
            icon = opponent_icons.get(song)
            if icon:
                screen.blit(icon, (rect.left - icon.get_width() - 10, rect_y + (rect.height - icon.get_height()) // 2))

            # Draw text
            screen.blit(text, (rect.x + 10, rect.y + (rect.height - text.get_height()) // 2))

        # Difficulty display
        diff_text = font.render(f"Difficulty: {selected_difficulty.title()}", True, RED)
        screen.blit(diff_text, (WIDTH // 4 - diff_text.get_width() // 2 - 20, HEIGHT // 4 + 30))

    elif state==STATE_RESULTS:
        screen.blit(menuBg_image,(0,0))
        title=bigfont.render("Results",True,BLACK)
        screen.blit(title,(WIDTH//2-title.get_width()//2,100))
        y=250
        for k,v in results.items():
            text=font.render(f"{k}: {v}",True,BLACK)
            screen.blit(text,(WIDTH//2-text.get_width()//2,y))
            y+=40
        text=font.render("Press Enter to return to Menu",True,GRAY)
        screen.blit(text,(WIDTH//2-text.get_width()//2,y+50))

    elif state == STATE_OPTIONS:
        screen.blit(menuBg_image, (0, 0))
        title = bigfont.render("Options", True, BLACK)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        if opened_tab is None:
            # Show tab list
            tab_y = 200
            for i, tab in enumerate(options_tabs):
                color = RED if i == highlighted_tab else BLACK
                text = font.render(tab, True, color)
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, tab_y + i * 40))
        else:
            # Tabs are hidden, center the opened tab content
            if opened_tab == "Controls":
                y = HEIGHT // 2 - 100  # center roughly vertically
                for i, dir_name in enumerate(directions):
                    color = RED if i == option_selected else BLACK
                    key_name = pygame.key.name(player_keys[dir_name])
                    text = font.render(f"{dir_name.capitalize()}: {key_name}", True, color)
                    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y + i * 50))
                prompt = font.render(
                    "Press a key to assign..." if waiting_for_key else "Use ↑↓ to select, Enter to rebind, Esc to return",
                    True, RED if waiting_for_key else GRAY
                )
                screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, y + 220))

            elif opened_tab == "Preferences":
                y = HEIGHT // 2 - 50
                for i, (pref_name, value) in enumerate(preferences.items()):
                    color = RED if i == option_selected else BLACK
                    display_name = pref_name.replace("_", " ").title()
                    status = "ON" if value else "OFF"
                    text = font.render(f"{display_name}: {status}", True, color)
                    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y + i * 50))
                prompt = font.render("Use ↑↓ to select, Enter to toggle, Esc to return", True, GRAY)
                screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, y + 120))

    elif state == STATE_PAUSED:
        # Draw the captured snapshot
        screen.blit(pause_snapshot, (0, 0))

        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # 50% opacity
        screen.blit(overlay, (0, 0))

        # Draw pause menu items
        pause_items = ["Resume", "Restart Song", "Quit to Menu"]
        for i, item in enumerate(pause_items):
            color = RED if i == pause_selected else WHITE
            text = font.render(item, True, color)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50 + i * 40))

    pygame.display.flip()