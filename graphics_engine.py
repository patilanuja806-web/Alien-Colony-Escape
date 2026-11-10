"""
High-Definition Procedural Graphics Renderer.
Animated Alien Bioforms, Astronaut, Plasma Cores, Airlock, Starfields,
Particles, Glow text and the cinematic title sequence.
"""
import math
import random
import pygame

import hd


class GraphicsRenderer:
    def __init__(self, width=1280, height=720):
        self.w = width
        self.h = height
        self.particles = []       # [x, y, vx, vy, life, max_life, color, size, gravity]
        self.stars = [[random.uniform(0, width), random.uniform(0, height), random.uniform(0.2, 1.0)]for _ in range(170)]
        self._glyph_cache = {}
        self._glow_cache = {}
        self._bg = self._make_background()
        self._scan = self._make_scanlines()
        self._vignette = self._make_vignette()

    # ------------------------------------------------------------------ setup
    def _make_background(self):
        s = hd.Surface((self.w, self.h))
        for y in range(self.h):
            t = y / self.h
            hd.draw.line(s, (int(6 + 10 * t), int(8 + 12 * t), int(18 + 26 * t)), (0, y), (self.w, y))
        return s

    def _make_scanlines(self):
        s = hd.Surface((self.w, self.h), pygame.SRCALPHA)
        for y in range(0, self.h, 3):
            hd.draw.line(s, (0, 0, 0, 36), (0, y), (self.w, y))
        return s

    def _make_vignette(self):
        s = hd.Surface((self.w, self.h), pygame.SRCALPHA)
        steps = 70
        for i in range(steps):
            a = int(210 * (1 - i / steps) ** 2)
            hd.draw.rect(s, (255, 0, 30, a), (i, i, self.w - 2 * i, self.h - 2 * i), 1)
        return s

    # ------------------------------------------------------------- backgrounds
    def draw_background(self, surface, tick, speed=1.0):
        surface.blit(self._bg, (0, 0))
        for st in self.stars:
            st[0] -= st[2] * 0.6 * speed
            if st[0] < 0:
                st[0] = self.w
                st[1] = random.uniform(0, self.h)
            tw = 0.6 + 0.4 * math.sin(tick * 0.05 + st[1])
            b = int((80 + st[2] * 175) * tw)
            col = (b, b, min(255, b + 30))
            if st[2] > 0.8:
                hd.draw.circle(surface, col, (int(st[0]), int(st[1])), 2)
            else:
                surface.set_at((int(st[0]) % self.w, int(st[1]) % self.h), col)

    def draw_scanlines(self, surface):
        surface.blit(self._scan, (0, 0))

    def draw_vignette(self, surface, strength):
        if strength <= 0.02:
            return
        self._vignette.set_alpha(int(255 * min(1.0, strength)))
        surface.blit(self._vignette, (0, 0))

    # --------------------------------------------------------------- particles
    def spawn_burst(self, pos, color, n=24, speed=3.5, life=40, size=3, gravity=0.0):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.4, 1.0) * speed
            self.particles.append([pos[0], pos[1], math.cos(a) * v, math.sin(a) * v,
                                   life * random.uniform(0.6, 1.0), life, color, size, gravity])

    def spawn_ember(self, x, y, color=(0, 220, 255)):
        self.particles.append([x, y, random.uniform(-0.3, 0.3), random.uniform(-1.4, -0.4),
                               random.uniform(60, 120), 120, color, random.choice((1, 2, 2, 3)), 0.0])

    def spawn_confetti(self, n=3):
        for _ in range(n):
            col = random.choice([(40, 255, 130), (0, 220, 255), (255, 215, 0), (255, 80, 160)])
            self.particles.append([random.uniform(0, self.w), -10, random.uniform(-1, 1),
                                   random.uniform(1.5, 3.5), 200, 200, col, random.choice((3, 4, 5)), 0.02])

    def update_draw_particles(self, surface):
        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += p[8]
            p[4] -= 1
            if p[4] > 0:
                alive.append(p)
                k = p[4] / p[5]
                size = max(1, int(p[7] * (0.4 + 0.6 * k)))
                col = (int(p[6][0] * k + 20), int(p[6][1] * k + 20), int(p[6][2] * k + 20))
                col = tuple(min(255, c) for c in col)
                hd.draw.circle(surface, col, (int(p[0]), int(p[1])), size)
        self.particles = alive[-900:]

    # -------------------------------------------------------------- glow text
    def glyph(self, font, text, color):
        key = (id(font), text, color)
        s = self._glyph_cache.get(key)
        if s is None:
            s = font.render(text, True, color)
            self._glyph_cache[key] = s
        return s

    def glow(self, font, text, color):
        key = (id(font), text, color)
        g = self._glow_cache.get(key)
        if g is None:
            base = self.glyph(font, text, color)
            bw, bh = base.get_width() + 60, base.get_height() + 60
            big = hd.Surface((bw, bh), pygame.SRCALPHA)
            big.blit(base, (30, 30))
            small = hd.transform.smoothscale(big, (max(1, bw // 5), max(1, bh // 5)))
            g = hd.transform.smoothscale(small, (bw, bh))
            g.blit(g.copy(), (0, 0))
            self._glow_cache[key] = g
        return g

    def draw_glow_text(self, surface, font, text, color, center, glow_alpha=200, alpha=255):
        g = self.glow(font, text, color)
        t = self.glyph(font, text, color)
        g.set_alpha(int(glow_alpha * 0.35))
        t.set_alpha(int(alpha))
        surface.blit(g, g.get_rect(center=center))
        surface.blit(t, t.get_rect(center=center))
        t.set_alpha(255)

    # ------------------------------------------------------------ title sequence
    def draw_title_line(self, surface, font, text, cy, color, t, t0, glitch=False, pulse=0.0):
        """Letters drop in one-by-one, zooming and flashing, then pulse with glow."""
        widths = [font.size(ch)[0] for ch in text]
        x = self.w // 2 - sum(widths) // 2
        for i, ch in enumerate(text):
            w = widths[i]
            ti = t - (t0 + i * 8)
            if ti >= 0 and ch != ' ':
                k = min(1.0, ti / 26)
                ease = 1 - (1 - k) ** 3
                scale = 1 + (1 - ease) * 2.2
                yoff = -(1 - ease) * 120
                if int(ti) == 0:
                    self.spawn_burst((x + w // 2, cy), color, n=18, speed=4, life=40, size=3)
                surf = self.glyph(font, ch, color)
                gl = self.glow(font, ch, color)
                if scale > 1.01:
                    surf = hd.transform.rotozoom(surf, 0, scale)
                    gl = hd.transform.rotozoom(gl, 0, scale)
                rect = surf.get_rect(center=(x + w // 2, cy + yoff))
                gl.set_alpha(int(120 + 90 * math.sin(t * 0.06 + i * 0.5) + pulse * 40))
                surf.set_alpha(int(255 * min(1.0, ti / 10)))
                surface.blit(gl, gl.get_rect(center=rect.center))
                if glitch and ti > 30:
                    r = self.glyph(font, ch, (255, 40, 80))
                    c = self.glyph(font, ch, (0, 255, 255))
                    off = random.randint(3, 8)
                    r.set_alpha(150)
                    c.set_alpha(150)
                    surface.blit(r, r.get_rect(center=(rect.centerx - off, rect.centery)))
                    surface.blit(c, c.get_rect(center=(rect.centerx + off, rect.centery + 2)))
                    r.set_alpha(255)
                    c.set_alpha(255)
                surface.blit(surf, rect)
            x += w

    def draw_big_eye(self, surface, center, tick, alpha=70, scale=1.0):
        W, H = int(760 * scale), int(340 * scale)
        tmp = hd.Surface((W, H), pygame.SRCALPHA)
        cx, cy = W // 2, H // 2
        a, b = int(340 * scale), int(120 * scale)
        blink = 1.0
        ph = tick % 420
        if ph < 14:
            blink = abs(ph - 7) / 7
        b = max(2, int(b * blink))
        top, bot = [], []
        for i in range(41):
            x = -1 + i / 20
            y = b * (1 - x * x)
            top.append((cx + x * a, cy - y))
            bot.append((cx + x * a, cy + y))
        hd.draw.polygon(tmp, (60, 0, 15, 255), top + bot[::-1])
        hd.draw.polygon(tmp, (255, 30, 80, 255), top + bot[::-1], 4)
        look = math.sin(tick * 0.02) * 90 * scale
        ir = int(95 * scale)
        iris = hd.Surface((ir * 2, ir * 2), pygame.SRCALPHA)
        for r in range(ir, 0, -3):
            k = r / ir
            hd.draw.circle(iris, (int(255 * (1 - k * 0.5)), int(60 * (1 - k)), 20, 255), (ir, ir), r)
        tmp.blit(iris, (cx + look - ir, cy - ir))
        pw = int((10 + 4 * math.sin(tick * 0.1)) * scale)
        hd.draw.ellipse(tmp, (0, 0, 0, 255), (cx + look - pw, cy - int(b * 0.95), pw * 2, int(b * 1.9)))
        # clip to eye shape using mask
        mask = hd.Surface((W, H), pygame.SRCALPHA)
        hd.draw.polygon(mask, (255, 255, 255, 255), top + bot[::-1])
        tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        hd.draw.polygon(tmp, (255, 30, 80, 255), top + bot[::-1], 4)
        tmp.set_alpha(alpha)
        surface.blit(tmp, tmp.get_rect(center=center))

    # ------------------------------------------------------------ map graphics
    def draw_futuristic_tile(self, surface, rect, is_wall, r=0, c=0):
        if is_wall:
            hd.draw.rect(surface, (26, 36, 56), rect)
            hd.draw.rect(surface, (45, 68, 105), rect, 2)
            hd.draw.rect(surface, (34, 50, 80), rect.inflate(-14, -14), 1)
            hd.draw.circle(surface, (80, 115, 170), (rect.left + 5, rect.top + 5), 2)
            hd.draw.circle(surface, (80, 115, 170), (rect.right - 5, rect.bottom - 5), 2)
            hd.draw.line(surface, (60, 90, 140), (rect.left + 8, rect.centery), (rect.right - 8, rect.centery), 1)
        else:
            hd.draw.rect(surface, (12, 17, 28), rect)
            hd.draw.rect(surface, (20, 28, 46), rect, 1)
            if (r + c) % 2 == 0:
                hd.draw.rect(surface, (14, 21, 34), rect.inflate(-6, -6))
            hd.draw.circle(surface, (28, 40, 62), rect.center, 2)

    def build_map_surface(self, grid, tile, size):
        s = hd.Surface(size)
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                self.draw_futuristic_tile(s, pygame.Rect(c * tile, r * tile, tile, tile), v == 1, r, c)
        return s

    def draw_scan_sweep(self, surface, origin, size, tick):
        """A bright radar line that sweeps across the station floor."""
        ox, oy = origin
        w, h = size
        x = ox + int((tick * 3) % (w + 200)) - 100
        s = hd.Surface((90, h), pygame.SRCALPHA)
        for i in range(90):
            hd.draw.line(s, (0, 220, 255, int(34 * i / 90)), (i, 0), (i, h))
        old = surface.get_clip()
        surface.set_clip(pygame.Rect(ox, oy, w, h))
        surface.blit(s, (x, oy))
        surface.set_clip(old)

    # ------------------------------------------------------------- characters
    def draw_astronaut(self, surface, center, tick, facing=(1, 0), moving=False):
        cx, cy = center
        fx, fy = facing
        swing = math.sin(tick * 0.5) * 5 if moving else 0
        bob = -int(abs(math.sin(tick * 0.5)) * 3) if moving else int(math.sin(tick * 0.12) * 1.5)
        cy += bob

        sh = hd.Surface((30, 10), pygame.SRCALPHA)
        hd.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, 30, 10))
        surface.blit(sh, (center[0] - 15, center[1] + 14))

        # thruster flare
        fl = 3 + int(2 * math.sin(tick * 0.3))
        hd.draw.circle(surface, (0, 180, 255), (int(cx - 5 - swing), cy + 17 + fl // 2), 2)
        hd.draw.circle(surface, (0, 180, 255), (int(cx + 5 + swing), cy + 17 + fl // 2), 2)
        # legs
        hd.draw.rect(surface, (150, 165, 190), (int(cx - 8 + swing), cy + 7, 6, 10), border_radius=2)
        hd.draw.rect(surface, (150, 165, 190), (int(cx + 2 - swing), cy + 7, 6, 10), border_radius=2)
        hd.draw.rect(surface, (70, 80, 100), (int(cx - 8 + swing), cy + 14, 7, 4), border_radius=1)
        hd.draw.rect(surface, (70, 80, 100), (int(cx + 2 - swing), cy + 14, 7, 4), border_radius=1)
        # backpack on the side opposite to facing
        back = -1 if fx >= 0 else 1
        if fy != 0 and fx == 0:
            hd.draw.rect(surface, (80, 90, 110), (cx - 9, cy - 4, 18, 16), border_radius=3)
        else:
            hd.draw.rect(surface, (80, 90, 110), (cx + back * 10 - 3, cy - 3, 7, 16), border_radius=2)
        # arms
        hd.draw.line(surface, (200, 208, 225), (cx - 9, cy + 1), (cx - 12, int(cy + 8 - swing)), 4)
        hd.draw.line(surface, (200, 208, 225), (cx + 9, cy + 1), (cx + 12, int(cy + 8 + swing)), 4)
        # torso
        hd.draw.rect(surface, (230, 235, 245), (cx - 9, cy - 3, 18, 15), border_radius=5)
        hd.draw.rect(surface, (150, 165, 190), (cx - 9, cy - 3, 18, 15), 2, border_radius=5)
        led = (255, 60, 60) if (tick // 20) % 2 == 0 else (60, 255, 120)
        hd.draw.circle(surface, led, (cx + fx * 3, cy + 4), 2)
        # helmet
        hc = (cx, cy - 9)
        hd.draw.circle(surface, (235, 240, 250), hc, 11)
        hd.draw.circle(surface, (150, 165, 190), hc, 11, 2)
        if fy < 0 and fx == 0:      # facing away: back of helmet
            hd.draw.circle(surface, (200, 208, 225), hc, 7)
        else:
            vis = pygame.Rect(0, 0, 14, 11)
            vis.center = (cx + fx * 4, cy - 9 + (3 if fy > 0 else 0))
            hd.draw.ellipse(surface, (0, 200, 240), vis)
            hd.draw.ellipse(surface, (255, 255, 255), (vis.x + 2, vis.y + 2, 5, 4))
            hd.draw.ellipse(surface, (0, 120, 170), vis, 1)
        # antenna
        hd.draw.line(surface, (150, 165, 190), (cx - 6, cy - 18), (cx - 8, cy - 23), 1)
        hd.draw.circle(surface, led, (cx - 8, cy - 23), 2)

    def draw_alien(self, surface, center, tick, facing=(1, 0), danger=0.0, scale=1.0):
        """Animated xenomorph: pulsing aura, wriggling tentacles, tracking eyes."""
        cx, cy = center
        s = scale
        fx, fy = facing
        if fx == 0 and fy == 0:
            fx = 1
        px, py = -fy, fx
        pulse = math.sin(tick * 0.15)
        core_color = (130, 0, 35)
        alien_color = (255, 30, 80)

        R = int((30 + 5 * pulse + 14 * danger) * s)
        aura = hd.Surface((R * 2, R * 2), pygame.SRCALPHA)
        for i in range(5):
            hd.draw.circle(aura, (255, 40, 90, int(10 + 12 * danger)), (R, R), R - i * max(1, R // 6))
        surface.blit(aura, (cx - R, cy - R))

        # tentacles (3 segments each, wriggling)
        for idx in range(8):
            base = idx * math.pi / 4 + tick * 0.012
            x, y = float(cx), float(cy)
            for seg in range(3):
                ang = base + math.sin(tick * 0.14 + idx + seg * 0.9) * 0.55
                ln = (8 - seg) * s
                nx, ny = x + math.cos(ang) * ln, y + math.sin(ang) * ln
                hd.draw.line(surface, (200, 20, 60), (x, y), (nx, ny), max(1, int((4 - seg) * s)))
                x, y = nx, ny
            hd.draw.circle(surface, (255, 90, 120), (int(x), int(y)), max(1, int(3 * s)))

        # carapace + elongated head crest toward facing
        body = pygame.Rect(0, 0, int(28 * s), int(24 * s))
        body.center = (cx, cy)
        hd.draw.ellipse(surface, core_color, body)
        hd.draw.ellipse(surface, alien_color, body, 2)
        head = pygame.Rect(0, 0, int(20 * s), int(16 * s))
        head.center = (cx + int(fx * 7 * s), cy + int(fy * 7 * s))
        hd.draw.ellipse(surface, (170, 10, 50), head)
        hd.draw.ellipse(surface, alien_color, head, 1)

        # eyes (look toward facing) with slit pupils
        ex, ey = cx + fx * 6 * s, cy + fy * 6 * s
        for sgn in (-1, 1):
            ox = ex + px * 5 * sgn * s
            oy = ey + py * 5 * sgn * s
            hd.draw.circle(surface, (255, 255, 60), (int(ox), int(oy)), max(2, int(3.5 * s)))
            hd.draw.circle(surface, (40, 0, 0), (int(ox + fx * s), int(oy + fy * s)), max(1, int(1.5 * s)))
        # jaw / teeth
        jx, jy = cx + fx * 13 * s, cy + fy * 13 * s
        for k in (-1, 0, 1):
            tx = jx + px * k * 3 * s
            ty = jy + py * k * 3 * s
            hd.draw.line(surface, (255, 255, 255), (tx, ty), (tx + fx * 3 * s, ty + fy * 3 * s), 1)

    def draw_energy_core(self, surface, center, tick):
        cx, cy = center
        pulse = 2 * math.sin(tick * 0.2)
        gr = 24
        g = hd.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        for i in range(5):
            hd.draw.circle(g, (255, 215, 0, 18), (gr, gr), int(gr - i * 3 + pulse))
        surface.blit(g, (cx - gr, cy - gr))
        spin = abs(math.cos(tick * 0.07))
        w = max(2, int(7 * spin))
        diamond = [(cx, cy - 9), (cx + w, cy), (cx, cy + 9), (cx - w, cy)]
        hd.draw.polygon(surface, (255, 245, 200), diamond)
        hd.draw.polygon(surface, (255, 200, 0), diamond, 2)
        for i in range(3):
            a = tick * 0.08 + i * math.tau / 3
            hd.draw.circle(surface, (255, 255, 160), (int(cx + math.cos(a) * 14), int(cy + math.sin(a) * 9)), 2)

    def draw_airlock_exit(self, surface, rect, unlocked, anim_tick):
        pulse = 0.5 + 0.5 * math.sin(anim_tick * 0.12)
        if unlocked:
            color = (0, int(200 + 55 * pulse), 140)
            g = hd.Surface((rect.w + 40, rect.h + 40), pygame.SRCALPHA)
            hd.draw.rect(g, (0, 255, 140, int(30 + 40 * pulse)), g.get_rect(), border_radius=14)
            surface.blit(g, (rect.x - 20, rect.y - 20))
        else:
            color = (140, 70, 70) if (anim_tick // 30) % 2 else (90, 70, 80)
        hd.draw.rect(surface, (15, 25, 20), rect)
        hd.draw.rect(surface, color, rect, 3, border_radius=6)
        # sliding doors
        gap = int((rect.w // 2 - 4) * (0.35 + 0.35 * pulse)) if unlocked else 0
        half = rect.w // 2 - 3
        hd.draw.rect(surface, (40, 55, 60), (rect.x + 3 - gap, rect.y + 4, half, rect.h - 8))
        hd.draw.rect(surface, (40, 55, 60), (rect.centerx + gap, rect.y + 4, half, rect.h - 8))
        for i in range(-10, rect.width, 10):
            p1 = (rect.left + max(0, i), rect.top + 4)
            p2 = (rect.left + min(rect.width, i + 10), rect.bottom - 4)
            hd.draw.line(surface, color, p1, p2, 1)
        hd.draw.circle(surface, color, rect.center, 6)
        if not unlocked:
            hd.draw.line(surface, (255, 80, 80), (rect.centerx - 5, rect.centery - 5), (rect.centerx + 5, rect.centery + 5), 2)
            hd.draw.line(surface, (255, 80, 80), (rect.centerx + 5, rect.centery - 5), (rect.centerx - 5, rect.centery + 5), 2)