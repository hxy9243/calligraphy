import unittest
import numpy as np
from stroke_layers import compose_layers


class CrossingTest(unittest.TestCase):
    def setUp(self):
        self.support=np.zeros((2,9,9),bool)
        self.support[0,4,1:8]=True
        self.support[1,1:8,4]=True
        self.progress=np.zeros((2,9,9),np.float32)
        self.progress[0]=np.linspace(0,1,9)[None,:]
        self.progress[1]=np.linspace(0,1,9)[:,None]

    def test_crossing_retained_without_future_arms(self):
        ink=self.support.any(0)
        layers,exposure,owner=compose_layers(self.support,self.progress,ink)
        self.assertTrue(layers[:,4,4].all())
        # Horizontal stroke has reached the center, but vertical has not begun.
        frame=exposure<=.6
        self.assertTrue(frame[4,4])
        self.assertFalse(frame[:4,4].any())
        self.assertFalse(frame[5:,4].any())
        np.testing.assert_array_equal(exposure<=2,ink)
        self.assertEqual(owner[4,4],0)

    def test_outside_ink_is_not_backfilled(self):
        ink=self.support.any(0);ink[0,0]=True
        _,exposure,owner=compose_layers(self.support,self.progress,ink)
        self.assertTrue(np.isinf(exposure[0,0]))
        self.assertEqual(owner[0,0],-1)

    def test_first_arrival_matches_layer_compositing(self):
        layers,exposure,_=compose_layers(self.support,self.progress,self.support.any(0))
        for t in np.linspace(0,2,30):
            expected=np.maximum.reduce([layer*np.clip((t-i-self.progress[i]*.88)/.09,0,1) for i,layer in enumerate(layers)])
            actual=np.clip((t-exposure)/.09,0,1)
            np.testing.assert_allclose(actual,expected,atol=2e-6)


if __name__=='__main__':unittest.main()
