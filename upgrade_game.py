"""
upgrade_game.py - ONE-TIME upgrade for Alien Colony Escape.   Run:  python upgrade_game.py
  * HD / 4K-sharp rendering at your screen's real resolution (hd.py)
  * small BACK button + ESC = go to the previous page (also during gameplay)
  * fixes the Medium alien getting stuck bouncing between two tiles
Safe: makes .bak backups, stops with a message if anything does not match.
"""
import os
import subprocess
import sys

FILES = {}

FILES['hd.py'] = r'''"""
hd.py - resolution-independent drawing layer for Alien Colony Escape.

The game code still thinks in a 1280x720 "logical" world, but everything
(shapes, fonts, surfaces) is rendered at your screen's real resolution, so
text and graphics stay razor sharp instead of being stretched.

MAX_SCALE controls the maximum internal render size:
    1.5 = up to 1920x1080 | 2.0 = up to 2560x1440 (default) | 3.0 = up to 3840x2160 (true 4K, needs a fast PC)
"""
import pygame

MAX_SCALE = 2.0
MIN_SCALE = 0.6
K = 1.0


def init(logical_w, logical_h, screen_w, screen_h):
    global K
    K = max(MIN_SCALE, min(screen_w / logical_w, screen_h / logical_h, MAX_SCALE))


def _n(v):
    return int(round(v * K))


def _w(v):
    return 0 if not v else max(1, int(round(v * K)))


def _pt(p):
    return (int(round(p[0] * K)), int(round(p[1] * K)))


def _rect(r):
    x, y, w, h = r
    left = int(round(x * K))
    top = int(round(y * K))
    return pygame.Rect(left, top, max(0, int(round((x + w) * K)) - left), max(0, int(round((y + h) * K)) - top))


def _dst(surface):
    return surface.surf if isinstance(surface, HSurf) else surface


class HSurf:
    """A pygame Surface that reports and accepts *logical* coordinates."""

    def __init__(self, surf):
        self.surf = surf

    def get_width(self):
        return self.surf.get_width() / K

    def get_height(self):
        return self.surf.get_height() / K

    def get_size(self):
        return (self.get_width(), self.get_height())

    def get_rect(self, **kw):
        r = pygame.Rect(0, 0, int(round(self.get_width())), int(round(self.get_height())))
        for key, val in kw.items():
            setattr(r, key, val)
        return r

    def blit(self, src, dest=(0, 0), area=None, special_flags=0):
        s = src.surf if isinstance(src, HSurf) else src
        a = _rect(area) if area is not None else None
        pos = (int(round(dest[0] * K)), int(round(dest[1] * K)))
        self.surf.blit(s, pos, a, special_flags)

    def fill(self, color, rect=None, special_flags=0):
        if rect is None:
            self.surf.fill(color)
        else:
            self.surf.fill(color, _rect(rect), special_flags)

    def set_alpha(self, value, flags=0):
        self.surf.set_alpha(value)

    def copy(self):
        return HSurf(self.surf.copy())

    def set_clip(self, rect=None):
        self.surf.set_clip(None if rect is None else _rect(rect))

    def get_clip(self):
        r = self.surf.get_clip()
        return pygame.Rect(int(round(r.x / K)), int(round(r.y / K)),
                           int(round(r.w / K)), int(round(r.h / K)))

    def set_at(self, pos, color):
        n = max(1, int(round(K)))
        px, py = _pt(pos)
        self.surf.fill(color, (px, py, n, n))


def Surface(size, flags=0):
    s = pygame.Surface((max(1, _n(size[0])), max(1, _n(size[1]))), flags)
    try:
        s = s.convert_alpha() if flags & pygame.SRCALPHA else s.convert()
    except pygame.error:
        pass
    return HSurf(s)


class HFont:
    def __init__(self, name, size, bold=False):
        self.font = pygame.font.SysFont(name, max(6, int(round(size * K))), bold=bold)

    def render(self, text, antialias, color, background=None):
        if background is None:
            return HSurf(self.font.render(text, antialias, color))
        return HSurf(self.font.render(text, antialias, color, background))

    def size(self, text):
        w, h = self.font.size(text)
        return (w / K, h / K)


def SysFont(name, size, bold=False):
    return HFont(name, size, bold)


class _Draw:
    @staticmethod
    def rect(surface, color, rect, width=0, **kw):
        for key in list(kw):
            if key.startswith("border"):
                kw[key] = _n(kw[key])
        pygame.draw.rect(_dst(surface), color, _rect(rect), _w(width), **kw)

    @staticmethod
    def circle(surface, color, center, radius, width=0):
        pygame.draw.circle(_dst(surface), color, _pt(center), max(1, _n(radius)), _w(width))

    @staticmethod
    def ellipse(surface, color, rect, width=0):
        pygame.draw.ellipse(_dst(surface), color, _rect(rect), _w(width))

    @staticmethod
    def line(surface, color, start, end, width=1):
        pygame.draw.line(_dst(surface), color, _pt(start), _pt(end), max(1, _w(width)))

    @staticmethod
    def lines(surface, color, closed, points, width=1):
        pygame.draw.lines(_dst(surface), color, closed, [_pt(p) for p in points], max(1, _w(width)))

    @staticmethod
    def polygon(surface, color, points, width=0):
        pygame.draw.polygon(_dst(surface), color, [_pt(p) for p in points], _w(width))


class _Transform:
    @staticmethod
    def smoothscale(surf, size):
        return HSurf(pygame.transform.smoothscale(surf.surf, (max(1, _n(size[0])), max(1, _n(size[1])))))

    @staticmethod
    def rotozoom(surf, angle, scale):
        return HSurf(pygame.transform.rotozoom(surf.surf, angle, scale))


draw = _Draw()
transform = _Transform()
'''

FILES['patch_v2.py'] = r'''"""
patch_v2.py - run once inside the project folder:  python patch_v2.py
 1. Crisp rendering: native-resolution fullscreen + smooth scaling, no scanline haze, softer glow.
 2. Small BACK button (and ESC) = go to the previous page, also during gameplay.
 3. Fixes the Medium alien getting stuck bouncing between two tiles (ai_engine.py).
Makes backups: main.py.bak, graphics_engine.py.bak, ai_engine.py.bak
"""
import shutil
import sys

MAIN_EDITS = [
    # --- native fullscreen instead of blurry SCALED ---
    ("""        try:
            self.screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
        except pygame.error:
            self.fullscreen = False
            self.screen = pygame.display.set_mode((W, H))
""",
     """        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            self.fullscreen = False
            self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
"""),

    # --- toggle_fullscreen + view helpers + back button helpers ---
    ("""    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
            self.fullscreen = not self.fullscreen
        except pygame.error:
            pass
""",
     """    def toggle_fullscreen(self):
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
        k = min(sw / W, sh / H)
        tw, th = int(W * k), int(H * k)
        return surf, k, (sw - tw) // 2, (sh - th) // 2, tw, th

    def to_logical(self, pos):
        _, k, ox, oy, _, _ = self.view_transform()
        return (int((pos[0] - ox) / k), int((pos[1] - oy) / k))

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
        pygame.draw.rect(self.canvas, (40, 60, 105) if hov else CLR_PANEL, self.BACK_RECT, border_radius=8)
        pygame.draw.rect(self.canvas, CLR_CYAN if hov else CLR_BORDER, self.BACK_RECT, 2, border_radius=8)
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
"""),

    # --- remap mouse events ---
    ("""        if events is None:
            events = pygame.event.get()

        for event in events:""",
     """        if events is None:
            events = pygame.event.get()
        events = [self.remap_event(e) for e in events]

        for event in events:"""),

    # --- no scanline haze ---
    ("        self.renderer.draw_scanlines(self.canvas)\n", ""),

    # --- smooth, aspect-correct compose ---
    ("""        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))
        pygame.display.flip()""",
     """        surf, k, vx, vy, tw, th = self.view_transform()
        surf.fill((0, 0, 0))
        if (tw, th) == (W, H):
            surf.blit(self.canvas, (vx + ox, vy + oy))
        else:
            surf.blit(pygame.transform.smoothscale(self.canvas, (tw, th)), (vx + ox, vy + oy))
        pygame.display.flip()"""),

    # --- back handling in input handlers ---
    ("""    def handle_auth_input(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:""",
     """    def handle_auth_input(self, events):
        for e in events:
            if (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) or (
                    e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.BACK_RECT.collidepoint(e.pos)):
                self.go_back()
                return
            if e.type == pygame.KEYDOWN:"""),

    ("""    def handle_briefing_input(self, events):
        total = sum""",
     """    def handle_briefing_input(self, events):
        if self.back_pressed(events):
            self.go_back()
            return
        total = sum"""),

    ("""        names = ["Simple", "Medium", "Hard"]
        self.hover_card = -1""",
     """        if self.back_pressed(events):
            self.go_back()
            return
        names = ["Simple", "Medium", "Hard"]
        self.hover_card = -1"""),

    ("""    def handle_end_input(self, events):
        for e in events:""",
     """    def handle_end_input(self, events):
        if self.back_pressed(events):
            self.go_back()
            return
        for e in events:"""),

    # --- draw the back button on each screen ---
    ("        R.draw_astronaut(s, (W // 2 + 380, 400), t, facing=(-1, 0))\n",
     "        R.draw_astronaut(s, (W // 2 + 380, 400), t, facing=(-1, 0))\n        self.draw_back_button()\n"),

    ("        R.draw_alien(s, (W - 110, 360), t, facing=(-1, 0), scale=1.4)\n",
     "        R.draw_alien(s, (W - 110, 360), t, facing=(-1, 0), scale=1.4)\n        self.draw_back_button()\n"),

    ("            R.draw_alien(s, (card.right - 100, card.centery), t + i * 20, facing=(-1, 0), danger=danger, scale=1.5)\n",
     "            R.draw_alien(s, (card.right - 100, card.centery), t + i * 20, facing=(-1, 0), danger=danger, scale=1.5)\n        self.draw_back_button()\n"),

    ("""        if t > 40 and (t // 25) % 2 == 0:
            self.text_center(self.font_header, "[ SPACE: TACTICAL SELECTION   |   R: RETRY ]", CLR_CYAN, 620)
""",
     """        if t > 40 and (t // 25) % 2 == 0:
            self.text_center(self.font_header, "[ SPACE: TACTICAL SELECTION   |   R: RETRY   |   ESC: BACK ]", CLR_CYAN, 620)
        self.draw_back_button()
"""),

    # --- gameplay: small BACK button (cancels the run, returns to difficulty page) ---
    ("""    def handle_gameplay_input(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.set_state("SELECT_DIFF")
                return
""",
     """    def handle_gameplay_input(self, events):
        if self.back_pressed(events, allow_backspace=False):
            self.go_back()
            return
"""),

    ("""        self.text_center(self.font_mono, "WASD / ARROWS: move   ESC: abort   F11: fullscreen", CLR_MUTED, H - 26)
""",
     """        self.text_center(self.font_mono, "WASD / ARROWS: move   BACK / ESC: previous page   F11: fullscreen", CLR_MUTED, H - 26)
        self.draw_back_button()
"""),
]

AI_NEW_FUNC = """_trail = deque(maxlen=60)


def _distances_from(goal, grid, rows, cols):
    dist = {goal: 0}
    queue = deque([goal])
    while queue:
        cur = queue.popleft()
        for nxt in get_valid_neighbors(cur, grid, rows, cols):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    return dist


def search_dbdfs(start, goal, grid, rows, cols, prev_pos=None, max_depth=75):
    # Depth-bounded DFS with momentum (erratic, winding pursuit).
    # Anti-loop rule: if the DFS wants to step back onto a recently visited tile (a loop),
    # the hunter takes one step along the shortest route instead, so it always closes in.
    if prev_pos is None:
        _trail.clear()
    path = _dbdfs_raw(start, goal, grid, rows, cols, prev_pos, max_depth)
    if path and (path[0] == prev_pos or path[0] in _trail):
        dist = _distances_from(goal, grid, rows, cols)
        if start in dist:
            closer = [n for n in get_valid_neighbors(start, grid, rows, cols)
                      if dist.get(n, 10 ** 9) < dist[start]]
            if closer:
                cur = min(closer, key=lambda n: dist[n])
                path = [cur]
                while cur != goal:
                    nxts = [n for n in get_valid_neighbors(cur, grid, rows, cols)
                            if dist.get(n, 10 ** 9) < dist[cur]]
                    if not nxts:
                        break
                    cur = nxts[0]
                    path.append(cur)
    _trail.append(start)
    return path


"""

AI_EDITS = [
    ("def search_dbdfs(start, goal, grid, rows, cols, prev_pos=None, max_depth=75):",
     "def _dbdfs_raw(start, goal, grid, rows, cols, prev_pos=None, max_depth=75):"),
    ("# --- 3: HARD DIFFICULTY - OPTIMAL A* SEARCH ---\n",
     AI_NEW_FUNC + "# --- 3: HARD DIFFICULTY - OPTIMAL A* SEARCH ---\n"),
]

GFX_EDITS = [
    ("        g.set_alpha(int(glow_alpha))\n", "        g.set_alpha(int(glow_alpha * 0.35))\n"),
]


def apply(path, edits, pre=None):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if pre:
        text = pre(text)
    for i, (old, new) in enumerate(edits, 1):
        n = text.count(old)
        if n != 1:
            print(f"[FAILED] {path}: edit #{i} matched {n} times (expected 1). Nothing was changed.")
            print("First line of that edit:", old.strip().splitlines()[0])
            sys.exit(1)
        text = text.replace(old, new)
    shutil.copyfile(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] patched {path}  (backup: {path}.bak)")


def use_logical_mouse(text):
    if text.count("pygame.mouse.get_pos()") < 1:
        print("[FAILED] main.py: mouse code not found.")
        sys.exit(1)
    return text.replace("pygame.mouse.get_pos()", "self.mouse_pos()")


if "__main__" == __name__:
    apply("main.py", MAIN_EDITS, pre=use_logical_mouse)
    apply("graphics_engine.py", GFX_EDITS)
    apply("ai_engine.py", AI_EDITS)
    print("Done. Now run:  python main.py")
'''

FILES['patch_v3.py'] = r'''"""
patch_v3.py - run once in the project folder (AFTER patch_v2.py):  python patch_v3.py
Switches the whole game to native-resolution (HD / 4K) rendering using hd.py.
Backups: main.py.bak3 and graphics_engine.py.bak3
"""
import shutil
import sys

SWAPS = [
    ("pygame.draw.", "hd.draw."),
    ("pygame.Surface(", "hd.Surface("),
    ("pygame.transform.", "hd.transform."),
    ("pygame.font.SysFont(", "hd.SysFont("),
]

MAIN_EDITS = [
    ("import pygame\n\nfrom storyline import", "import pygame\n\nimport hd\nfrom storyline import"),

    ("        self.canvas = hd.Surface((W, H))\n",
     "        hd.init(W, H, *pygame.display.get_surface().get_size())\n        self.canvas = hd.Surface((W, H))\n"),

    ("""    def view_transform(self):
        surf = pygame.display.get_surface()
        sw, sh = surf.get_size()
        k = min(sw / W, sh / H)
        tw, th = int(W * k), int(H * k)
        return surf, k, (sw - tw) // 2, (sh - th) // 2, tw, th

    def to_logical(self, pos):
        _, k, ox, oy, _, _ = self.view_transform()
        return (int((pos[0] - ox) / k), int((pos[1] - oy) / k))
""",
     """    def view_transform(self):
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
"""),

    ("""        surf, k, vx, vy, tw, th = self.view_transform()
        surf.fill((0, 0, 0))
        if (tw, th) == (W, H):
            surf.blit(self.canvas, (vx + ox, vy + oy))
        else:
            surf.blit(hd.transform.smoothscale(self.canvas, (tw, th)), (vx + ox, vy + oy))
        pygame.display.flip()""",
     """        surf, k, vx, vy, tw, th = self.view_transform()
        surf.fill((0, 0, 0))
        cs = self.canvas.surf
        px, py = vx + int(ox * hd.K), vy + int(oy * hd.K)
        if cs.get_size() == (tw, th):
            surf.blit(cs, (px, py))
        else:
            surf.blit(pygame.transform.smoothscale(cs, (tw, th)), (px, py))
        pygame.display.flip()"""),
]

GFX_EDITS = [
    ("import random\nimport pygame\n", "import random\nimport pygame\n\nimport hd\n"),
    ("            g.blit(g, (0, 0))\n", "            g.blit(g.copy(), (0, 0))\n"),
]


def patch(path, edits):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if "import hd" in text:
        print(f"[SKIP] {path} is already patched.")
        return
    for old, new in SWAPS:
        text = text.replace(old, new)
    for i, (old, new) in enumerate(edits, 1):
        n = text.count(old)
        if n != 1:
            print(f"[FAILED] {path}: edit #{i} matched {n} times (expected 1). Nothing was changed.")
            print("   It starts with:", old.strip().splitlines()[0])
            print("   Did you run patch_v2.py first?")
            sys.exit(1)
        text = text.replace(old, new)
    shutil.copyfile(path, path + ".bak3")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] patched {path}  (backup: {path}.bak3)")


if __name__ == "__main__":
    import os
    if not os.path.exists("hd.py"):
        print("[FAILED] hd.py not found in this folder. Create it first.")
        sys.exit(1)
    patch("main.py", MAIN_EDITS)
    patch("graphics_engine.py", GFX_EDITS)
    print("Done. Now run:  python main.py")
'''


PATCHED_MARKERS = ("import hd", "BACK_RECT", "def go_home", "_dbdfs_raw")


def restore_if_already_patched(name):
    bak = name + ".bak"
    if not os.path.exists(name):
        print(f"[FAILED] {name} not found. Run this inside your project folder.")
        sys.exit(1)
    with open(name, "r", encoding="utf-8") as f:
        text = f.read()
    if any(m in text for m in PATCHED_MARKERS) and os.path.exists(bak):
        with open(bak, "r", encoding="utf-8") as f:
            original = f.read()
        with open(name, "w", encoding="utf-8") as f:
            f.write(original)
        print(f"[INFO] {name} was patched before - restored the original from {bak}")


if __name__ == "__main__":
    for name in ("main.py", "graphics_engine.py", "ai_engine.py"):
        restore_if_already_patched(name)
    for name, text in FILES.items():
        with open(name, "w", encoding="utf-8") as f:
            f.write(text)
    for script in ("patch_v2.py", "patch_v3.py"):
        if subprocess.call([sys.executable, script]) != 0:
            print("\nUpgrade stopped. Nothing is half-applied for the failing file. Send me the message above.")
            sys.exit(1)
    print("\nALL DONE. Start the game with:  python main.py")