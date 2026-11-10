"""
Alien Colony Escape - Main Execution File
Fullscreen game: animated title (60 s), login, briefing, difficulty select,
animated gameplay with BFS / DBDFS / A* aliens, and animated end screens.
"""
import math
import random
import sys

import pygame

import hd
from storyline import (LORE_INTRO, DIFFICULTY_INTEL, GAME_TITLE_LINE_1, GAME_TITLE_LINE_2,GAME_TAGLINE, BOOT_LOG)
from ai_engine import search_bfs, search_dbdfs, search_astar
from auth_manager import AuthManager
from graphics_engine import GraphicsRenderer

# Logical resolution (scaled to fill any screen, keeps aspect ratio)
W, H = 1280, 720
FPS = 60
TITLE_FRAMES = 60 * 60          # title screen lasts one minute

# Palette
CLR_BG = (8, 12, 20)
CLR_PANEL = (18, 25, 42)
CLR_BORDER = (45, 65, 105)
CLR_TEXT = (240, 245, 255)
CLR_MUTED = (130, 145, 175)
CLR_CYAN = (0, 220, 255)
CLR_RED = (255, 45, 85)
CLR_GREEN = (40, 255, 130)
CLR_GOLD = (255, 215, 0)

# Station Map (1 = Wall, 0 = Hallway)
MAP_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,1],
    [1,0,1,1,1,0,1,0,1,1,1,1,1,0,0,1,0,1,0,1],
    [1,0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,0,1,0,1],
    [1,0,1,0,1,1,1,0,1,0,1,0,1,1,1,1,0,1,0,1],
    [1,0,0,0,1,0,0,0,0,0,1,0,0,0,0,1,0,0,0,1],
    [1,1,1,0,1,0,1,1,1,0,1,1,1,0,0,1,1,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,1],
    [1,0,1,1,1,1,1,0,1,1,1,0,1,1,1,1,1,1,0,1],
    [1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,1],
    [1,0,1,1,1,0,1,0,1,0,1,1,1,1,1,0,0,1,0,1],
    [1,0,0,0,1,0,1,0,0,0,1,0,0,0,1,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

ROWS = len(MAP_GRID)
COLS = len(MAP_GRID[0])
TILE_SIZE = 46
GRID_W, GRID_H = COLS * TILE_SIZE, ROWS * TILE_SIZE
GRID_ORIGIN_X = (W - GRID_W) // 2
GRID_ORIGIN_Y = 104

STATES = ("TITLE", "AUTH", "BRIEFING", "SELECT_DIFF", "GAMEPLAY", "END")


def wrap_text(font, text, max_w):
    """Word-wrap text into a list of lines ('' = blank line)."""
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        line = ""
        for word in para.split(" "):
            test = (line + " " + word).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


class AlienColonyEscapeApp:
    def __init__(self):
        pygame.init()
        self.fullscreen = True
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            self.fullscreen = False
            self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        pygame.display.set_caption("Alien Colony Escape")
        pygame.mouse.set_visible(True)
        hd.init(W, H, *pygame.display.get_surface().get_size())
        self.canvas = hd.Surface((W, H))
        self.fade_surf = hd.Surface((W, H))
        self.fade_surf.fill((0, 0, 0))
        self.clock = pygame.time.Clock()
        self.anim_tick = 0

        # Typography
        self.font_huge = hd.SysFont("Verdana", 128, bold=True)
        self.font_big = hd.SysFont("Verdana", 84, bold=True)
        self.font_title = hd.SysFont("Verdana", 28, bold=True)
        self.font_header = hd.SysFont("Verdana", 19, bold=True)
        self.font_body = hd.SysFont("Verdana", 15)
        self.font_mono = hd.SysFont("Courier New", 14, bold=True)
        self.font_count = hd.SysFont("Verdana", 150, bold=True)

        # Subsystems
        self.auth = AuthManager()
        self.renderer = GraphicsRenderer(W, H)

        # State
        self.current_state = "TITLE"
        self.state_time = 0
        self.fade_alpha = 255
        self.shake = 0
        self.snapshot = None
        self.active_user = None
        self.auth_mode = "LOGIN"
        self.txt_username = ""
        self.txt_password = ""
        self.selected_field = "USER"
        self.system_message = ""
        self.briefing_lines = wrap_text(self.font_body, LORE_INTRO["briefing"], 900)
        self.hover_card = -1

        # Gameplay
        self.difficulty = "Medium"
        self.map_surface = self.renderer.build_map_surface(MAP_GRID, TILE_SIZE, (GRID_W, GRID_H))
        self.ai_function = search_dbdfs
        self.airlock_pos = (11, 1)
        self.required_cores = 3
        self.reset_mission()

    # ---------------------------------------------------------------- helpers
    def set_state(self, state):
        self.current_state = state
        self.state_time = 0
        self.fade_alpha = 255

    def tile_center(self, r, c):
        return (GRID_ORIGIN_X + c * TILE_SIZE + TILE_SIZE // 2,
                GRID_ORIGIN_Y + r * TILE_SIZE + TILE_SIZE // 2)

    def text_center(self, font, text, color, y, surface=None):
        surf = font.render(text, True, color)
        (surface or self.canvas).blit(surf, (W // 2 - surf.get_width() // 2, y))
        return surf

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        try:
            if self.fullscreen:
                pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((W, H), pygame.RESIZABLE)
        except pygame.error:
            pass

    # ---- screen scaling (keeps mouse clicks accurate) ----
    def view_transform(self):
        surf = pygame.display.get_surface()
        sw, sh = surf.get_size()
        cw, ch = self.canvas.surf.get_size()
        k = min(sw / cw, sh / ch)
        tw, th = int(cw * k), int(ch * k)
        return surf, k, (sw - tw) // 2, (sh - th) // 2, tw, th

    def to_logical(self, pos):
        _, k, ox, oy, _, _ = self.view_transform()
        s = k * hd.K
        return (int((pos[0] - ox) / s), int((pos[1] - oy) / s))

    def mouse_pos(self):
        return self.to_logical(pygame.mouse.get_pos())

    def remap_event(self, e):
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and hasattr(e, "pos"):
            d = dict(e.dict)
            d["pos"] = self.to_logical(e.pos)
            return pygame.event.Event(e.type, d)
        return e

    # ---- back / home button ----
    BACK_RECT = pygame.Rect(24, 20, 130, 36)
    PREV_STATE = {"AUTH": "TITLE", "BRIEFING": "AUTH", "SELECT_DIFF": "BRIEFING",
                  "GAMEPLAY": "SELECT_DIFF", "END": "SELECT_DIFF"}

    def draw_back_button(self, label="<  BACK"):
        hov = self.BACK_RECT.collidepoint(self.mouse_pos())
        hd.draw.rect(self.canvas, (40, 60, 105) if hov else CLR_PANEL, self.BACK_RECT, border_radius=8)
        hd.draw.rect(self.canvas, CLR_CYAN if hov else CLR_BORDER, self.BACK_RECT, 2, border_radius=8)
        img = self.font_mono.render(label, True, CLR_TEXT)
        self.canvas.blit(img, img.get_rect(center=self.BACK_RECT.center))

    def back_pressed(self, events, allow_backspace=True):
        keys = (pygame.K_ESCAPE, pygame.K_BACKSPACE) if allow_backspace else (pygame.K_ESCAPE,)
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.BACK_RECT.collidepoint(e.pos):
                return True
            if e.type == pygame.KEYDOWN and e.key in keys:
                return True
        return False

    def go_back(self):
        # Go to the PREVIOUS page (gameplay -> difficulty -> briefing -> login -> title)
        target = self.PREV_STATE.get(self.current_state)
        if not target:
            return
        self.set_state(target)
        if target == "TITLE":
            self.state_time = 400          # title already revealed, skippable at once
        elif target == "AUTH":
            self.txt_password = ""
            self.system_message = ""
        elif target == "BRIEFING":
            self.state_time = 3000         # show the whole briefing straight away

    # ------------------------------------------------------------ mission setup
    def reset_mission(self):
        self.player_pos = [1, 1]
        self.player_vis = [1.0, 1.0]
        self.player_face = (1, 0)
        self.move_cooldown = 0
        self.alien_pos = [11, 18]
        self.alien_vis = [11.0, 18.0]
        self.alien_face = (-1, 0)
        self.alien_prev_pos = None
        self.alien_path = []
        self.alien_step_counter = 0
        self.energy_cores = [(1, 18), (5, 9), (9, 3)]
        self.collected_cores = 0
        self.float_texts = []
        self.banner = ("", 0)
        self.countdown = 190
        self.elapsed = 0
        self.game_outcome = ""

        if self.difficulty == "Simple":
            self.step_delay, self.ai_function = 22, search_bfs
        elif self.difficulty == "Medium":
            self.step_delay, self.ai_function = 15, search_dbdfs
        else:
            self.step_delay, self.ai_function = 10, search_astar

    def end_mission(self, outcome):
        self.game_outcome = outcome
        self.snapshot = self.canvas.copy()
        self.renderer.particles.clear()
        if outcome == "DEFEAT":
            self.shake = 28
            self.renderer.spawn_burst(self.tile_center(*self.player_pos), (255, 40, 80), n=60, speed=6, life=60, size=4)
        else:
            self.renderer.spawn_burst(self.tile_center(*self.player_pos), (40, 255, 130), n=60, speed=6, life=60, size=4)
        self.set_state("END")
        self.fade_alpha = 0

    # -------------------------------------------------------------- alien logic
    def update_alien_behavior(self):
        if self.countdown > 0:
            return
        if self.alien_pos == self.player_pos:
            self.end_mission("DEFEAT")
            return

        self.alien_step_counter += 1
        if self.alien_step_counter >= self.step_delay:
            self.alien_step_counter = 0
            path = self.ai_function(tuple(self.alien_pos), tuple(self.player_pos),
                                    MAP_GRID, ROWS, COLS, self.alien_prev_pos)
            self.alien_path = path
            if path:
                old = tuple(self.alien_pos)
                self.alien_prev_pos = old
                self.alien_pos = list(path[0])
                self.alien_face = (self.alien_pos[1] - old[1], self.alien_pos[0] - old[0])
                if self.alien_pos == self.player_pos:
                    self.end_mission("DEFEAT")

    # --------------------------------------------------------------- main loop
    def run(self):
        while True:
            self.frame()

    def frame(self, events=None):
        self.clock.tick(FPS)
        self.anim_tick += 1
        self.state_time += 1
        if events is None:
            events = pygame.event.get()
        events = [self.remap_event(e) for e in events]

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()

        st = self.current_state
        if st == "TITLE":
            self.handle_title_input(events)
            self.render_title_screen()
        elif st == "AUTH":
            self.handle_auth_input(events)
            self.render_auth_screen()
        elif st == "BRIEFING":
            self.handle_briefing_input(events)
            self.render_briefing_screen()
        elif st == "SELECT_DIFF":
            self.handle_selection_input(events)
            self.render_selection_screen()
        elif st == "GAMEPLAY":
            self.handle_gameplay_input(events)
            self.update_gameplay()
            self.update_alien_behavior()
            if self.current_state == "GAMEPLAY":
                self.render_gameplay_screen()
        if self.current_state == "END":
            self.handle_end_input(events)
            self.render_end_screen()


        # fade-in transition
        if self.fade_alpha > 0:
            self.fade_alpha = max(0, self.fade_alpha - 9)
            self.fade_surf.set_alpha(self.fade_alpha)
            self.canvas.blit(self.fade_surf, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            ox = random.randint(-self.shake, self.shake) // 2
            oy = random.randint(-self.shake, self.shake) // 2
            self.shake = int(self.shake * 0.92)
        surf, k, vx, vy, tw, th = self.view_transform()
        surf.fill((0, 0, 0))
        cs = self.canvas.surf
        px, py = vx + int(ox * hd.K), vy + int(oy * hd.K)
        if cs.get_size() == (tw, th):
            surf.blit(cs, (px, py))
        else:
            surf.blit(pygame.transform.smoothscale(cs, (tw, th)), (px, py))
        pygame.display.flip()

    # ============================================================ STATE: TITLE
    def handle_title_input(self, events):
        done = self.state_time >= TITLE_FRAMES
        for e in events:
            if self.state_time > 180 and (
                    (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE))
                    or e.type == pygame.MOUSEBUTTONDOWN):
                done = True
        if done:
            self.set_state("AUTH")

    def render_title_screen(self):
        s, t = self.canvas, self.state_time
        R = self.renderer
        R.draw_background(s, self.anim_tick, speed=1.0 + min(3.0, t / 200))

        # giant watching alien eye behind the title
        R.draw_big_eye(s, (W // 2, 330), t, alpha=int(min(90, t * 0.6)), scale=1.25)

        # ambient embers
        if t % 2 == 0:
            R.spawn_ember(random.uniform(0, W), H + 5)

        # horizontal glitch bars
        glitch = (t % 150) < 7 and t > 200
        R.draw_title_line(s, self.font_big, GAME_TITLE_LINE_1, 250, CLR_CYAN, t, 20, glitch)
        pulse = 0.5 + 0.5 * math.sin(t * 0.08)
        R.draw_title_line(s, self.font_huge, GAME_TITLE_LINE_2, 380, CLR_RED, t, 120, glitch, pulse)

        # laser sweep across the title once fully revealed
        if t > 230:
            sweep = (t * 9) % (W + 600) - 300
            beam = hd.Surface((120, 330), pygame.SRCALPHA)
            for i in range(120):
                hd.draw.line(beam, (255, 255, 255, int(55 * math.sin(math.pi * i / 120))), (i, 0), (i, 330))
            s.blit(beam, (sweep, 190))

        # tagline
        if t > 260:
            a = min(255, (t - 260) * 4)
            R.draw_glow_text(s, self.font_header, GAME_TAGLINE, CLR_MUTED, (W // 2, 500), glow_alpha=a * 0.4, alpha=a)

        # boot log typewriter (bottom-left)
        log_t = max(0, t - 60)
        total_chars = int(log_t * 0.9)
        y = H - 190
        cnt = 0
        shown_lines = []
        for line in BOOT_LOG:
            if cnt >= total_chars:
                break
            take = min(len(line), total_chars - cnt)
            shown_lines.append(line[:take])
            cnt += len(line)
        for line in shown_lines[-8:]:
            s.blit(self.font_mono.render(line, True, CLR_GREEN), (60, y))
            y += 20

        # progress bar for the full minute
        prog = min(1.0, t / TITLE_FRAMES)
        bar = pygame.Rect(W // 2 - 300, H - 70, 600, 14)
        hd.draw.rect(s, (20, 30, 50), bar, border_radius=7)
        hd.draw.rect(s, CLR_CYAN, (bar.x, bar.y, int(bar.w * prog), bar.h), border_radius=7)
        hd.draw.rect(s, CLR_BORDER, bar, 1, border_radius=7)
        secs_left = max(0, int((TITLE_FRAMES - t) / FPS) + 1)
        self.text_center(self.font_mono, f"INITIALIZING COLONY SYSTEMS  {int(prog * 100):3d}%   ({secs_left}s)",
                         CLR_MUTED, H - 48)
        if t > 180 and (t // 30) % 2 == 0:
            self.text_center(self.font_mono, "[ PRESS SPACE TO SKIP ]", CLR_CYAN, H - 28)

        R.update_draw_particles(s)
        if t > TITLE_FRAMES - 45:
            k = (t - (TITLE_FRAMES - 45)) / 45
            self.fade_surf.set_alpha(int(255 * min(1, k)))
            s.blit(self.fade_surf, (0, 0))

    # ============================================================= STATE: AUTH
    def trigger_auth(self):
        if self.auth_mode == "LOGIN":
            success, msg = self.auth.login(self.txt_username, self.txt_password)
            if success:
                self.active_user = self.txt_username.strip().lower()
                self.system_message = msg
                self.set_state("BRIEFING")
                return
            self.shake = 10
            self.system_message = msg
        else:
            success, msg = self.auth.register(self.txt_username, self.txt_password)
            self.system_message = msg

    AUTH_USER = pygame.Rect(W // 2 - 170, 255, 340, 46)
    AUTH_PASS = pygame.Rect(W // 2 - 170, 330, 340, 46)
    AUTH_LOGIN = pygame.Rect(W // 2 - 170, 410, 160, 46)
    AUTH_REG = pygame.Rect(W // 2 + 10, 410, 160, 46)

    def handle_auth_input(self, events):
        for e in events:
            if (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) or (
                    e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.BACK_RECT.collidepoint(e.pos)):
                self.go_back()
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_TAB:
                    self.selected_field = "PASS" if self.selected_field == "USER" else "USER"
                elif e.key == pygame.K_BACKSPACE:
                    if self.selected_field == "USER":
                        self.txt_username = self.txt_username[:-1]
                    else:
                        self.txt_password = self.txt_password[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.auth_mode = "LOGIN"
                    self.trigger_auth()
                elif e.key == pygame.K_ESCAPE:
                    pass
                elif e.unicode and e.unicode.isprintable():
                    if self.selected_field == "USER" and len(self.txt_username) < 16:
                        self.txt_username += e.unicode
                    elif self.selected_field == "PASS" and len(self.txt_password) < 16:
                        self.txt_password += e.unicode
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = e.pos
                if self.AUTH_USER.collidepoint(pos):
                    self.selected_field = "USER"
                elif self.AUTH_PASS.collidepoint(pos):
                    self.selected_field = "PASS"
                elif self.AUTH_LOGIN.collidepoint(pos):
                    self.auth_mode = "LOGIN"
                    self.trigger_auth()
                elif self.AUTH_REG.collidepoint(pos):
                    self.auth_mode = "REGISTER"
                    self.trigger_auth()

    def render_auth_screen(self):
        s, t = self.canvas, self.anim_tick
        R = self.renderer
        R.draw_background(s, t)
        R.draw_big_eye(s, (W // 2, 360), t, alpha=28, scale=1.5)
        R.draw_glow_text(s, self.font_title, "ALIEN COLONY ESCAPE", CLR_CYAN, (W // 2, 95), glow_alpha=140 + 60 * math.sin(t * 0.06))
        self.text_center(self.font_body, "Deep Space Research Outpost - Terminal Gatekeeper", CLR_MUTED, 130)

        box = pygame.Rect(W // 2 - 250, 185, 500, 330)
        hd.draw.rect(s, CLR_PANEL, box, border_radius=10)
        hd.draw.rect(s, CLR_BORDER, box, 2, border_radius=10)
        # animated top accent
        sx = box.x + int((t * 4) % box.w)
        hd.draw.line(s, CLR_CYAN, (sx, box.y + 1), (min(box.right - 4, sx + 60), box.y + 1), 3)

        blink = (t // 30) % 2 == 0
        for rect, label, val, key in ((self.AUTH_USER, "Operator: ", self.txt_username, "USER"),
                                       (self.AUTH_PASS, "Passkey: ", "*" * len(self.txt_password), "PASS")):
            active = self.selected_field == key
            hd.draw.rect(s, (10, 15, 25), rect, border_radius=6)
            hd.draw.rect(s, CLR_CYAN if active else CLR_BORDER, rect, 2, border_radius=6)
            txt = label + val + ("_" if active and blink else "")
            s.blit(self.font_body.render(txt, True, CLR_TEXT), (rect.x + 14, rect.y + 13))

        mouse = self.mouse_pos()
        for rect, col, hov, label in ((self.AUTH_LOGIN, (25, 90, 175), (40, 130, 235), "LOGIN"),
                                       (self.AUTH_REG, (90, 45, 140), (130, 70, 200), "REGISTER")):
            hd.draw.rect(s, hov if rect.collidepoint(mouse) else col, rect, border_radius=6)
            lbl = self.font_header.render(label, True, CLR_TEXT)
            s.blit(lbl, lbl.get_rect(center=rect.center))

        self.text_center(self.font_mono, "TAB: switch field   ENTER: login   F11: fullscreen", CLR_MUTED, 478)
        if self.system_message:
            clr = CLR_GREEN if "successful" in self.system_message.lower() else CLR_RED
            self.text_center(self.font_body, self.system_message, clr, 530)

        R.draw_alien(s, (W // 2 - 380, 400), t, facing=(1, 0), scale=1.6)
        R.draw_astronaut(s, (W // 2 + 380, 400), t, facing=(-1, 0))
        self.draw_back_button()

    # ========================================================== STATE: BRIEFING
    def handle_briefing_input(self, events):
        if self.back_pressed(events):
            self.go_back()
            return
        total = sum(len(l) for l in self.briefing_lines)
        for e in events:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.state_time * 2.4 < total:
                    self.state_time = int(total / 2.4) + 1     # first press: finish typing
                else:
                    self.set_state("SELECT_DIFF")

    def render_briefing_screen(self):
        s, t = self.canvas, self.anim_tick
        R = self.renderer
        R.draw_background(s, t, speed=0.6)
        R.draw_glow_text(s, self.font_title, LORE_INTRO["title"], CLR_RED, (W // 2, 55), glow_alpha=170)
        self.text_center(self.font_mono, f"LOG LOC: {LORE_INTRO['location']} | {LORE_INTRO['stardate']} | OPERATOR {self.active_user}",
                         CLR_CYAN, 92)

        panel = pygame.Rect(W // 2 - 500, 125, 1000, 480)
        hd.draw.rect(s, CLR_PANEL, panel, border_radius=8)
        hd.draw.rect(s, CLR_BORDER, panel, 2, border_radius=8)

        chars = int(self.state_time * 2.4)
        y = 160
        shown = 0
        cursor = None
        for line in self.briefing_lines:
            if not line:
                y += 14
                continue
            take = max(0, min(len(line), chars - shown))
            shown += len(line)
            if take > 0:
                col = CLR_GOLD if line.startswith(("OBJECTIVE", "CONTROLS")) else CLR_TEXT
                img = self.font_body.render(line[:take], True, col)
                s.blit(img, (panel.x + 50, y))
                cursor = (panel.x + 50 + img.get_width(), y)
            y += 25
        if cursor and (t // 15) % 2 == 0 and chars < shown:
            hd.draw.rect(s, CLR_GREEN, (cursor[0] + 2, cursor[1], 9, 17))

        if chars >= shown and (t // 25) % 2 == 0:
            self.text_center(self.font_header, "[ PRESS SPACEBAR TO PROCEED TO SYSTEM SELECTION ]", CLR_GREEN, 640)
        elif chars < shown:
            self.text_center(self.font_mono, "SPACE: skip typing", CLR_MUTED, 650)
        R.draw_alien(s, (W - 110, 360), t, facing=(-1, 0), scale=1.4)
        self.draw_back_button()

    # ======================================================= STATE: SELECT_DIFF
    CARD_W, CARD_H = 900, 160

    def card_rect(self, i):
        return pygame.Rect((W - self.CARD_W) // 2, 105 + i * 190, self.CARD_W, self.CARD_H)

    def start_game(self, difficulty):
        self.difficulty = difficulty
        self.reset_mission()
        self.set_state("GAMEPLAY")

    def handle_selection_input(self, events):
        if self.back_pressed(events):
            self.go_back()
            return
        names = ["Simple", "Medium", "Hard"]
        self.hover_card = -1
        for i in range(3):
            if self.card_rect(i).collidepoint(self.mouse_pos()):
                self.hover_card = i
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_1, pygame.K_KP1):
                    self.start_game("Simple")
                elif e.key in (pygame.K_2, pygame.K_KP2):
                    self.start_game("Medium")
                elif e.key in (pygame.K_3, pygame.K_KP3):
                    self.start_game("Hard")
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i in range(3):
                    if self.card_rect(i).collidepoint(e.pos):
                        self.start_game(names[i])

    def render_selection_screen(self):
        s, t = self.canvas, self.anim_tick
        R = self.renderer
        R.draw_background(s, t)
        R.draw_glow_text(s, self.font_title, "SELECT XENOMORPH NEURAL ARCHITECTURE", CLR_TEXT, (W // 2, 55), glow_alpha=90)
        self.text_center(self.font_mono, "Press 1 / 2 / 3 or click a card", CLR_MUTED, 82)

        options = [("1", "Simple", (50, 180, 100), 0.1), ("2", "Medium", (230, 160, 40), 0.5),
                   ("3", "Hard", (240, 50, 70), 0.95)]
        for i, (key, name, clr, danger) in enumerate(options):
            info = DIFFICULTY_INTEL[name]
            card = self.card_rect(i)
            hov = self.hover_card == i
            if hov:
                card = card.inflate(14, 8)
                glow = hd.Surface((card.w + 30, card.h + 30), pygame.SRCALPHA)
                hd.draw.rect(glow, (*clr, 40 + int(25 * math.sin(t * 0.15))), glow.get_rect(), border_radius=16)
                s.blit(glow, (card.x - 15, card.y - 15))
            hd.draw.rect(s, (24, 34, 58) if hov else CLR_PANEL, card, border_radius=8)
            hd.draw.rect(s, clr, card, 3 if hov else 2, border_radius=8)

            s.blit(self.font_header.render(f"[{key}] {info['title']}", True, clr), (card.x + 30, card.y + 18))
            s.blit(self.font_mono.render(f"PREDATOR THREAT: {info['threat']}", True, CLR_TEXT), (card.x + 30, card.y + 52))
            y = card.y + 84
            for line in wrap_text(self.font_body, info["description"], self.CARD_W - 240):
                s.blit(self.font_body.render(line, True, CLR_MUTED), (card.x + 30, y))
                y += 22
            R.draw_alien(s, (card.right - 100, card.centery), t + i * 20, facing=(-1, 0), danger=danger, scale=1.5)
        self.draw_back_button()

    # ========================================================= STATE: GAMEPLAY
    def try_move(self, dr, dc):
        nr, nc = self.player_pos[0] + dr, self.player_pos[1] + dc
        self.player_face = (dc, dr)
        if not (0 <= nr < ROWS and 0 <= nc < COLS) or MAP_GRID[nr][nc] != 0:
            return False
        self.player_pos = [nr, nc]

        if (nr, nc) in self.energy_cores:
            self.energy_cores.remove((nr, nc))
            self.collected_cores += 1
            cx, cy = self.tile_center(nr, nc)
            self.renderer.spawn_burst((cx, cy), CLR_GOLD, n=40, speed=4.5, life=45, size=3)
            self.float_texts.append([cx, cy - 20, 60, f"CORE {self.collected_cores}/{self.required_cores}", CLR_GOLD])
            if self.collected_cores >= self.required_cores:
                self.banner = ("AIRLOCK UNLOCKED - RUN TO THE EXIT!", 150)
                self.renderer.spawn_burst(self.tile_center(*self.airlock_pos), CLR_GREEN, n=50, speed=5, life=50, size=3)

        if (nr, nc) == tuple(self.airlock_pos) and self.collected_cores >= self.required_cores:
            self.end_mission("VICTORY")
        elif self.player_pos == self.alien_pos and self.countdown <= 0:
            self.end_mission("DEFEAT")
        return True

    def handle_gameplay_input(self, events):
        if self.back_pressed(events, allow_backspace=False):
            self.go_back()
            return
        if self.countdown > 0:
            return
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return
        keys = pygame.key.get_pressed()
        dr = dc = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dr = -1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dr = 1
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dc = -1
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dc = 1
        if dr or dc:
            self.try_move(dr, dc)
            self.move_cooldown = 7

    def update_gameplay(self):
        if self.countdown > 0:
            self.countdown -= 1
        else:
            self.elapsed += 1
        # smooth visual movement
        for vis, pos, k in ((self.player_vis, self.player_pos, 0.33), (self.alien_vis, self.alien_pos, 0.16)):
            for i in (0, 1):
                d = pos[i] - vis[i]
                vis[i] = pos[i] if abs(d) < 0.02 else vis[i] + d * k
        for ft in self.float_texts:
            ft[1] -= 0.8
            ft[2] -= 1
        self.float_texts = [f for f in self.float_texts if f[2] > 0]
        if self.banner[1] > 0:
            self.banner = (self.banner[0], self.banner[1] - 1)

    def vis_to_px(self, vis):
        return (GRID_ORIGIN_X + vis[1] * TILE_SIZE + TILE_SIZE / 2,
                GRID_ORIGIN_Y + vis[0] * TILE_SIZE + TILE_SIZE / 2)

    def danger_level(self):
        d = abs(self.alien_pos[0] - self.player_pos[0]) + abs(self.alien_pos[1] - self.player_pos[1])
        return max(0.0, min(1.0, 1 - (d - 1) / 9))

    def render_gameplay_screen(self):
        s, t = self.canvas, self.anim_tick
        R = self.renderer
        R.draw_background(s, t, speed=0.4)

        # HUD
        hud = pygame.Rect(GRID_ORIGIN_X, 18, GRID_W, 70)
        hd.draw.rect(s, CLR_PANEL, hud, border_radius=6)
        hd.draw.rect(s, CLR_BORDER, hud, 1, border_radius=6)
        s.blit(self.font_mono.render(f"OPERATOR: {self.active_user}", True, CLR_TEXT), (hud.x + 20, 30))
        s.blit(self.font_mono.render(f"AI SYSTEM: {self.difficulty.upper()}", True, CLR_CYAN), (hud.x + 20, 56))
        cores_col = CLR_GREEN if self.collected_cores >= self.required_cores else CLR_GOLD
        s.blit(self.font_mono.render(f"HYPER-CORES: {self.collected_cores}/{self.required_cores}", True, cores_col), (hud.x + 300, 30))
        s.blit(self.font_mono.render(f"TIME: {self.elapsed // FPS // 60:02d}:{self.elapsed // FPS % 60:02d}", True, CLR_TEXT), (hud.x + 300, 56))
        danger = self.danger_level()
        s.blit(self.font_mono.render("PROXIMITY ALERT", True, CLR_RED if danger > 0.6 else CLR_MUTED), (hud.x + 560, 30))
        bar = pygame.Rect(hud.x + 560, 56, 300, 12)
        hd.draw.rect(s, (30, 20, 30), bar, border_radius=6)
        bar_col = (int(60 + 195 * danger), int(255 - 210 * danger), 60)
        hd.draw.rect(s, bar_col, (bar.x, bar.y, int(bar.w * max(0.04, danger)), bar.h), border_radius=6)
        hd.draw.rect(s, CLR_BORDER, bar, 1, border_radius=6)

        # Station
        s.blit(self.map_surface, (GRID_ORIGIN_X, GRID_ORIGIN_Y))
        R.draw_scan_sweep(s, (GRID_ORIGIN_X, GRID_ORIGIN_Y), (GRID_W, GRID_H), t)

        # Alien's planned route (faint)
        if self.alien_path and self.countdown <= 0:
            pts = [self.vis_to_px(self.alien_vis)] + [self.tile_center(r, c) for r, c in self.alien_path[:12]]
            if len(pts) > 1:
                ov = hd.Surface((W, H), pygame.SRCALPHA)
                hd.draw.lines(ov, (255, 40, 90, 60), False, pts, 3)
                s.blit(ov, (0, 0))

        # Airlock
        ex = pygame.Rect(GRID_ORIGIN_X + self.airlock_pos[1] * TILE_SIZE,
                         GRID_ORIGIN_Y + self.airlock_pos[0] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        R.draw_airlock_exit(s, ex, self.collected_cores >= self.required_cores, t)

        # Cores
        for cr, cc in self.energy_cores:
            R.draw_energy_core(s, self.tile_center(cr, cc), t)

        # Characters (draw lower one last for depth)
        p_moving = abs(self.player_pos[0] - self.player_vis[0]) + abs(self.player_pos[1] - self.player_vis[1]) > 0.1
        px, py = self.vis_to_px(self.player_vis)
        ax, ay = self.vis_to_px(self.alien_vis)
        R.draw_astronaut(s, (int(px), int(py)), t, self.player_face, p_moving)
        R.draw_alien(s, (int(ax), int(ay)), t, self.alien_face, danger)

        R.update_draw_particles(s)

        for x, y, life, txt, col in self.float_texts:
            img = self.font_header.render(txt, True, col)
            img.set_alpha(min(255, life * 6))
            s.blit(img, (x - img.get_width() // 2, y))

        # Banner
        if self.banner[1] > 0:
            a = min(255, self.banner[1] * 6)
            R.draw_glow_text(s, self.font_title, self.banner[0], CLR_GREEN, (W // 2, GRID_ORIGIN_Y + GRID_H // 2),
                             glow_alpha=a * 0.7, alpha=a)

        # Heartbeat vignette when the alien is close
        if danger > 0.35:
            R.draw_vignette(s, danger * (0.55 + 0.45 * math.sin(t * (0.1 + 0.2 * danger))))

        # Footer
        self.text_center(self.font_mono, "WASD / ARROWS: move   BACK / ESC: previous page   F11: fullscreen", CLR_MUTED, H - 26)
        self.draw_back_button()

        # Countdown
        if self.countdown > 0:
            ov = hd.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 120))
            s.blit(ov, (0, 0))
            n = self.countdown // 60 + 1
            frac = (self.countdown % 60) / 60
            label = str(n) if n <= 3 else "3"
            img = self.font_count.render(label, True, CLR_CYAN)
            img = hd.transform.rotozoom(img, 0, 0.7 + 0.6 * frac)
            img.set_alpha(int(80 + 175 * frac))
            s.blit(img, img.get_rect(center=(W // 2, H // 2 - 10)))
            self.text_center(self.font_title, "GET READY - COLLECT 3 CORES, THEN REACH THE AIRLOCK", CLR_TEXT, H // 2 + 100)

    # ============================================================== STATE: END
    def handle_end_input(self, events):
        if self.back_pressed(events):
            self.go_back()
            return
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    self.set_state("SELECT_DIFF")
                elif e.key == pygame.K_r:
                    self.start_game(self.difficulty)

    def render_end_screen(self):
        s, t = self.canvas, self.state_time
        R = self.renderer
        if self.snapshot:
            s.blit(self.snapshot, (0, 0))
        shade = hd.Surface((W, H), pygame.SRCALPHA)
        shade.fill((6, 10, 18, min(215, t * 6)))
        s.blit(shade, (0, 0))

        slide = min(1.0, t / 30)
        ease = 1 - (1 - slide) ** 3
        win = self.game_outcome == "VICTORY"
        if win:
            R.spawn_confetti(3)
            head, col = "STATION ESCAPE SUCCESSFUL!", CLR_GREEN
            msg = "You reactivated the emergency bulkheads and boarded the escape transport."
        else:
            head, col = "VITAL SIGNS TERMINATED", CLR_RED
            msg = "The colony predator tracked down your movement patterns."
            if (t % 90) < 5:        # periodic red flash
                flash = hd.Surface((W, H), pygame.SRCALPHA)
                flash.fill((255, 0, 40, 60))
                s.blit(flash, (0, 0))
        cy = 250 + int((1 - ease) * -200)
        R.draw_glow_text(s, self.font_big, head, col, (W // 2, cy),
                         glow_alpha=150 + 80 * math.sin(t * 0.1), alpha=int(255 * ease))
        if not win:
            R.draw_glow_text(s, self.font_title, "CAUGHT BY THE ALIEN", CLR_RED, (W // 2, cy + 70), glow_alpha=100, alpha=int(255 * ease))
        img = self.font_body.render(msg, True, CLR_TEXT)
        img.set_alpha(int(255 * ease))
        s.blit(img, (W // 2 - img.get_width() // 2, 340))

        stats = f"AI: {self.difficulty.upper()}   |   TIME: {self.elapsed // FPS // 60:02d}:{self.elapsed // FPS % 60:02d}   |   CORES: {self.collected_cores}/{self.required_cores}"
        self.text_center(self.font_mono, stats, CLR_CYAN, 385)

        if not win:
            R.draw_alien(s, (W // 2, 520), self.anim_tick, (0, 1), 1.0, scale=2.2)
        else:
            R.draw_astronaut(s, (W // 2, 520), self.anim_tick, (1, 0), moving=True)

        if t > 40 and (t // 25) % 2 == 0:
            self.text_center(self.font_header, "[ SPACE: TACTICAL SELECTION   |   R: RETRY   |   ESC: BACK ]", CLR_CYAN, 620)
        self.draw_back_button()
        R.update_draw_particles(s)


if __name__ == "__main__":
    app = AlienColonyEscapeApp()
    app.run()