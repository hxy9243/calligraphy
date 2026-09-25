import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from refine_strokes import corrected_decomposition, load_controls
from smooth_strokes import frame, validate


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.geometry=np.zeros((2,80,80),np.float32)
        self.geometry[0,10:70,36:44]=1
        self.geometry[0,37:44,40:56]=1  # incorrect arm on the vertical
        self.geometry[1,36:44,10:70]=1
        yy,xx=np.mgrid[:80,:80]
        self.phase=np.array([np.clip((yy-10)/59,0,1),np.clip((xx-10)/59,0,1)],np.float32)
        self.target=self.geometry.max(0)
        self.record={'points':[[40,12,4],[40,68,4]],
                     'junctions':[{'box':[30,30,60,50],'recipient':2}]}

    def test_pinned_boundary_transfers_arm_without_losing_overlap_or_ink(self):
        s=corrected_decomposition(self.geometry,self.phase,self.target,{'1':self.record},80)
        self.assertEqual(s['layers'][0,40,49],0)
        self.assertEqual(s['layers'][1,40,49],1)
        self.assertTrue((s['layers'][:,40,40]>.99).all())
        self.assertTrue((s['layers'][:,self.target==0]==0).all())
        np.testing.assert_array_equal(frame(s,2),self.target)
        self.assertEqual(validate(s)['no_new_ink_strokes'],[])

    def test_invalid_control_geometry_and_recipient_are_rejected(self):
        record={'points':[[40,12,4],[40,68,4]],
                'junctions':[{'box':[30,30,60,50],'recipient':3}]}
        with self.assertRaises(ValueError):
            corrected_decomposition(self.geometry,self.phase,self.target,{'1':record},80)
        config={'schema_version':1,'coordinate_size':80,'sheets':{'reference':{'清':{'1':{'points':[[40,12,4],[40,12,4]]}}}}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'controls.json';path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):load_controls(path)


if __name__=='__main__':unittest.main()
