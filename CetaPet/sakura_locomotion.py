# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_locomotion.py.disabled
# """Direction-specific articulated rig with shared ground anchors and live facial features."""
# from pathlib import Path
# from dataclasses import replace
# import math
# from PySide6.QtCore import Qt,QRectF,QPointF
# from PySide6.QtGui import QImage,QPainter,QPixmap,QPen,QColor,QPainterPath,QTransform,QPolygonF
# from sakura_face import FACE_PARAMS,mix_face
# BASE=Path(__file__).resolve().parent/'asset_library/sakura/v4'
# FEAR=(1.22,1.16,-9,-8,-4,4,-2,4.2,0,7)
# def lerp(a,b,t):return a+(b-a)*t
# def blend_point(a,b,t):return lerp(a[0],b[0],t),lerp(a[1],b[1],t)
# def grounded(image,height,dpr):
#     # Normalize the actual supporting sole, including rotated boot corners.
#     # The fixed logical foot anchor is also used by navigation and persistence.
#     w,h=image.width(),image.height();alpha=bytes(image.constBits())[3::4]
#     bottom=next((y for y in range(h-1,-1,-1) if max(alpha[y*w:(y+1)*w],default=0)>=32),None)
#     if bottom is None:return image
#     dy=round(height*950/900*dpr)-1-bottom
#     if not dy:return image
#     out=QImage(image.size(),QImage.Format_ARGB32_Premultiplied);out.fill(Qt.transparent)
#     p=QPainter(out);p.drawImage(0,dy,image);p.end();return out
# 
# class LocomotionRig:
#     def __init__(self,front):
#         self.front=front
#         self.turn_keys={i:QPixmap(str(BASE/'turn_sequence'/f'{i:02}.png')) for i in range(16)}
#         self.parts={d:{p.stem:QPixmap(str(p)) for p in (BASE/d).glob('*.png')} for d in ('back','left','right')}
#         # Original front legs are split at their knee, preserving all original pixels.
#         self.parts['down']={}
#         for name,old in (('near','left_leg'),('far','right_leg')):
#             pm=front.layers[old];k=round(pm.height()*.47)
#             self.parts['down'][name+'_thigh']=pm.copy(0,0,pm.width(),k)
#             self.parts['down'][name+'_shin']=pm.copy(0,k-6,pm.width(),pm.height()-k+6)
#     def part(self,p,pm,rect,angle=0):
#         p.save();p.translate(rect[0]+rect[2]/2,rect[1]+rect[3]*.12);p.rotate(angle);p.translate(-rect[2]/2,-rect[3]*.12)
#         p.drawPixmap(QRectF(0,0,rect[2],rect[3]),pm,QRectF(pm.rect()));p.restore()
#     def segment(self,p,pm,start,end,a=(.5,.05),b=(.5,.95),opacity=1,width_limit=None):
#         x0,y0=a[0]*pm.width(),a[1]*pm.height();x1,y1=b[0]*pm.width(),b[1]*pm.height()
#         source=math.hypot(x1-x0,y1-y0);target=math.dist(start,end)
#         if source<1 or target<1:return
#         angle=math.degrees(math.atan2(end[1]-start[1],end[0]-start[0])-math.atan2(y1-y0,x1-x0))
#         scale=target/source
#         p.save();p.setOpacity(opacity);p.translate(*start);p.rotate(math.degrees(math.atan2(end[1]-start[1],end[0]-start[0])))
#         thickness=scale
#         if width_limit is not None:thickness=min(scale,width_limit/max(1,pm.width()))
#         p.scale(scale,thickness);p.rotate(-math.degrees(math.atan2(y1-y0,x1-x0)))
#         p.translate(-x0,-y0);p.drawPixmap(0,0,pm);p.restore()
#     def hair(self,p,pm,rect,time,fold,grounded=False):
#         x,y,w,h=rect;phase=math.tau*(time%12)/12
#         for row in range(14):
#             v0=row/14;v1=(row+1)/14
#             dx0=(7+7*(1-fold))*v0*v0*math.sin(phase*3-v0*2)
#             dx1=(7+7*(1-fold))*v1*v1*math.sin(phase*3-v1*2)
#             if grounded:
#                 dx0*=max(0,min(1,(1-v0)/.18));dx1*=max(0,min(1,(1-v1)/.18))
#             src=QPolygonF([QPointF(0,pm.height()*v0),QPointF(pm.width(),pm.height()*v0),QPointF(pm.width(),pm.height()*v1),QPointF(0,pm.height()*v1)])
#             dst=QPolygonF([QPointF(x+dx0,y+h*v0),QPointF(x+w+dx0,y+h*v0),QPointF(x+w+dx1,y+h*v1),QPointF(x+dx1,y+h*v1)])
#             transform=QTransform()
#             if QTransform.quadToQuad(src,dst,transform):
#                 p.save();p.setTransform(transform,True);p.drawPixmap(QRectF(0,pm.height()*v0,pm.width(),pm.height()/14+.8),pm,QRectF(0,pm.height()*v0,pm.width(),pm.height()/14+.8));p.restore()
#     def leg(self,p,parts,name,hip,foot,bend=1,fold=0,far=False):
#         dx,dy=foot[0]-hip[0],foot[1]-hip[1];distance=max(1,math.hypot(dx,dy));l1,l2=lerp(112,50,fold),lerp(150,120,fold)
#         cos=max(-1,min(1,(distance*distance+l1*l1-l2*l2)/(2*distance*l1)))
#         angle=math.atan2(dx,dy)+bend*math.acos(cos)
#         knee=(hip[0]+l1*math.sin(angle),hip[1]+l1*math.cos(angle))
#         p.save();p.setPen(Qt.NoPen);p.setBrush(QColor('#edc1b5'));p.drawEllipse(QPointF(*knee),7 if not fold else 6,7 if not fold else 6);p.restore()
#         thigh=parts[name+'_thigh'];shin=parts[name+'_shin']
#         alpha=.90 if far else 1
#         self.segment(p,thigh,hip,knee,opacity=alpha)
#         self.segment(p,shin,knee,foot,opacity=alpha)
#     def ear_head(self,p,pm,rect,fold):
#         x,y,w,h=rect
#         for row in range(10):
#             for col in range(6):
#                 u0,u1=col/6,(col+1)/6;v0,v1=row/10,(row+1)/10
#                 def target(u,v):
#                     outer=max(0,1-abs(u-.15)/.23)+max(0,1-abs(u-.85)/.23)
#                     top=max(0,1-v/.42);sign=-1 if u<.5 else 1
#                     return QPointF(x+w*u+sign*fold*w*.065*outer*top,y+h*v+fold*h*.30*outer*top)
#                 src=QPolygonF([QPointF(pm.width()*u0,pm.height()*v0),QPointF(pm.width()*u1,pm.height()*v0),QPointF(pm.width()*u1,pm.height()*v1),QPointF(pm.width()*u0,pm.height()*v1)])
#                 dst=QPolygonF([target(u0,v0),target(u1,v0),target(u1,v1),target(u0,v1)])
#                 transform=QTransform()
#                 if QTransform.quadToQuad(src,dst,transform):
#                     p.save();p.setTransform(transform,True)
#                     area=QRectF(pm.width()*u0,pm.height()*v0,pm.width()/6+.5,pm.height()/10+.5)
#                     p.drawPixmap(area,pm,area);p.restore()
#     def side_face(self,p,rect,direction,blink,fear):
#         # Heads were generated with clean face skin, so exactly one eye is rendered.
#         x,y,w,h=rect;cx=x+w*(.19 if direction=='left' else .80);cy=y+h*(.58 if direction=='left' else .69)
#         sign=-1 if direction=='left' else 1;opening=max(0,1-blink)
#         p.setPen(QPen(QColor('#352534'),2.0,Qt.SolidLine,Qt.RoundCap));p.setBrush(QColor('#9c7895'))
#         if opening<=.1:
#             path=QPainterPath();path.moveTo(cx-10,cy);path.quadTo(cx,cy+4,cx+9,cy+1);p.drawPath(path)
#         else:
#             p.save()
#             lens=QPainterPath();lens.moveTo(cx-9,cy-5*opening);lens.cubicTo(cx-4,cy-13*opening,cx+6,cy-11*opening,cx+9,cy);lens.cubicTo(cx+6,cy+11*opening,cx-5,cy+12*opening,cx-9,cy+3*opening);lens.closeSubpath()
#             p.setClipPath(lens);pm=self.front.face.eyes[0]
#             p.drawPixmap(QRectF(cx-10,cy-12*opening,20,24*opening),pm,QRectF(pm.rect()));p.restore()
#         p.setPen(QPen(QColor('#715065'),1.5));p.drawLine(QPointF(cx-9,cy-18-4*fear),QPointF(cx+7,cy-17-6*fear))
#         p.setPen(QPen(QColor('#b87980'),1.1));p.drawLine(QPointF(cx+sign*11,cy+25),QPointF(cx+sign*15,cy+25+2*fear))
#     def turn_key(self,index,pose,height,dpr):
#         if index%4==0:
#             return self.render(replace(pose,direction={0:'down',4:'left',8:'up',12:'right'}[index],turn_from=-1,walk_weight=0,fold=0),height,dpr)
#         pm=self.turn_keys[index]
#         image=QImage(math.ceil(height*.8*dpr),math.ceil(height*1000/900*dpr),QImage.Format_ARGB32_Premultiplied);image.fill(Qt.transparent)
#         p=QPainter(image);p.setRenderHints(QPainter.SmoothPixmapTransform);p.scale(height/900*dpr,height/900*dpr)
#         raw=pm.toImage().convertToFormat(QImage.Format_RGBA8888);a=bytes(raw.constBits())[3::4];w=raw.width();h=raw.height()
#         feet=[i%w for i in range(round(w*h*.92),w*h) if a[i]>100]
#         sole=sum(feet)/len(feet) if feet else w/2;s=900/h
#         sx=min(s,340/max(1,sole),340/max(1,w-sole))
#         self.hair(p,pm,(360-sole*sx,50,w*sx,900),pose.time,1,True)
#         p.end();image=grounded(image,height,dpr);image.setDevicePixelRatio(dpr);return image
#     def turning(self,pose,height,dpr):
#         # Dense, actually drawn rotation keys, never two figures composited.
#         # Each cell is a different perspective, not a mirror or a scaled front.
#         angle=(pose.turn_from+pose.turn_mix)%8
#         index=round(angle*2)%16
#         return self.turn_key(index,pose,height,dpr)
#     def render(self,pose,height,dpr):
#         if pose.turn_from>=0:return self.turning(pose,height,dpr)
#         direction=pose.direction;fold=max(0,min(1,pose.fold));weight=pose.walk_weight*(1-fold)
#         if fold>.001:direction='down'
#         canvas=QImage(math.ceil(height*.8*dpr),math.ceil(height*1000/900*dpr),QImage.Format_ARGB32_Premultiplied);canvas.fill(Qt.transparent)
#         p=QPainter(canvas);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform);p.scale(height/900*dpr,height/900*dpr)
#         phase=math.tau*(pose.walk_phase%1);wind=math.tau*(pose.time%12)/12
#         bob=weight*3*(1-math.cos(phase*2));sway=3*math.sin(wind)
#         p.translate(sway,0)
#         key='back' if direction=='up' else direction
#         parts=self.parts[key]
#         if key=='down':
#             hair=self.front.layers['back_hair'];hair_rect=(76,143,560,660)
#             head=self.front.layers['head_base'];head_rect=(178,50,410,467)
#             torso=self.front.layers['torso'];torso_rect=(158,365,407,408)
#         else:
#             hair=parts['hair'];head=parts['head'];torso=parts['torso']
#             if key=='back':hair_rect=(94,135,540,670);head_rect=(180,50,395,470);torso_rect=(215,380,315,405)
#             elif key=='left':hair_rect=(260,110,335,690);head_rect=(250,55,315,420);torso_rect=(280,370,235,410)
#             else:hair_rect=(120,110,335,690);head_rect=(205,55,300,420);torso_rect=(245,370,235,410)
#         hair_rect=(hair_rect[0],hair_rect[1]-bob,*hair_rect[2:]);head_rect=(head_rect[0],head_rect[1]-bob,*head_rect[2:]);torso_rect=(torso_rect[0],torso_rect[1]-bob,*torso_rect[2:])
#         breath=math.sin(wind*3)*(1-fold)
#         torso_rect=(torso_rect[0],torso_rect[1]-breath,torso_rect[2],torso_rect[3]*(1+.004*breath))
#         f=fold*fold*(3-2*fold)
#         def rect_mix(a,b):return tuple(lerp(x,y,f) for x,y in zip(a,b))
#         hair_rect=rect_mix(hair_rect,(190,500,350,400));head_rect=rect_mix(head_rect,(175,420,390,440));torso_rect=rect_mix(torso_rect,(280,740,170,155))
#         self.hair(p,hair,hair_rect,pose.time,fold)
#         for name,offset,far in (('far',math.pi,True),('near',0,False)):
#             wave=math.sin(phase+offset);lift=max(0,wave)*24*weight
#             side=key in ('left','right');sign=-1 if key=='left' else 1
#             x=360+(22 if far else -22)*(1-fold)
#             if side:x=360+(8 if far else -8)
#             foot=(x+(wave*30*weight*sign if side else wave*8*weight),950-lift)
#             hip=blend_point((x,695-bob),(375 if far else 345,835),f)
#             legparts=parts
#             # Both feet must point left. The independently drawn near left boot
#             # is reused on the far leg instead of the draft's wrong-facing boot.
#             if key=='left' and far:legparts=dict(parts,far_shin=parts['near_shin'])
#             self.leg(p,legparts,name,hip,foot,bend=(sign if side else (1 if far else -1)),fold=fold,far=far)
#         torso_angle=math.sin(phase)*1.3*weight+fold*5+fold*.7*math.sin(pose.time*11)
#         self.part(p,torso,torso_rect,torso_angle)
# 
#         for name,far in (('far',True),('near',False)):
#             side=key in ('left','right');x=420 if far else 290
#             if side:x=380 if far else 340
#             start_shoulder=(474,425) if far else (294,432)
#             start_hand=(454,472) if far else (201,655)
#             if side:start_shoulder=(x,425);start_hand=(x+(18 if far else -18),662)
#             shoulder=blend_point(start_shoulder,(400 if far else 320,765),f)
#             hand=blend_point((start_hand[0]+math.sin(phase+(math.pi if far else 0))*12*weight,start_hand[1]),(395 if far else 335,845),f)
#             pm=(self.front.layers['right_arm' if far else 'left_arm'] if key=='down' else parts[name+'_arm'])
#             if key=='down':
#                 original=(423,398-bob,153,247) if far else (166,404-bob,160,288)
#                 curled=(360,810,140,130) if far else (300,710,140,160)
#                 # One sleeve texture throughout the motion; the hand remains part
#                 # of the sleeve rather than dissolving into a second hand.
#                 rect=tuple(lerp(a,b,f) for a,b in zip(original,curled))
#                 self.part(p,pm,rect,math.sin(phase+(math.pi if far else 0))*3*weight)
#             else:self.segment(p,pm,shoulder,hand,a=(.5,.05),b=(.62 if far else .12,.88))
#         if key=='back':self.hair(p,hair,hair_rect,pose.time+.15,fold)
#         if key=='down' and fold>0:self.ear_head(p,head,head_rect,fold)
#         else:self.part(p,head,head_rect,math.sin(wind)*1.1)
#         if key=='down':
#             p.save();p.translate(head_rect[0],head_rect[1]);p.scale(head_rect[2]/372,head_rect[3]/471)
#             values=pose.face_values if pose.face_values is not None else FACE_PARAMS.get(pose.expression,FACE_PARAMS['calm'])
#             values=mix_face(values,FEAR,max(pose.fear,fold))
#             self.front.face.draw(p,pose.blink,values);p.restore()
#             p.save();p.setOpacity(1-f)
#             p.translate(head_rect[0],head_rect[1]);p.scale(head_rect[2]/410,head_rect[3]/467*(1-.4*f));p.translate(-178,-50)
#             self.front._hair(p,'front_left',pose,0,0);self.front._hair(p,'front_right',pose,0,0)
#             p.restore()
#         elif key in ('left','right'):self.side_face(p,head_rect,key,pose.blink,pose.fear)
#         p.end();canvas=grounded(canvas,height,dpr);canvas.setDevicePixelRatio(dpr);return canvas
