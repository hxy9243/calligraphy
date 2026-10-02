import copy
import unittest
import numpy as np
from calligraphy.stroke_fairing import fair_values, fair_program, turn_landmarks
from calligraphy.stroke_ir import validate_program
from pathlib import Path
import json

class FairingTests(unittest.TestCase):
    def test_affine_and_exact_landmarks(self):
        values = np.column_stack([np.linspace(0,1,12),np.linspace(1,2,12)])
        np.testing.assert_allclose(fair_values(values,4,[0,11]), values,atol=1e-12)
        noisy=values.copy();noisy[5,1]+=.25
        result=fair_values(noisy,4,[0,5,11])
        np.testing.assert_array_equal(result[[0,5,11]],noisy[[0,5,11]])
        self.assertLess(np.sum(np.diff(result,n=2,axis=0)**2),np.sum(np.diff(noisy,n=2,axis=0)**2))

    def test_invalid_strength(self):
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):fair_values(np.arange(5),value,[0,4])

    def test_turn_landmark_is_fixed(self):
        centers=np.array([[.1,.2],[.2,.2],[.3,.2],[.4,.2],[.4,.3],[.4,.4],[.4,.5]])
        contacts=np.stack([centers+[.01,0],centers-[.01,0]],axis=1)
        fixed=turn_landmarks(contacts,[[.1,.2],[.4,.2],[.4,.5]])
        self.assertTrue({2,3,4}.issubset(fixed))

    def test_public_replay_contract_and_copy(self):
        root=Path(__file__).resolve().parents[2]
        bank=json.loads((root/'examples/kai-stroke-ir/fixtures/32-glyph-bank.json').read_text())
        program=bank['glyphs'][0]['program']
        original=copy.deepcopy(program)
        guides=[np.asarray(s['geometry']['stations']).mean(axis=1).tolist() for s in program['strokes']]
        for mode in ('rails','motion'):
            result=fair_program(program,guides,mode=mode,strength=1)
            validate_program(result)
            self.assertEqual(result['relations'],program['relations'])
            for a,b in zip(program['strokes'],result['strokes']):
                self.assertEqual(a['id'],b['id'])
                np.testing.assert_array_equal(np.asarray(a['geometry']['stations'])[[0,1,-2,-1]],np.asarray(b['geometry']['stations'])[[0,1,-2,-1]])
        self.assertEqual(program,original)

if __name__=='__main__':unittest.main()
