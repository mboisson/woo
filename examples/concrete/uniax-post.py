#
# demonstration of the yade.post2d module (see its documentation for details)
#
from yade import post2d
import pylab # the matlab-like interface of matplotlib

# run uniax.py to get this file
O.load('/tmp/uniax-tension.xml.bz2')

# flattener that project to the xz plane
flattener=post2d.AxisFlatten(useRef=False,axis=1)
# return scalar given a Body instance
extractDmg=lambda b: b.state['normDmg']
# will call flattener.planar implicitly
# the same as: extractVelocity=lambda b: flattener.planar(b,b.state['vel'])
extractVelocity=lambda b: b.state['vel']

# create new figure
pylab.figure()
# plot raw damage
post2d.plot(post2d.data(extractDmg,flattener))

# plot smooth damage into new figure
pylab.figure(); ax,map=post2d.plot(post2d.data(extractDmg,flattener,stDev=2e-3))

# show color scale
pylab.colorbar(map,orientation='horizontal')

# raw velocity (vector field) plot
pylab.figure(); post2d.plot(post2d.data(extractVelocity,flattener))

# smooth velocity plot; data are sampled at regular grid
pylab.figure(); ax,map=post2d.plot(post2d.data(extractVelocity,flattener,stDev=1e-3))
# save last (current) figure to file
pylab.gcf().savefig('/tmp/foo.png') 

# show the figures
pylab.show()