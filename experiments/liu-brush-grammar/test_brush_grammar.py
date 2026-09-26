"""Behavior checks for complete geometry and irreversible stroke deposition."""
from pathlib import Path
import json,unittest
import cv2
import numpy as np
from brush_grammar import ContactBrush,complete,sample,validate
ROOT=Path(__file__).resolve().parent

class BrushGrammarTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.controls=json.loads((ROOT/'fitted-controls.json').read_text())
 def test_accumulation_is_monotonic_and_independent_of_frame_rate(self):
  for strokes in self.controls.values():
   for stroke in strokes:
    painter=ContactBrush(stroke);previous=painter.advance(0)
    self.assertFalse(previous.any())
    for t in [.07,.13,.28,.47,.61,.84,1.]:
     current=painter.advance(t);self.assertTrue(np.all(current>=previous));previous=current
    np.testing.assert_array_equal(previous,complete(stroke))
    with self.assertRaises(ValueError):painter.advance(.5)
 def test_each_stroke_is_connected_and_tips_stay_closed(self):
  authored=json.loads((ROOT/'controls.json').read_text())
  for char,strokes in self.controls.items():
   for s,original in zip(strokes,authored[char]):
    ink=complete(s);n,_=cv2.connectedComponents((ink>.5).astype(np.uint8));self.assertEqual(n,2,s['name'])
    a=np.array(original['contacts']);b=np.array(s['contacts']);tips=np.linalg.norm(a[:,0]-a[:,1],axis=1)<1e-6
    np.testing.assert_allclose(b[tips,0],b[tips,1],atol=1e-6)
    self.assertLessEqual(np.abs(a-b).max(),7.00001)
 def test_square_shoulder_exists_before_downstroke_and_future_arm_hidden(self):
  s=self.controls['月'][1];rails,times=sample(s)
  p=ContactBrush(s);ink=p.advance(times[5*16])
  self.assertGreater(ink[50:75,333:355].sum(),100)
  self.assertEqual(ink[200:300].sum(),0)
  final=p.advance(1);self.assertGreater(final[240,345],.99)
 def test_crossing_strokes_overlap_without_leaking_future_arm(self):
  strokes=self.controls['千'];horizontal=complete(strokes[1]);vertical=complete(strokes[2])
  self.assertGreater(np.minimum(horizontal,vertical).sum(),500)
  self.assertEqual(horizontal[300:400,235:255].sum(),0)
  self.assertGreater(vertical[300:340,235:255].mean(),.99)
 def test_invalid_contacts_rejected(self):
  for contacts in [[],[[[1,1],[2,2]]]*3,[[[float('nan'),1],[2,2]]]*3]:
   with self.assertRaises(ValueError):validate({'contacts':contacts})

if __name__=='__main__':unittest.main()
