"""
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
