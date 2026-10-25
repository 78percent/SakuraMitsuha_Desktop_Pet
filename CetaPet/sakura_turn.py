# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_turn.py.disabled
# """Distance-independent, shortest-path turning. Positions never change during a turn."""
# import math
# 
# ANGLES={'down':0,'left':2,'up':4,'right':6}
# 
# class Facing:
#     def __init__(self,direction='down'):
#         self.angle=float(ANGLES[direction]);self.start=self.angle;self.target=self.angle;self.age=0.;self.duration=0.
#     @property
#     def active(self):return abs(self.target-self.angle)>1e-7
#     def request(self,direction):
#         wanted=ANGLES[direction]
#         if abs((self.target-wanted+4)%8-4)<1e-7:return
#         delta=(wanted-self.angle+4)%8-4
#         self.start=self.angle;self.target=self.angle+delta;self.age=0.;self.duration=.12+.12*abs(delta)
#     def step(self,dt):
#         if not self.active:return
#         self.age+=dt;u=min(1,self.age/max(.001,self.duration));u=u*u*(3-2*u)
#         self.angle=self.start+(self.target-self.start)*u
#     def snapshot(self):
#         low=math.floor(self.angle);return low%8,(low+1)%8,self.angle-low
