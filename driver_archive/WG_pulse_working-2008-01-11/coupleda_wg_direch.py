"""
Test driver code. Anything of lasting importance should be factored out pronto
"""
from __future__ import division
from itertools import izip
import os, sys
import pickle
import random
import numpy as N
import scipy
#
# Local Imports
#
import NewCode
import NewCode.eMAGUSImport as eMAGUSImport
import NewCode.Mesh as Mesh
from NewCode.Utilities import Struct, partial, close_to_point
from NewCode import SubDimMesh, DifferentialForm, SystemMatrix, PostProc, Runners, Feeds
from NewCode.DifferentialForm import Discretiser, SubDimDiscretiser,SubDimDiscretiserEntities
from NewCode.DifferentialForm import DiscretiserDOFs
from NewCode.DiscretisedSystem import CoupledFirstOrderSystemHardSource
from NewCode.tests.TestMeshes import FlatTet, InscribedTetMesh, TwoTets

from NewCode.Feeds import WaveguideEigenMatcher

mesh1 = Mesh.Mesh(FlatTet.listmesh)
mesh2 = Mesh.Mesh(TwoTets.listmesh)
mesh3 = Mesh.Mesh(InscribedTetMesh.listmesh)
input_dat = """&INPUTFILE meshfilename = 'test_tet.fek',
extra_meshfilename =  'waveguide1x0.25x5.1-5.femmesh',
run_label(1) = '  ', 
mesh_type = 'oldfeknative'
aux_inputfilename = 'test_tet.aux' /
&PROBLEM
OUTPUT_ELEMENT_DATA=.F.,
solution_type = 'coupled time domain',
element_order = 'CTLN',
SPARSE = .T.,
ON_SCREEN_REPORTING = .T.,
USE_PRE_CONDITIONER = .F./
&OUTPUTFILE  outfilename = '+test_tet.out'/
"""

f = file('workspace/input.dat', 'w')
f.write(input_dat) ; f.close()

eMAGUSImport.init('workspace')
mesh4 = Mesh.Mesh(eMAGUSImport.get_listmesh())
mesh=mesh4

print 'Mesh elements: ', len(mesh.elements)

Discretiser.BasePformDiscretiser.defaultIntegrationOrder = 8

cb = DifferentialForm.constrained_on_boundary
free = DifferentialForm.allfree
constrained = DifferentialForm.allconstrained
 
from analytical_WG_driver import WGT

g_eps = 1e-10                           # Geometrical tollerance

drv_fun = WGT.discrete_drv_fn
z_measure = WGT.test_z
z_measure_p = close_to_point(z_measure, g_eps)
runtime = WGT.t_final
z_port = 0.
z_port_p = close_to_point(z_port, g_eps)
a=1. ; b=0.25                           # WG x/y dim
zero_p = close_to_point(0, g_eps)
a_p, b_p = (close_to_point(xx, g_eps) for xx in (a,b))
on_port = lambda ent: N.all(z_port_p(ent.nodeCoords[:,2]))
def port_free(ent):
    ncx = ent.nodeCoords[:,0] ; ncy = ent.nodeCoords[:,1]
    return not (N.all(a_p(ncx)) or N.all(zero_p(ncx))
                or N.all(b_p(ncy)) or N.all(zero_p(ncy)))
                                        
on_measurement_port = lambda ent: N.all(z_measure_p(ent.nodeCoords[:,2]))
measurement_port_free = port_free
freeE = cb
freeB = lambda ent: freeE(ent) or on_port(ent)
direch_free = lambda ent: on_port(ent) and port_free(ent)  

class TestRun(Runners.TestRun):
    drv_fun = staticmethod(drv_fun)
    useLU = True
    SystemClass = CoupledFirstOrderSystemHardSource

    def __init__(self, mesh, **kwargs):
        self.system = self.SystemClass(mesh, **kwargs)
        
    def setupSource(self):
        self.sm = sm = Feeds.SurfaceFieldMatcher()
        sm.initSubdim(self.system.discs.E, on_port, port_free)
        self.E_wg = E_wg = Feeds.gen_E_TE01(a,b)
        self.direch_dofArray = sm.matchKnown(E_wg)
        self.system.setDirechBCs(Struct(E=direch_free, B=constrained,
                                        H=constrained, D=constrained))
        self.system.setSourceDOFs(self.direch_dofArray, self.drv_fun)
        
    def setupLogging(self):
        divisor = self.log_divisor
        from NewCode import PostProc
        self.sm_m = sm_m = Feeds.SurfaceFieldMatcher()
        sm_m.initSubdim(self.system.discs.E, on_measurement_port, measurement_port_free)
        self.measure_dofArray = sm_m.matchKnown(self.E_wg)
        self.tif = tif = Feeds.TangentialFuncProjSurfaceIntegral(
            self.system.discs.E, on_measurement_port, measurement_port_free)
        self.test_pts = test_pts = N.array([[a/2, b/2, z_measure]], N.float64)
        test_elnos, test_el_coords = PostProc.LocatePoints(self.system.discs.E.mesh, test_pts)
        self.test_elnos = test_elnos ; self.test_el_coords = test_el_coords
        self.system.addReconstructedLogger('E', test_elnos, test_el_coords, divisor=divisor)
        self.logged_dofnos = logged_dofnos = tif.superDOFMap
        self.system.addLogger('E', dofnos=logged_dofnos, divisor=divisor)

    def getResult(self):
        rsv = N.array(self.system.loggedReconstructed.E[0]['vals'])[:,0,:]
        point_reconstructed_ts = rsv[:,1]
        sm_m = self.sm_m
        measure_dofArray = self.measure_dofArray
        nf =  N.dot(measure_dofArray, sm_m.subDisc.matrix.mass().matvec(measure_dofArray))
        ts_modeintg_n = N.array([
            N.dot(measure_dofArray, sm_m.subDisc.matrix.mass().matvec(dof_vec))
            for dof_vec in self.system.loggedDOFs.E[tuple(self.logged_dofnos)].vals],
                                N.float64)/nf        
        return Struct(point_reconstructed_ts=point_reconstructed_ts,
                      nf=nf, ts_modeintg_n=ts_modeintg_n)

analytical_dt = WGT.dt                  # Should be 0.0625

#orders = (1,2,3,4)
orders = (1,)
#dt_divisors = (128,64,32,16,8,4,2,1)
dt_divisors = (6,)
resses = {}
for order in orders:
    if not order in resses: resses[order]={}
    H_order = E_order = (order, True)
    D_order = B_order = (order-1, False) if order > 1 else (order, True)
    TRS = TestRun(mesh, BCs=Struct(E=freeE, B=freeB, D=free, H=free),
                  disc_orders=dict(E=E_order, B=B_order, H=H_order, D=D_order))
    TRS.setupSource()
    for dt_div in dt_divisors:
        print 'order: ', order
        dt = analytical_dt/dt_div
        no_steps = int(N.ceil(runtime/dt))
        TRS.log_divisor = dt_div
        TRS.set_dt(dt)      
        TRS.runSteps(no_steps)
        resses[order][dt_div] = TRS.getResult()


pickle.dump(resses, file('+coupleda_wg_tmp.pickle', 'w'))
