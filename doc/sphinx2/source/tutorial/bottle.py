from woo.core import *
from woo.dem import *
import woo, math
from minieigen import *
capsMask=0b0001
loneMask=0b0010
wallMask=0b0011
capsMat=wallMat=woo.utils.defaultMaterial()
S=woo.master.scene=Scene(fields=[DemField(gravity=(0,0,-10),loneMask=loneMask)])
S.dem.par.append(Wall.make(0,axis=2,sense=1,mat=wallMat,mask=wallMask,color=0))
bottle=woo.utils.importSTL('pill-bottle.coarse2.stl',mat=wallMat,mask=wallMask,scale=0.001,shift=(.056,.027,-0.01),ori=((1,0,0),math.pi/2.),color=-.25)
S.dem.par.appendClumped(bottle,centralNode=Node(pos=(0,0,.04)))
S.lab.botNode=S.dem.nodes[0] # this is the bottle node
S.dtSafety=.5

import woo.gl
woo.gl.Renderer.engines=False
woo.gl.Renderer.allowFast=False

factory=CylinderFactory(stepPeriod=100,node=Node(pos=(0,0,.17),ori=Quaternion((0,1,0),math.pi/2.)),radius=.018,height=.05,generator=PharmaCapsuleGenerator(),materials=[capsMat],mask=capsMask,massFlowRate=0,maxMass=.12,label='feed',attemptPar=100,color=-1,doneHook='pillsDone(S)')
S.engines=DemField.minimalEngines(damping=.4)+[factory]
S.saveTmp()

def pillsDone(S):
	# wait for another 0.2s and then start moving the bottle
	S.lab.botNode.dem.impose=InterpolatedMotion(t0=S.time+0.2,poss=[S.lab.botNode.pos,(0,.05,.08),(0,.05,.09),(0,.04,.13)],oris=[Quaternion.Identity,((1,0,0),.666*math.pi),((1,0,0),.85*math.pi),((1,0,0),.9*math.pi)],times=[0,.3,.8,1.6])
