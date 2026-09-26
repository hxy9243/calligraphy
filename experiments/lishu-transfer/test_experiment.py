"""Regression checks for the new shared affine mask/progress mapping."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from experiment import S, fit_template, extract_cells, compose_layers


class AspectFitTests(unittest.TestCase):
    def test_flattened_cross_keeps_overlap_and_future_vertical_arm_hidden(self):
        layers = np.zeros((2,S,S),np.float32)
        layers[0,77:83,30:130] = 1
        layers[1,30:130,77:83] = 1
        yy,xx = np.mgrid[:S,:S]
        phase = np.stack([np.clip((xx-30)/99,0,1),np.clip((yy-30)/99,0,1)]).astype(np.float32)
        target = np.zeros((S,S),bool)
        target[60:100,10:150] = True
        fitted,progress = fit_template(layers,phase,target)
        membership,exposure,owner = compose_layers(fitted>.5,progress,target)
        self.assertTrue(membership[:,80,80].all())
        self.assertEqual(owner[80,80],0)
        self.assertEqual(owner[95,80],1)
        self.assertGreater(exposure[95,80],1)
        self.assertLess(exposure[80,30],exposure[80,120])
        self.assertLess(exposure[65,80],exposure[95,80])
        self.assertEqual(owner[61,11],-1)

    def test_sheet_cut_moves_to_whitespace_without_clipping(self):
        sheet=np.full((400,1000),255,np.uint8)
        for row in range(2):
            for col in range(5):
                left=col*200+20
                if col==2:
                    left=395  # crosses nominal x=400 boundary
                sheet[row*200+60:row*200+130,left:col*200+175]=0
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sheet.png';Image.fromarray(sheet).save(path)
            glyphs=extract_cells(path)
        self.assertEqual(glyphs.shape,(10,S,S))
        self.assertTrue(all((g<150).any() for g in glyphs))
        self.assertFalse((glyphs[:,0]<150).any())


if __name__=='__main__':
    unittest.main()
