#!/usr/bin/env python3
"""Sphene Gyre — neon orbital-slingshot arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "SPHENE GYRE"
HANDLE = "x.com/ElbowOS"

VOID = (18, 6, 8)
INK = (42, 12, 14)
WINE = (72, 18, 28)
COPPER = (255, 140, 64)
AMBER = (255, 196, 72)
GOLD = (255, 226, 120)
CREAM = (255, 244, 228)
ROSE = (255, 92, 118)
MAG = (255, 64, 168)
TEAL = (40, 210, 190)
LIME = (180, 255, 90)

ARENA = pygame.Rect(48, 160, W - 96, 1440)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Well:
    def __init__(self, x, y, mass, col, kind="well"):
        self.x, self.y, self.mass, self.col, self.kind = x, y, mass, col, kind
        self.phase = random.random() * math.tau
        self.vx = random.uniform(-28, 28)
        self.vy = random.uniform(-22, 22)


class Shard:
    def __init__(self, host: Well):
        self.host = host
        self.ang = random.random() * math.tau
        self.rad = random.uniform(90, 210)
        self.spin = random.choice((-1.4, -1.1, 1.1, 1.4))
        self.col = random.choice((GOLD, LIME, TEAL, ROSE, AMBER))
        self.r = random.choice((11, 14, 16))

    @property
    def x(self):
        return self.host.x + math.cos(self.ang) * self.rad

    @property
    def y(self):
        return self.host.y + math.sin(self.ang) * self.rad


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 58)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 30)
        self.reset()
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def reset(self) -> None:
        self.t = 0.0
        self.score = 0
        self.combo = 0
        self.flash = 0.0
        self.sun = Well(W * 0.5, ARENA.centery - 40, 260, GOLD, "sun")
        self.wells = [
            Well(300, 520, 140, COPPER),
            Well(780, 680, 150, ROSE),
            Well(320, 1080, 135, TEAL),
            Well(760, 1240, 145, MAG),
        ]
        self.rocks = [
            Well(random.uniform(ARENA.left + 80, ARENA.right - 80),
                 random.uniform(ARENA.top + 160, ARENA.bottom - 80),
                 40, WINE, "rock")
            for _ in range(5)
        ]
        self.shards = [Shard(random.choice(self.wells + [self.sun])) for _ in range(8)]
        self.sparks: list[Spark] = []
        self.pops: list[tuple] = []
        self.trail: list[tuple] = []
        self.stars = [(random.randint(0, W), random.randint(0, H), random.random()) for _ in range(90)]
        self.host = self.sun
        self.ang = 0.4
        self.rad = 170
        self.spin = 1.35
        self.free = False
        self.vx = self.vy = 0.0
        self.px = self.host.x + math.cos(self.ang) * self.rad
        self.py = self.host.y + math.sin(self.ang) * self.rad
        self.running = True
        self.cooldown = 0.0

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(70, 380)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     random.uniform(0.18, 0.5), col, random.randint(3, 7)))

    def sling(self) -> None:
        if self.cooldown > 0:
            return
        if not self.free:
            tx = -math.sin(self.ang) * self.spin * self.rad
            ty = math.cos(self.ang) * self.spin * self.rad
            self.vx, self.vy = tx * 1.15, ty * 1.15
            self.free = True
            self.cooldown = 0.22
            self.burst(self.px, self.py, COPPER, 10)

    def capture(self, well: Well) -> None:
        self.host = well
        self.free = False
        self.rad = max(78, min(200, math.hypot(self.px - well.x, self.py - well.y)))
        self.ang = math.atan2(self.py - well.y, self.px - well.x)
        cross = (self.px - well.x) * self.vy - (self.py - well.y) * self.vx
        self.spin = 1.55 if cross >= 0 else -1.55
        self.cooldown = 0.18
        self.score += 6
        self.burst(well.x, well.y, well.col, 8)

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.sun.phase += dt * 1.4
        for w in self.wells:
            w.phase += dt * 1.8
            w.x += w.vx * dt
            w.y += w.vy * dt
            if w.x < ARENA.left + 120 or w.x > ARENA.right - 120:
                w.vx *= -1
            if w.y < ARENA.top + 160 or w.y > ARENA.bottom - 120:
                w.vy *= -1
        for r in self.rocks:
            r.phase += dt * 2.2
            r.x += r.vx * dt * 0.4
            r.y += r.vy * dt * 0.4
            r.x = max(ARENA.left + 60, min(ARENA.right - 60, r.x))
            r.y = max(ARENA.top + 80, min(ARENA.bottom - 60, r.y))
        for sh in self.shards:
            sh.ang += sh.spin * dt
        if self.free:
            ax = ay = 0.0
            bodies = [self.sun] + self.wells
            for b in bodies:
                dx, dy = b.x - self.px, b.y - self.py
                d2 = dx * dx + dy * dy + 80
                f = b.mass * 4200 / d2
                inv = 1.0 / math.sqrt(d2)
                ax += dx * inv * f
                ay += dy * inv * f
            self.vx += ax * dt
            self.vy += ay * dt
            spd = math.hypot(self.vx, self.vy)
            if spd > 920:
                self.vx *= 920 / spd
                self.vy *= 920 / spd
            self.px += self.vx * dt
            self.py += self.vy * dt
            if not ARENA.inflate(-24, -24).collidepoint(self.px, self.py):
                self.px = max(ARENA.left + 30, min(ARENA.right - 30, self.px))
                self.py = max(ARENA.top + 30, min(ARENA.bottom - 30, self.py))
                self.vx *= -0.55
                self.vy *= -0.55
            for b in bodies:
                if math.hypot(self.px - b.x, self.py - b.y) < 58 + b.mass * 0.08:
                    self.capture(b)
                    break
        else:
            self.ang += self.spin * dt
            self.rad += math.sin(self.t * 2.2) * 8 * dt
            self.px = self.host.x + math.cos(self.ang) * self.rad
            self.py = self.host.y + math.sin(self.ang) * self.rad
        if self.record and not self.free and self.cooldown <= 0:
            aim = self.best_aim()
            if aim is not None:
                want = math.atan2(aim[1] - self.host.y, aim[0] - self.host.x)
                tang = self.ang + (math.pi / 2 if self.spin > 0 else -math.pi / 2)
                err = (want - tang + math.pi) % math.tau - math.pi
                if abs(err) < 0.28:
                    self.sling()
        live_sh = []
        for sh in self.shards:
            if math.hypot(self.px - sh.x, self.py - sh.y) < sh.r + 16:
                self.combo += 1
                pts = 12 + self.combo * 3
                self.score += pts
                self.flash = 0.14
                self.burst(sh.x, sh.y, sh.col, 16)
                self.pops.append((f"+{pts}", sh.x, sh.y - 18, 0.55, sh.col))
                live_sh.append(Shard(random.choice(self.wells + [self.sun])))
            else:
                live_sh.append(sh)
        self.shards = live_sh
        for r in self.rocks:
            if math.hypot(self.px - r.x, self.py - r.y) < 28:
                self.combo = 0
                self.burst(r.x, r.y, ROSE, 8)
                self.vx *= -0.7
                self.vy *= -0.7
                self.px += (self.px - r.x) * 0.4
                self.py += (self.py - r.y) * 0.4
        self.trail.append((self.px, self.py, COPPER))
        self.trail = self.trail[-48:]
        live = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt + 40 * dt
            sp.life -= dt
            if sp.life > 0:
                live.append(sp)
        self.sparks = live[-220:]
        self.pops = [(a, x, y - 70 * dt, life - dt, c) for a, x, y, life, c in self.pops if life - dt > 0]

    def best_aim(self):
        best, bd = None, 1e9
        for sh in self.shards:
            d = math.hypot(sh.x - self.px, sh.y - self.py)
            if 80 < d < bd:
                bd, best = d, (sh.x, sh.y)
        if best is None:
            others = [w for w in self.wells + [self.sun] if w is not self.host]
            w = min(others, key=lambda b: math.hypot(b.x - self.px, b.y - self.py))
            best = (w.x, w.y)
        return best

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (6 + tw * 16)) % H)
            c = 30 + int(tw * 80)
            pygame.draw.circle(s, (c, c // 3, c // 4), (sx, yy), 1 + int(tw * 2))
        pygame.draw.rect(s, INK, ARENA, border_radius=28)
        pygame.draw.rect(s, COPPER, ARENA, 3, border_radius=28)
        pygame.draw.rect(s, GOLD, ARENA, 1, border_radius=28)
        for body in [self.sun] + self.wells:
            glow = 28 + int(10 * math.sin(body.phase))
            pygame.draw.circle(s, body.col, (int(body.x), int(body.y)), int(body.mass * 0.22) + glow, 2)
            pygame.draw.circle(s, body.col, (int(body.x), int(body.y)), int(18 + body.mass * 0.06))
            pygame.draw.circle(s, CREAM, (int(body.x), int(body.y)), int(18 + body.mass * 0.06), 2)
        pygame.draw.circle(s, GOLD, (int(self.sun.x), int(self.sun.y)), 34)
        pygame.draw.circle(s, AMBER, (int(self.sun.x), int(self.sun.y)), 22)
        for r in self.rocks:
            pygame.draw.circle(s, WINE, (int(r.x), int(r.y)), 18)
            pygame.draw.circle(s, ROSE, (int(r.x), int(r.y)), 18, 2)
        for sh in self.shards:
            rr = int(sh.r + 2 * math.sin(self.t * 5 + sh.ang))
            pygame.draw.circle(s, sh.col, (int(sh.x), int(sh.y)), rr)
            pygame.draw.circle(s, CREAM, (int(sh.x), int(sh.y)), rr, 2)
        if len(self.trail) > 2:
            pts = [(int(x), int(y)) for x, y, _ in self.trail]
            pygame.draw.lines(s, (120, 40, 20), False, pts, 8)
            pygame.draw.lines(s, COPPER, False, pts, 3)
        pygame.draw.circle(s, AMBER, (int(self.px), int(self.py)), 16)
        pygame.draw.circle(s, CREAM, (int(self.px), int(self.py)), 16, 2)
        pygame.draw.circle(s, GOLD, (int(self.px - 4), int(self.py - 5)), 4)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life / 0.4)))
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 160, 60, int(55 * self.flash / 0.14)))
            s.blit(veil, (0, 0))
        title = self.font_lg.render(TITLE, True, COPPER)
        s.blit(title, title.get_rect(center=(W // 2, 54)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 106)))
        s.blit(self.font_md.render(f"SCORE  {self.score}", True, AMBER), (70, 1640))
        s.blit(self.font_md.render(f"CHAIN  x{self.combo}", True, MAG), (W - 340, 1640))
        hint = self.font_sm.render("sling the sphene comet between gravity wells", True, CREAM)
        s.blit(hint, hint.get_rect(center=(W // 2, 1700)))
        for tag, x, y, life, col in self.pops:
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        foot = self.font_sm.render("SPACE sling  A/D spin  R reset  ESC quit", True, (210, 160, 140))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 28)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.reset()
            elif ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.sling()

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            keys = pygame.key.get_pressed()
            if not self.free:
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    self.spin -= 2.8 * dt
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    self.spin += 2.8 * dt
                self.spin = max(-2.6, min(2.6, self.spin))
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/SPHENE_GYRE_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
