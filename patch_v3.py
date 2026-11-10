"""
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
