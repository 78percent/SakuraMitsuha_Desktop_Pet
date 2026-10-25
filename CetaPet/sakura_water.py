# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_water.py.disabled
# """Body-space water material: texture/shape refraction, not a water overlay effect."""
# from dataclasses import dataclass
# import math
# from PySide6.QtCore import Qt,QRectF,QPointF
# from PySide6.QtGui import QImage,QPainter,QPolygonF,QTransform,QLinearGradient,QColor
# 
# @dataclass
# class MaterialFrame:
#     image:QImage
#     coverage:QImage
# 
# class WaterMaterial:
#     def render(self,source,time,amount=0.,opacity=1.,contraction=0.):
#         amount=max(0,min(1,amount));opacity=max(0,min(1,opacity))
#         if amount<=0 and contraction<=0 and opacity>=1:return MaterialFrame(source,source)
#         dpr=source.devicePixelRatio();raw=source.copy();raw.setDevicePixelRatio(1)
#         w,h=raw.width(),raw.height();phase=math.tau*(time%12)/12
#         out=QImage(raw.size(),QImage.Format_ARGB32_Premultiplied);out.fill(Qt.transparent)
#         p=QPainter(out);p.setRenderHints(QPainter.SmoothPixmapTransform)
#         cols,rows=10,18
#         amplitude=amount*5.0*dpr
#         def point(x,y):
#             v=y/h
#             dx=amplitude*(math.sin(v*14-phase*3)+.4*math.sin(x/w*9+v*7+phase*2))
#             dy=amplitude*.6*math.sin(x/w*12+v*5+phase*2)*math.sin(math.pi*v)
#             pull=contraction*(.78+.13*math.sin(math.pi*v))
#             return QPointF(w/2+(x-w/2)*(1-pull)+dx,y+dy)
#         for row in range(rows):
#             for col in range(cols):
#                 x0,x1=w*col/cols,w*(col+1)/cols;y0,y1=h*row/rows,h*(row+1)/rows
#                 src=QPolygonF([QPointF(x0,y0),QPointF(x1,y0),QPointF(x1,y1),QPointF(x0,y1)])
#                 dst=QPolygonF([point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1)])
#                 matrix=QTransform()
#                 if not QTransform.quadToQuad(src,dst,matrix):continue
#                 p.save();p.setTransform(matrix)
#                 rect=QRectF(x0,y0,x1-x0+.6,y1-y0+.6)
#                 p.drawImage(rect,raw,rect);p.restore()
#         # Shading changes the material INSIDE the already refracted body alpha.
#         p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
#         sheen=QLinearGradient(0,0,w,h)
#         shift=.09*math.sin(phase)
#         for pos,color in ((0,'#243a59'),(.29+shift,'#99b8c9'),(.47+shift,'#d5e7ef'),(.59+shift,'#476b87'),(1,'#23344d')):sheen.setColorAt(max(0,min(1,pos)),QColor(color))
#         p.setOpacity(amount*.62);p.fillRect(out.rect(),sheen);p.end()
#         coverage=out.copy();coverage.setDevicePixelRatio(dpr)
#         p=QPainter(out);p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
#         p.fillRect(out.rect(),QColor(255,255,255,round(opacity*255)));p.end()
#         out.setDevicePixelRatio(dpr)
#         return MaterialFrame(out,coverage)
