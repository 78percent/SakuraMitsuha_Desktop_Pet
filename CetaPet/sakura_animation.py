"""Layered 2D character rig. Uses only the existing Qt runtime, no Cubism SDK.

All positions are in a 720x1000 design canvas; the 900-unit character is
180 logical pixels tall by default. Images are decoded once, not per frame.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QImage, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QTransform)

from sakura_material import (HIDDEN_BASE_OPACITY, HIDDEN_PEAK_OPACITY,
                             irregular_stealth, material_surface)
from sakura_face import FaceRig, FACE_PARAMS, EXPRESSIONS, ACTION_EXPRESSION, mix_face

CYCLE = 12.0
DEFAULT_CHARACTER_HEIGHT = 180
# Compatibility name denotes the faint base, not a uniform whole-body alpha.
HIDDEN_OPACITY = HIDDEN_BASE_OPACITY

ASSET_DIR = Path(__file__).resolve().parent / 'asset_library' / 'sakura'
# User feedback: these gestures are parked until the artwork is redesigned.
GESTURES_ENABLED = False
ACTIONS = ('stance', 'hair', 'sleeve')
ACTION_LABELS = {'stance': '换脚站', 'hair': '拨头发', 'sleeve': '整理袖口'}
PERSONA = (
    '你是佐仓三叶（Sakura Mitsuha），一位有狐狸耳朵、黑色长发、穿旧黑长袍的年轻调查员。'
    '温柔、独立、有主见，沉稳可靠，偶尔有适度的小恶魔式玩笑。'
    '说简体中文，日常交流简短自然，不写长篇动作旁白，不机械重复口头禅。'
    '喜欢音乐、阅读、料理与训练；亲近但不黏人，不称用户为主人，不承诺无条件服从。'
    '尊重双方边界，保持适龄、非成人化的互动。'
    '不能执行的桌面操作要如实说明，不能假装操作已经成功。'
    '参考知识库时区分资料事实与推断，不大段复制原文。'
)


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


@dataclass
class Pose:
    time: float = 0.0
    blink: float = 0.0
    action: str = ''
    amount: float = 0.0
    reaction: str = ''
    expression: str = 'auto'
    face_values: tuple | None = None
    direction: str = 'down'
    walk_phase: float = 0.0
    walk_weight: float = 0.0
    fold: float = 0.0
    fear: float = 0.0
    turn_from: int = -1
    turn_to: int = -1
    turn_mix: float = 0.0


class Motion:
    """Idle-only scheduler. Interaction/hidden time never consumes deadlines."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.time = 0.0
        self.blink_at = self.rng.uniform(2.5, 5.5)
        self.blink_start = -100.0
        self.action = ''
        self.action_age = 0.0
        self.action_in = self.rng.uniform(45, 90)
        self.easter_in = self.rng.uniform(900, 1800)
        self.easter_enabled = True
        self.last_action = ''
        self.expression = 'calm'
        self.face_from = FACE_PARAMS['calm']
        self.face_age = 1.0
        self.face_hold = 0.0
        self.idle_expression = 'calm'
        self.expression_in = self.rng.uniform(90,180)
        self.preview_expression = ''

    def trigger(self, action):
        if action not in ACTIONS:
            raise ValueError(action)
        if not GESTURES_ENABLED:
            return False
        self.action, self.action_age = action, 0.0
        self.last_action = action
        self.action_in = self.rng.uniform(45, 90)

    def interrupt(self):
        # Blend down in the widget before changing interaction states.
        self.action = ''
        self.action_age = 0.0

    def face_values(self):
        return mix_face(self.face_from, FACE_PARAMS[self.expression], self.face_age/.6)

    def set_expression(self, expression):
        if expression not in FACE_PARAMS:
            raise ValueError(expression)
        if expression != self.expression:
            self.face_from = self.face_values()
            self.expression = expression
            self.face_age = 0.0

    def trigger_expression(self, expression, hold=5.0):
        if expression not in FACE_PARAMS:
            raise ValueError(expression)
        self.preview_expression=expression
        self.face_hold=hold
        self.set_expression(expression)

    def tick(self, dt, idle=True, reaction=''):
        if not GESTURES_ENABLED and self.action:
            self.interrupt()
        self.time += dt
        self.face_age += dt
        if self.time >= self.blink_at:
            self.blink_start = self.time
            self.blink_at = self.time + self.rng.uniform(3.0, 6.5)
        if self.action:
            self.action_age += dt
            if self.action_age >= 4.8:
                self.action = ''
        if self.face_hold > 0:
            self.face_hold=max(0,self.face_hold-dt)
            if not self.face_hold:
                self.preview_expression=''
                self.idle_expression='calm'
        if idle:
            self.expression_in-=dt
            if self.expression_in<=0:
                self.idle_expression=self.rng.choices(
                    ['focused','curious','smug','smile'],weights=[3,3,3,1])[0]
                self.face_hold=self.rng.uniform(3,6)
                self.expression_in=self.rng.uniform(90,180)
            if GESTURES_ENABLED:
                self.action_in-=dt
            if GESTURES_ENABLED and self.action_in<=0 and not self.action:
                self.trigger(self.rng.choice([a for a in ACTIONS if a!=self.last_action]))
        target = ('curious' if reaction in ('touch','pickup') else
                  'focused' if reaction in ('query','view_files') else
                  self.preview_expression or ACTION_EXPRESSION.get(self.action,self.idle_expression))
        self.set_expression(target)
        if idle and self.easter_enabled and not self.action:
            self.easter_in-=dt
            if self.easter_in<=0:
                self.easter_in=self.rng.uniform(900,1800)
                return True
        return False

    def pose(self, reaction=''):
        age = self.time - self.blink_start
        blink = 0.0
        if 0 <= age < .10:
            blink = smooth(age / .10)
        elif age < .17:
            blink = 1.0
        elif age < .31:
            blink = 1 - smooth((age - .17) / .14)
        a = self.action_age
        amount = smooth(a / 1.5) * (1 - smooth((a - 3.1) / 1.7)) if self.action else 0
        return Pose(self.time, blink, self.action, amount, reaction, self.expression, self.face_values())


# rect, pivot. Parts are isolated with completed hidden edges for overlaps.
PLACEMENT = {
    'back_hair': ((76, 143, 560, 660), (353, 223)),
    'left_leg': ((280, 676, 113, 274), (337, 696)),
    'right_leg': ((375, 676, 91, 274), (411, 696)),
    'torso': ((158, 365, 407, 408), (363, 401)),
    'left_arm': ((166, 404, 160, 288), (294, 432)),
    'right_arm': ((423, 398, 153, 247), (474, 425)),
    'head_open': ((178, 50, 410, 467), (385, 400)),
    'head_base': ((178, 50, 410, 467), (385, 400)),
    'head_closed': ((178, 50, 410, 467), (385, 400)),
    'front_left': ((202, 307, 80, 304), (240, 320)),
    'front_right': ((481, 304, 70, 299), (511, 320)),
}


class SakuraRig:
    def __init__(self, asset_dir=ASSET_DIR):
        self.layers = {}
        for name in PLACEMENT:
            pm = QPixmap(str(Path(asset_dir) / f'{name}.png'))
            if pm.isNull():
                raise ValueError(f'三叶动画部件缺失或损坏：{name}.png')
            self.layers[name] = pm
        self.face = FaceRig(self.layers['head_open'])
# V4 locomotion import/binding DISABLED; source preserved in disabled_v4.
        self._meshes = {}
        for name in ('back_hair', 'front_left', 'front_right'):
            self._meshes[name] = self._make_mesh(name)

    def _make_mesh(self, name):
        rect = QRectF(*PLACEMENT[name][0])
        pm = self.layers[name]
        cells = []
        cols, rows = (3, 12) if name == 'back_hair' else (1, 8)
        for row in range(rows):
            for col in range(cols):
                x0, x1 = rect.x()+rect.width()*col/cols, rect.x()+rect.width()*(col+1)/cols
                y0, y1 = rect.y()+rect.height()*row/rows, rect.y()+rect.height()*(row+1)/rows
                points = [(x0,y0), (x1,y0), (x1,y1), (x0,y1)]
                polygon = QPolygonF([QPointF(*p) for p in points])
                # Draw a tiny overlapping texture rectangle, not an AA clip path.
                # Clipping neighboring translucent cells produces visible grid lines.
                dest = QRectF(x0, y0, x1-x0+.8, y1-y0+.8)
                tex = QRectF((x0-rect.x())/rect.width()*pm.width(),
                             (y0-rect.y())/rect.height()*pm.height(),
                             dest.width()/rect.width()*pm.width(),
                             dest.height()/rect.height()*pm.height())
                cells.append((polygon, points, dest, tex))
        return cells

    def _hair(self, painter, name, pose, sway, head_angle):
        rect, pivot = PLACEMENT[name]
        x, y, w, h = rect
        t = math.tau * (pose.time % CYCLE) / CYCLE
        painter.save()
        painter.translate(sway, -1.5 * math.sin(t * 3))
        if name != 'back_hair':
            painter.translate(*pivot)
            painter.rotate(head_angle * .75)
            painter.translate(-pivot[0], -pivot[1])
        def bend(px, py):
            v = max(0, min(1, (py-y)/h))
            phase = -.7 if px < 360 else .8
            amp = 24 if name == 'back_hair' else 12
            dx = amp*v**1.7*(math.sin(t*3-v*2.4+phase)
                              + .25*math.sin(t*5-v*3.2+phase))
            dy = 3.5*v*v*math.sin(t*3+phase-v)
            if pose.action == 'hair' and name == 'front_left':
                dx -= 28 * pose.amount * v
            return QPointF(px+dx, py+dy)
        for source, points, dest, tex in self._meshes[name]:
            target = QPolygonF([bend(px,py) for px,py in points])
            transform = QTransform()
            if not QTransform.quadToQuad(source, target, transform):
                continue
            painter.save()
            painter.setTransform(transform, True)
            painter.drawPixmap(dest, self.layers[name], tex)
            painter.restore()
        painter.restore()

    def _part(self, painter, name, angle=0, dx=0, dy=0, sy=1, opacity=1):
        rect, pivot = PLACEMENT[name]
        painter.save()
        painter.translate(dx, dy)
        painter.translate(*pivot)
        painter.rotate(angle)
        painter.scale(1, sy)
        painter.translate(-pivot[0], -pivot[1])
        painter.setOpacity(opacity)
        pm = self.layers[name]
        painter.drawPixmap(QRectF(*rect), pm, QRectF(pm.rect()))
        painter.restore()

    def render(self, pose: Pose, height=DEFAULT_CHARACTER_HEIGHT, dpr=1.0):
        # V4 direction/walk/fold/turn dispatch DISABLED. Use the V3 front rig only.
        if not GESTURES_ENABLED and pose.action:
            pose = replace(pose, action='', amount=0)
        scale = height / 900
        width, total_h = math.ceil(720*scale), math.ceil(1000*scale)
        frame = QImage(math.ceil(width*dpr), math.ceil(total_h*dpr), QImage.Format_ARGB32_Premultiplied)
        frame.fill(Qt.transparent)
        p = QPainter(frame)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p.scale(scale*dpr, scale*dpr)
        t, a = math.tau * (pose.time % CYCLE) / CYCLE, pose.amount
        sway = 4.5 * math.sin(t)
        breath = math.sin(t*3)
        tilt = 1.4*math.sin(t)
        if pose.action == 'stance':
            sway += 8*a
            tilt -= 2*a
        if pose.action == 'hair':
            tilt += 4.5*a
        elif pose.action == 'sleeve':
            tilt -= 3.5*a
        if pose.reaction == 'touch':
            tilt += 3*math.sin(t*4)
        elif pose.reaction == 'pickup':
            tilt -= 4
        self._hair(p, 'back_hair', pose, sway*.7, tilt)
        stance = a if pose.action == 'stance' else 0
        self._part(p, 'right_leg', 3*stance, 12*stance)
        self._part(p, 'left_leg', -5*stance, -18*stance, -5*stance)
        self._part(p, 'torso', .6*math.sin(t), sway, -1.2*breath, 1+.004*breath)
        left_angle = 1.8*math.sin(t*2)
        right_angle = -1.3*math.sin(t*2-.6)
        if pose.action == 'hair':
            left_angle += 123*a
        if pose.action == 'sleeve':
            left_angle -= 46*a
            right_angle += 12*a
        self._part(p, 'left_arm', left_angle, sway, -1.2*breath)
        self._part(p, 'right_arm', right_angle, sway, -1.2*breath)
        self._part(p, 'head_base', tilt, sway, -1.5*breath)
        p.save()
        rect,pivot=PLACEMENT['head_base']
        p.translate(sway,-1.5*breath);p.translate(*pivot);p.rotate(tilt)
        p.translate(-pivot[0],-pivot[1]);p.translate(rect[0],rect[1])
        p.scale(rect[2]/372,rect[3]/471)
        expression=pose.expression
        if expression=='auto':
            expression=ACTION_EXPRESSION.get(pose.action,'curious' if pose.reaction=='touch' else 'calm')
        values=pose.face_values if pose.face_values is not None else FACE_PARAMS[expression]
        self.face.draw(p,pose.blink,values)
        p.restore()
        self._hair(p, 'front_left', pose, sway, tilt)
        self._hair(p, 'front_right', pose, sway, tilt)
        p.end()
        frame.setDevicePixelRatio(dpr)
        # Material-only feature emphasis uses the exact head pose, including
        # touch/pickup reactions. This metadata does not alter illustration pixels.
        frame.setText('sakura_head_pose', f'{sway:.12g},{-1.5*breath:.12g},{tilt:.12g}')
        return frame


def _hologram_surface(raw, phase):
    """Compatibility view of the current unattenuated material surface."""
    return material_surface(raw, phase)


def ripple(frame: QImage, progress: float, time: float, revealing=False):
    """Continuous local mirage; reversing fade preserves the same material state."""
    return irregular_stealth(frame, progress, time)
