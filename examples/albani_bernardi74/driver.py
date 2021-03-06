## Copyright (C) 2011 Stellenbosch University
##
## This file is part of SUCEM.
##
## SUCEM is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## SUCEM is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with SUCEM. If not, see <http://www.gnu.org/licenses/>. 
##
## Contact: cemagga@gmail.com 
# Authors:
# Neilen Marais <nmarais@gmail.com>
# Evan Lezar <mail@evanlezar.com>
from __future__ import division

"""
Problem considered:

Eigenvalue solution of a dielectricaly loaded PEC cavity.

Note that the reference result described in Albani_Bernardi74 seems to
be incorrect; they seem to have missed a mode with a lower resonant
frequency.
    
    
Reference: 

'A Numerical Method Based on the Discretization of Maxwell Equations
in Integral Form (Short Papers)' ,Microwave Theory and Techniques,
IEEE Transactions on, vol. 22, no. 4, pp. 446-450, 1974. 
"""
import sys
import numpy as N
import os
import dolfin as dol

sys.path.insert(0, '../../')
from sucemfem.ProblemConfigurations.EMVectorWaveEigenproblem import EigenProblem, DefaultEigenSolver
from sucemfem.BoundaryConditions import PECWallsBoundaryCondition
from sucemfem.Consts import c0
del sys.path[0]

script_path = os.path.dirname(__file__)
# Load the mesh and the material region markers
mesh_file = os.path.join(script_path, 'mesh/albani_bernardi74_fig2VII.xml')
materials_mesh_file = "%s_physical_region%s" % (os.path.splitext(mesh_file))
mesh = dol.Mesh(mesh_file)
material_mesh_func = dol.MeshFunction('uint', mesh, materials_mesh_file)
# Define the dielectric properties of the regions in the mesh
materials = {1000:dict(eps_r=16),
             1001:dict(eps_r=1)}

# init the PEC walls boundary condition
pec_walls = PECWallsBoundaryCondition ()
pec_walls.init_with_mesh ( mesh ) 

# Use 3rd order basis functions 
order = 3
# Set up the eigen problem
ep = EigenProblem()
ep.set_mesh(mesh)
ep.set_basis_order(order)
ep.set_boundary_conditions( pec_walls )
ep.set_material_regions(materials)
ep.set_region_meshfunction(material_mesh_func)
ep.init_problem()

# Set up eigen problem solver where sigma is the shift to use in the shift-invert process
sigma = 1.5
es = DefaultEigenSolver()
es.set_eigenproblem(ep)
es.set_sigma(sigma)

# Solve the eigenproblem
eigs_w, eigs_v = es.solve_problem(10)

# Output the results
#res = N.array(sorted(eigs_w)[0:10])
res = N.array(sorted(1/eigs_w+sigma)[0:10]) #HAVE TO CORRECT FOR THE SPECTRUM SHIFT
print N.sqrt(res)
print c0*N.sqrt(res)/2/N.pi/1e6

print '\nreference:'
print "[ 2.40690704  2.59854088  3.2846475   3.85115539  4.03598938  4.2010115"
print "  4.38370524  4.48188875  4.78715748  4.86703817]"
print "[ 114.84184235  123.9853547   156.72186945  183.75191648  192.57098388"
print "  200.44475862  209.16170779  213.84638197  228.41180674  232.22319022]"
print '\n#TODO: replace with proper reference results'