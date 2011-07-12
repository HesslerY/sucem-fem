from __future__ import division

import dolfin
import numpy as np
import collections

from FenicsCode.Sources.current_source import CurrentSource
from FenicsCode.Sources.point_source import calc_pointsource_contrib
from FenicsCode.Utilities.Geometry import unit_vector, vector_length

class FillamentCurrentSource(CurrentSource):
    no_integration_points = 100

    def __init__(self, *names, **kwargs):
        self._dirty = True
        
    def set_no_integration_points(self, no_integration_points):
        """Set number of integration points to use along the length of
        the fillament"""
        self.no_integration_points = no_integration_points
    
    def set_source_endpoints(self, source_endpoints):
        """Set the current filament endpoints

        @param endpoints: 2x3 array with the coordinates of the start
        and end point of the current fillament. The conventional
        current flows from the start point towards the endpoint.
        """
        self.source_endpoints = source_endpoints
        self._dirty = True

    def set_value(self, value):
        """Set line current value in Amperes"""
        self.value = value
        self._dirty = True
        
    def _update(self):
        if self._dirty:
            self.source_start, self.source_end = self.source_endpoints
            self.source_delta = self.source_end - self.source_start
            self.vector_value = unit_vector(self.source_delta)*self.value
        self._dirty == False
            
    def get_contribution(self):
        self._update()
        source_len = vector_length(self.source_delta)
        no_pts = self.no_integration_points
        if no_pts == 1:
            intg_pts = [self.source_start + self.source_delta*0.5]
        else:
            intg_pts = self.source_start + self.source_delta*np.linspace(
                0,1,no_pts)[:, np.newaxis]

        contribs = collections.defaultdict(lambda : 0.)
        point_magnitude = self.vector_value*source_len/no_pts
        for pt in intg_pts:
            dnos, vals = calc_pointsource_contrib(
                self.function_space, pt, point_magnitude)
            for dn, v in zip(dnos, vals):
                contribs[dn] = contribs[dn] + v

        dofnos = np.array(contribs.keys(), dtype=np.uint)
        rhs_contribs = np.array(contribs.values())
        return dofnos, rhs_contribs
        
        
