import unittest
import numpy as np
from outline_strokes import fit_outline, rasterize, decompose, validate_outline, metrics
from smooth_strokes import assemble


class OutlineTests(unittest.TestCase):
    def test_closed_smooth_boundary_and_raster(self):
        layer=np.zeros((120,120),np.float32); layer[20:100,45:70]=1
        c=fit_outline(layer,4)
        np.testing.assert_allclose(c[-1,3],c[0,0])
        # Uniform spline intervals give matching Bezier first derivatives.
        np.testing.assert_allclose(c[:,3]-c[:,2],np.roll(c[:,1]-c[:,0],-1,axis=0),atol=1e-10)
        mask=rasterize(c,layer.shape)
        self.assertGreater(metrics(mask[None],layer)['silhouette_iou'],.9)
        self.assertTrue(np.isfinite(mask).all())

    def test_overlap_and_animation_are_not_source_clipped(self):
        a=np.zeros((120,120),np.float32); a[15:105,48:72]=1
        b=np.zeros_like(a); b[45:70,15:105]=1
        target=np.maximum(a,b); target[55:60,55:60]=0
        layers=np.stack([a,b])*target
        phase=np.indices(target.shape)[0]/119
        s,c=decompose(assemble(layers,np.stack([phase,phase]),target),4)
        self.assertGreater(s['layers'][:,57,57].min(),.99)
        validate_outline(s)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError): fit_outline(np.zeros((20,20)),4)


if __name__=='__main__': unittest.main()
