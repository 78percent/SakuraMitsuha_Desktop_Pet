"""One clean face base and mutually exclusive, registered facial features.

Canonical source coordinates: 372x471. All expressions share the same eyes;
only geometry, brows and mouth change. No old eye pixels exist under a blink.
"""
import math
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

EXPRESSIONS = {'calm':'平静','focused':'专注思考','curious':'好奇','smug':'轻微得意','smile':'浅笑'}
# left/right opening, left/right brow lift, left/right brow slant,
# mouth curve, mouth opening, gaze shift, mouth width
FACE_PARAMS = {
    'calm': (1,1,0,0,0,0,0,0,0,10),
    'focused': (.79,.79,1.5,1.5,2,-2,-1,0,-1,9),
    'curious': (1.08,1.08,-4,-3,-1,1,0,3,1.3,7),
    'smug': (.78,.87,-2,0,-1.7,.6,2,0,1.8,12),
    'smile': (.93,.93,0,0,0,0,3.5,0,0,13),
}
ACTION_EXPRESSION = {'hair':'smug','sleeve':'focused'}

def mix_face(a,b,t):
    t=max(0,min(1,t));t=t*t*(3-2*t)
    return tuple(x+(y-x)*t for x,y in zip(a,b))

class FaceRig:
    def __init__(self, original_head):
        self.eyes = [original_head.copy(92,231,53,49),original_head.copy(178,259,53,45)]

    def draw(self,painter,blink,values):
        left,right,bl,br,sl,sr,curve,opening,gaze,width=values
        for i,(x,y,w,h,openness) in enumerate(((92,231,53,49,left),(178,259,53,45,right))):
            aperture=max(0,(1-blink)*openness)
            # Exactly one eye representation. The closed arc never overlays an iris.
            if aperture <= .10:
                path=QPainterPath()
                path.moveTo(x+4,y+30)
                path.cubicTo(x+15,y+40,x+32,y+43,x+47,y+38)
                painter.setPen(QPen(QColor('#38252f'),2.8,Qt.SolidLine,Qt.RoundCap))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
                for xx,yy,dx,dy in ((x+5,y+31,-3,-2),(x+9,y+34,-3,0)):
                    painter.drawLine(xx,yy,xx+dx,yy+dy)
            else:
                painter.save()
                # Descend towards the lower lid while closing, retaining the eye tilt.
                center=y+h/2 + 10*blink
                painter.translate(x+gaze,center)
                painter.scale(1,aperture)
                painter.translate(0,-h/2)
                clip=QPainterPath()
                clip.moveTo(1,9);clip.cubicTo(12,0,36,1,52,20)
                clip.cubicTo(49,43,20,53,3,31);clip.closeSubpath()
                painter.setClipPath(clip,Qt.IntersectClip)
                painter.drawPixmap(QRectF(0,0,w,h),self.eyes[i],QRectF(self.eyes[i].rect()))
                painter.restore()
        # Single parameterized brows and mouth morph without two drawings dissolving.
        painter.setPen(QPen(QColor(91,57,65,160),1.4,Qt.SolidLine,Qt.RoundCap))
        for x,y,lift,slant in ((103,225,bl,sl),(186,252,br,sr)):
            path=QPainterPath();path.moveTo(x,y+lift-slant)
            path.quadTo(x+13,y+lift-2,x+28,y+lift+5+slant)
            painter.drawPath(path)
        painter.setPen(QPen(QColor('#b87875'),1.2,Qt.SolidLine,Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.save();painter.translate(151,308);painter.rotate(13)
        if opening>.35:
            painter.drawEllipse(QRectF(-opening*.6,-opening*.6,opening*1.2,opening*1.8))
        else:
            path=QPainterPath();path.moveTo(-width/2,0)
            path.quadTo(0,curve,width/2,0)
            painter.drawPath(path)
        painter.restore()
