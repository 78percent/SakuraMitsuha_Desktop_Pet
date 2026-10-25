# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_stealth.py.disabled
# """Deterministic hide-and-seek state machine. No Qt, mouse hooks or file IO."""
# from dataclasses import dataclass
# import random
# 
# 
# def ease(v):
#     v=max(0.,min(1.,v));return v*v*(3-2*v)
# 
# DURATIONS={'vanishing':1.6,'alerting':.65,'folding':.85,'unfold_hidden':1.2,'found_reveal':.8,
#            'unfold_visible':1.5,'settle':.3,'teleport_out':.28,'teleport_in':.38,
#            'recall_unfold':1.2,'recall_reveal':.8}
# HIDDEN={'roam','alerting','folding','crouched','armed','unfold_hidden'}
# 
# @dataclass
# class StealthPose:
#     stage:str
#     fold:float
#     opacity:float
#     water:float
#     contraction:float
#     armed:bool
#     can_roam:bool
# 
# class StealthSession:
#     def __init__(self,rng=None):
#         self.rng=rng or random.Random();self.time=0.;self.stage='visible';self.age=0.
#         self.manual=False;self.deadline=None;self.dwell=0.;self.outside=0.
#         self.origin=None;self.reason='';self.return_now=False;self.trace=[]
#         self._fold_start=0.;self._opacity_start=1.;self._water_start=0.;self.proximity=0.
#     def _enter(self,stage):
#         pose=self.pose();self._fold_start=pose.fold;self._opacity_start=pose.opacity;self._water_start=pose.water
#         self.stage=stage;self.age=0.;self.trace.append(stage)
#         if stage not in ('crouched','armed'):self.dwell=self.outside=0.
#     def hide(self,origin,manual=True):
#         if self.stage!='visible':
#             if manual:self.manual=True;self.deadline=None
#             return False
#         self.origin=origin;self.manual=manual;self.deadline=None;self.reason='';self.return_now=False
#         self._enter('vanishing');return True
#     def discover(self):
#         if self.stage!='armed':return False
#         self.reason='found';self.deadline=None;self._enter('found_reveal');return True
#     def recall(self,reason='recall'):
#         if self.stage=='visible' or self.reason in ('found','recall','timeout'):return False
#         self.reason=reason;self.deadline=None
#         if self.pose().fold>.001:self._enter('recall_unfold')
#         else:self._enter('recall_reveal')
#         return True
#     def step(self,dt,near=False,inside=False,far=True,proximity=0.):
#         if dt<0:raise ValueError('negative time')
#         self.time+=dt;self.age+=dt;self.return_now=False;self.proximity=max(0,min(1,proximity))
#         if self.deadline is not None and self.time>=self.deadline and self.stage in HIDDEN:
#             self.recall('timeout')
#         stage=self.stage
#         if stage=='roam' and near:self._enter('alerting')
#         elif stage=='crouched':
#             if far:self._enter('unfold_hidden')
#             elif inside:
#                 self.dwell+=dt
#                 if self.dwell+1e-9>=1.5:self._enter('armed');self.dwell=1.5
#             else:self.dwell=0.
#         elif stage=='armed':
#             self.outside=0. if inside else self.outside+dt
#             if self.outside+1e-9>=.5:
#                 self.dwell=0.;self._enter('unfold_hidden' if far else 'crouched')
#         elif stage=='unfold_hidden' and near:
#             self._enter('folding')
#         duration=DURATIONS.get(self.stage)
#         if duration and self.age+1e-9>=duration:
#             old=self.stage
#             following={'vanishing':'roam','alerting':'folding','folding':'crouched','unfold_hidden':'roam',
#                        'found_reveal':'unfold_visible','unfold_visible':'settle',
#                        'settle':'teleport_out','teleport_out':'teleport_in','teleport_in':'visible',
#                        'recall_unfold':'recall_reveal','recall_reveal':'teleport_out'}[old]
#             self._enter(following)
#             if old=='vanishing' and not self.manual:self.deadline=self.time+self.rng.uniform(30,60)
#             if old=='teleport_out':self.return_now=True
#             if following=='visible':self.reason='';self.manual=False;self.deadline=None
#         return self.pose()
#     def pose(self):
#         s=self.stage;u=ease(self.age/DURATIONS.get(s,1))
#         fold=0.;opacity=1.;water=0.;contract=0.
#         if s=='vanishing':
#             # The skin/cloth waterizes while still visible, then disappears.
#             water=ease(self.age/.9);opacity=1-.97*ease((self.age-.25)/1.35)
#         elif s=='roam':opacity=.03+.03*ease(self.proximity);water=1.
#         elif s=='alerting':opacity=self._opacity_start;water=1.
#         elif s=='folding':
#             fold=self._fold_start+(1-self._fold_start)*u
#             opacity=self._opacity_start+(.02-self._opacity_start)*u;water=1.
#         elif s in ('crouched','armed'):fold=1.;opacity=.02;water=1.
#         elif s=='unfold_hidden':fold=self._fold_start*(1-u);opacity=.02+.01*u;water=1.
#         elif s=='found_reveal':fold=1.;opacity=.02+.98*u;water=1-u
#         elif s in ('unfold_visible','recall_unfold'):
#             fold=self._fold_start*(1-u)
#             if s=='recall_unfold':opacity=self._opacity_start;water=1.
#         elif s=='recall_reveal':opacity=self._opacity_start+(1-self._opacity_start)*u;water=self._water_start*(1-u)
#         elif s=='teleport_out':opacity=1-u;water=u;contract=u
#         elif s=='teleport_in':opacity=u;water=1-u;contract=1-u
#         return StealthPose(s,fold,opacity,water,contract,s=='armed',s=='roam')
