"""
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
