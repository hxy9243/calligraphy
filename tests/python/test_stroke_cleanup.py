import copy
import unittest
import numpy as np
from calligraphy.stroke_cleanup import clean_program
from calligraphy.stroke_ir import render_program, validate_program


def specimen():
    x = np.linspace(.12, .88, 64)
    top = np.full(64,.45); bottom = np.full(64,.55)
    top[31] = .33  # narrow outward spike, rather than a broad corner
    # Preserve a deliberate, broad slanted entry.
    top[:6] += np.linspace(.03,0,6)
    contacts = np.stack([np.column_stack([x,top]),np.column_stack([x,bottom])],axis=1)
    return {'schemaVersion':'kai-stroke-ir/0.2','character':'一','script':'kai',
            'provenance':{'source':'synthetic'},'relations':[],
            'strokes':[{'id':'s1','kind':'heng','duration':1,'liftAfter':.15,
                'geometry':{'type':'paired-contacts','stations':contacts.tolist(),
                            'corners':[],'tension':0.0}}]}


class SelectiveCleanupTest(unittest.TestCase):
    def test_narrow_spike_reduced_without_rounding_the_whole_stroke(self):
        source = specimen(); snapshot = copy.deepcopy(source)
        result, report = clean_program(source)
        self.assertEqual(source,snapshot)
        validate_program(result)
        before = render_program(source,1) > .5
        after = render_program(result,1) > .5
        # The extreme spike disappears, while the broad straight body survives.
        self.assertTrue(before[162:175,230:244].any())
        self.assertFalse(after[162:175,230:244].any())
        self.assertGreater((after & before).sum()/before.sum(),.95)
        self.assertTrue(after[218,160:350].all())
        self.assertFalse(report['strokes'][0]['reviewRequired'])
        self.assertLessEqual(report['strokes'][0]['radiusPx'],5)
        for k in ('id','kind','duration','liftAfter'):
            self.assertEqual(source['strokes'][0][k],result['strokes'][0][k])

    def test_deposition_and_backward_seek_use_saved_geometry_only(self):
        result,_ = clean_program(specimen())
        a=render_program(result,.2); b=render_program(result,.8); c=render_program(result,1)
        self.assertTrue(np.all(a<=b));self.assertTrue(np.all(b<=c))
        self.assertTrue(np.array_equal(a,render_program(result,.2)))
        self.assertEqual(set(result['strokes'][0]['geometry']),{'type','stations','corners','tension'})

if __name__ == '__main__':unittest.main()
