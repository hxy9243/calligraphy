import copy
import unittest
import numpy as np
from calligraphy.stroke_crossings import smooth_kai_program
from calligraphy.stroke_ir import render_program


def specimen():
    a=np.array([[[x,220.],[x,250.]] for x in np.linspace(60,420,37)])
    a[(a[:,0,0]>=196)&(a[:,0,0]<=224),1,1]-=13
    b=np.array([[[195.,y],[225.,y]] for y in np.linspace(160,320,37)])
    strokes=[]
    for i,c in enumerate([a,b]):
        c[0]=c[0].mean(axis=0);c[-1]=c[-1].mean(axis=0)
        strokes.append({'id':f's{i}', 'kind':'unclassified','duration':i+1,'liftAfter':.1,
                        'geometry':{'type':'paired-contacts','stations':(c/480).tolist(),
                                    'corners':[], 'tension':.5}})
    return {'schemaVersion':'kai-stroke-ir/0.2','character':'十','script':'kai',
            'provenance':{'source':'synthetic'},'strokes':strokes,
            'relations':[{'kind':'cross','a':'s0','b':'s1'}]}


class CrossingTests(unittest.TestCase):
    def test_hidden_dent_and_program_contract(self):
        old=specimen();snapshot=copy.deepcopy(old);new,report=smooth_kai_program(old)
        self.assertEqual(old,snapshot);self.assertTrue(report['accepted'])
        self.assertTrue(report['strokes'][0]['changed'])
        self.assertEqual(old['relations'],new['relations'])
        for a,b in zip(old['strokes'],new['strokes']):
            for k in ('id','kind','duration','liftAfter'):self.assertEqual(a[k],b[k])
            np.testing.assert_array_equal(np.array(a['geometry']['stations'])[[0,1,-2,-1]],
                                          np.array(b['geometry']['stations'])[[0,1,-2,-1]])
        single=lambda p:{**p,'strokes':[p['strokes'][0]],'relations':[]}
        self.assertLess(render_program(single(old),1)[244,210],.1)
        self.assertGreater(render_program(single(new),1)[244,210],.9)
        frames=[render_program(new,t) for t in (0,.2,.5,.8,1)]
        self.assertTrue(all(np.all(a<=b) for a,b in zip(frames,frames[1:])))
        np.testing.assert_array_equal(frames[1],render_program(new,.2))

    def test_authored_corner_preserved(self):
        old=specimen();old['strokes'][0]['geometry']['corners']=[15]
        new,_=smooth_kai_program(old)
        self.assertEqual(old['strokes'][0]['geometry'],new['strokes'][0]['geometry'])

    def test_single_stroke_unchanged(self):
        old=specimen();old['strokes']=old['strokes'][:1];old['relations']=[]
        new,_=smooth_kai_program(old)
        self.assertEqual(old['strokes'],new['strokes'])

    def test_target_fit_gate_reverts_whole_proposal(self):
        old=specimen();new,report=smooth_kai_program(old,targets=[np.zeros((480,480))]*2)
        self.assertFalse(report['accepted']);self.assertEqual(old['strokes'],new['strokes'])
        self.assertEqual(report['reason'],'original-target-fit')


class CornerMotionTests(unittest.TestCase):
    def test_terminal_diagnostic_rebases_authored_corners(self):
        from calligraphy.stroke_fitting import _motion_checks
        from calligraphy.stroke_ir import compile_program
        p = specimen()
        p['strokes'][0]['geometry']['corners'] = [3, 34]
        report = _motion_checks(compile_program(p)[0])
        self.assertTrue(report['monotonic'])
        self.assertEqual(report['prefixFrames'], 31)


class InferredGeometryTests(unittest.TestCase):
    def test_inferred_crossing_corner_is_repaired_but_authored_one_is_not(self):
        from calligraphy.stroke_crossings import repair_crossings
        from calligraphy.stroke_ir import compile_program
        p = specimen()
        p['strokes'][0]['geometry']['corners'] = [15]
        records = compile_program(p)
        protected, _ = repair_crossings(records, preserve_corners=True)
        repaired, _ = repair_crossings(records, preserve_corners=True, inferred_corners=True)
        self.assertEqual(protected[0]['contacts'], records[0]['contacts'])
        self.assertNotEqual(repaired[0]['contacts'], records[0]['contacts'])
        self.assertNotIn(15, repaired[0]['corners'])

    def test_tiny_segment_removed_without_deleting_real_disconnected_piece(self):
        from calligraphy.stroke_crossings import smooth_kai_contacts
        from calligraphy.stroke_ir import compile_program
        main = compile_program(specimen())[0]
        def piece(width):
            return {'contacts': [[[x,80],[x,80+width]] for x in (100,104,108)],
                    'corners': [], 'tension': 0}
        tiny, substantial = piece(1), piece(35)
        stroke = {'segments': [{'start': 0, 'end': .8, 'stroke': main},
                               {'start': .8, 'end': .9, 'stroke': tiny},
                               {'start': .9, 'end': 1, 'stroke': substantial}]}
        result, report = smooth_kai_contacts([stroke], inferred_corners=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['segments']), 2)
        self.assertEqual(result[0]['segments'][1], stroke['segments'][2])
        self.assertEqual(len(report['removedSatellites']), 1)
        # A small complete stroke must never be treated as a satellite.
        dot, dot_report = smooth_kai_contacts([tiny], inferred_corners=True)
        self.assertEqual(dot, [tiny])
        self.assertEqual(dot_report['removedSatellites'], [])
