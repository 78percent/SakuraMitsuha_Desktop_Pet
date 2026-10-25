# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_navigation.py.disabled
# """Screen-union navigation in logical foot coordinates; no Qt or desktop IO."""
# from dataclasses import dataclass
# import heapq,math,random
# from sakura_turn import Facing
# 
# @dataclass(frozen=True)
# class Area:
#     x:float;y:float;w:float;h:float
#     @property
#     def right(self):return self.x+self.w
#     @property
#     def bottom(self):return self.y+self.h
# 
# class World:
#     def __init__(self,areas,width=288,height=400):
#         self.areas=[a if isinstance(a,Area) else Area(*a) for a in areas]
#         self.width=width;self.height=height
#     def valid(self,point):
#         x,y=point;l=x-self.width/2;r=x+self.width/2;t=y-self.height;b=y
#         ys=sorted({t,b,*[v for a in self.areas for v in (max(t,a.y),min(b,a.bottom)) if t<v<b]})
#         for ya,yb in zip(ys,ys[1:]):
#             if yb-ya<1e-8:continue
#             mid=(ya+yb)/2;spans=sorted((max(l,a.x),min(r,a.right)) for a in self.areas if a.y<=mid<=a.bottom and a.right>l and a.x<r)
#             edge=l
#             for sa,sb in spans:
#                 if sa>edge+1e-6:return False
#                 edge=max(edge,sb)
#             if edge<r-1e-6:return False
#         return bool(self.areas)
#     def project(self,point):
#         if self.valid(point):return tuple(point)
#         candidates=[]
#         for a in self.areas:
#             if a.w>=self.width and a.h>=self.height:
#                 p=(max(a.x+self.width/2,min(point[0],a.right-self.width/2)),max(a.y+self.height,min(point[1],a.bottom)))
#                 if self.valid(p):candidates.append(p)
#         return min(candidates,key=lambda p:math.dist(p,point)) if candidates else tuple(point)
#     def clear(self,a,b):
#         n=max(1,math.ceil(math.dist(a,b)/8))
#         return all(self.valid((a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n)) for i in range(n+1))
#     def route(self,start,end):
#         start=self.project(start);end=self.project(end)
#         xs=sorted({start[0],end[0],*[x for a in self.areas for x in (a.x+self.width/2,a.right-self.width/2,a.x,a.right)]})
#         ys=sorted({start[1],end[1],*[y for a in self.areas for y in (a.y+self.height,a.bottom,a.y)]})
#         source=(xs.index(start[0]),ys.index(start[1]));target=(xs.index(end[0]),ys.index(end[1]))
#         dist={source:0};previous={};queue=[(0,source)];valid={}
#         def point(node):return xs[node[0]],ys[node[1]]
#         while queue:
#             cost,node=heapq.heappop(queue)
#             if cost!=dist[node]:continue
#             if node==target:break
#             for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
#                 nxt=node[0]+dx,node[1]+dy
#                 if not(0<=nxt[0]<len(xs) and 0<=nxt[1]<len(ys)):continue
#                 key=tuple(sorted((node,nxt)))
#                 if key not in valid:valid[key]=self.clear(point(node),point(nxt))
#                 if not valid[key]:continue
#                 new=cost+math.dist(point(node),point(nxt))
#                 if new<dist.get(nxt,float('inf')):
#                     dist[nxt]=new;previous[nxt]=node;heapq.heappush(queue,(new,nxt))
#         if target not in dist:return []
#         nodes=[target]
#         while nodes[-1]!=source:nodes.append(previous[nodes[-1]])
#         points=[point(n) for n in reversed(nodes)]
#         result=[]
#         for p in points:
#             while len(result)>=2 and ((result[-2][0]==result[-1][0]==p[0]) or (result[-2][1]==result[-1][1]==p[1])):result.pop()
#             result.append(p)
#         return result[1:]
#     def random_target(self,rng):
#         usable=[a for a in self.areas if a.w>=self.width and a.h>=self.height]
#         if not usable:return None
#         a=rng.choice(usable)
#         return rng.uniform(a.x+self.width/2,a.right-self.width/2),rng.uniform(a.y+self.height,a.bottom)
# 
# class Roamer:
#     def __init__(self,world,position,rng=None):
#         self.world=world;self.position=world.project(position);self.rng=rng or random.Random()
#         self.path=[];self.rest=0.;self.speed=0.;self.distance=0.;self.direction='down'
#         self.max_speed=55.;self.acceleration=160.
#         self.facing=Facing();self.walk_age=0.;self.walk_for=self.rng.uniform(3,8)
#     def reconfigure(self,world):
#         self.world=world;self.position=world.project(self.position);self.path=[];self.speed=0.;self.rest=0.
#     def step(self,dt,enabled=True):
#         if not enabled:self.speed=0.;return self.position
#         if self.rest>0:
#             self.rest=max(0,self.rest-dt);self.speed=0.;return self.position
#         if not self.path:
#             self.speed=0.
#             target=self.world.random_target(self.rng)
#             if target:self.path=self.world.route(self.position,target)
#             if not self.path:self.rest=1.;return self.position
#         target=self.path[0];dx=target[0]-self.position[0];dy=target[1]-self.position[1];left=abs(dx)+abs(dy)
#         if left<1e-6:self.path.pop(0);return self.position
#         self.direction=('right' if dx>0 else 'left') if abs(dx)>1e-6 else ('down' if dy>0 else 'up')
#         self.facing.request(self.direction);self.facing.step(dt)
#         if self.facing.active:self.speed=0.;return self.position
#         self.walk_age+=dt
#         remaining=max(0,self.walk_for-self.walk_age)
#         if remaining<=0:
#             self.speed=0.;self.rest=self.rng.uniform(2,6);self.walk_age=0.;self.walk_for=self.rng.uniform(3,8);return self.position
#         self.speed=min(self.max_speed*min(1,remaining/.3),self.speed+self.acceleration*dt,math.sqrt(2*self.acceleration*left))
#         step=min(left,self.speed*dt);fraction=step/left
#         self.position=self.position[0]+dx*fraction,self.position[1]+dy*fraction;self.distance+=step
#         if step>=left-1e-6:
#             self.position=target;self.path.pop(0);self.speed=0.
#             if not self.path:self.rest=self.rng.uniform(2,6)
#         return self.position
