import unittest
import numpy as np
from smooth_strokes import smooth_decomposition, assemble, frame, validate


class SmoothStrokeTests(unittest.TestCase):
    def setUp(self):
        self.warped=np.zeros((2,80,80),np.float32)
        self.warped[0,36:44,10:70]=1
        self.warped[1,10:70,36:44]=1
        yy,xx=np.mgrid[:80,:80]
        self.phase=np.array([np.clip((xx-10)/59,0,1),np.clip((yy-10)/59,0,1)],np.float32)
        self.target=self.warped.max(0)

    def test_shared_cross_has_full_coverage_and_hides_future_arms(self):
        layers,phase,alpha=smooth_decomposition(self.warped,self.phase,self.target)
        s=assemble(layers,phase,self.target)
        self.assertGreater(layers[0,40,40],.9)
        self.assertGreater(layers[1,40,40],.9)
        self.assertEqual(frame(s,1)[15,40],0)
        self.assertEqual(frame(s,1)[65,40],0)
        np.testing.assert_array_equal(frame(s,2),self.target)
        self.assertEqual(validate(s)['no_new_ink_strokes'],[])

    def test_missing_support_ink_is_reconstructed_inside_layers_only(self):
        self.target[35:45,70:74]=.7
        layers,phase,_=smooth_decomposition(self.warped,self.phase,self.target)
        np.testing.assert_array_equal(layers.max(0),self.target)
        self.assertTrue((layers[:,self.target==0]==0).all())
        s=assemble(layers,phase,self.target)
        self.assertLess(np.abs(frame(s,2)-frame(s,2-1e-5)).max(),1e-6)

    def test_reject_invalid_or_missing_stroke_geometry(self):
        with self.assertRaises(ValueError):
            smooth_decomposition(self.warped,self.phase,self.target,feather=0)
        self.warped[1]=0
        with self.assertRaises(ValueError):
            smooth_decomposition(self.warped,self.phase,self.target)


if __name__=='__main__':
    unittest.main()
