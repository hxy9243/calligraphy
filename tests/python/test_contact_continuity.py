import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from calligraphy.contact_continuity import interior_gaps, preserve_final_ink, repair_contact_continuity
from calligraphy.contact_preparation import prepare_contacts
from calligraphy.contact_stroke import ContactStroke, complete_stroke


def bar(x=100):
    return {'contacts': [[[x,100],[x,100]], [[x,140],[x+12,140]],
                         [[x,180],[x+12,180]], [[x,220],[x,220]]],
            'corners': [], 'features': [], 'tension': .5}


def union(strokes):
    return np.maximum.reduce([complete_stroke(s) for s in strokes])


class ContactContinuityTests(unittest.TestCase):
    def test_only_large_interior_segment_gaps_nominate_a_refit(self):
        def segments(intervals):
            return {'segments':[{'start':a,'end':b,'stroke':bar()} for a,b in intervals]}
        strokes=[segments([(0,.25),(.76,1)]), segments([(0,.5),(.4,1)]),
                 segments([(0,.5),(.65,1)]),segments([(0,.05),(.5,1)]),bar()]
        self.assertEqual(interior_gaps(strokes),[0])
        original=copy.deepcopy(strokes)
        actual,report=repair_contact_continuity('風',strokes,strokes,None)
        self.assertIs(actual,strokes)
        self.assertIsNone(report)
        self.assertEqual(strokes,original)

    def test_projection_composes_ownership_and_keeps_exact_monotonic_alpha(self):
        stroke=bar()
        existing=140*480+112
        stroke['ownership']={'clip':[[150*480+106,.3]],'patches':[[existing,.4,.05]]}
        original=copy.deepcopy(stroke)
        target=complete_stroke(stroke).copy()
        target[140,112]=.8
        target[150,106]=.2
        target[160,113]=.6
        result=preserve_final_ink([stroke],target)
        self.assertEqual(stroke,original)
        np.testing.assert_array_equal(union(result),target)
        patches={row[0]:row[1:] for row in result[0]['ownership']['patches']}
        self.assertLessEqual(patches[existing][1],.05)
        painter=ContactStroke(result[0]); previous=np.zeros_like(target)
        for t in np.linspace(0,1,65):
            current=painter.advance(float(t))
            self.assertTrue(np.all(current>=previous))
            previous=current.copy()
        np.testing.assert_array_equal(previous,target)

    def test_projection_rejects_invalid_target_or_empty_support(self):
        for target in [np.zeros((10,10)),np.full((480,480),np.nan),np.full((480,480),2.)]:
            with self.subTest(shape=target.shape),self.assertRaises(ValueError):
                preserve_final_ink([bar()],target)
        with self.assertRaises(ValueError):
            preserve_final_ink([],np.zeros((480,480),np.float32))
        invisible=bar();invisible['contacts']=[[[100,100],[100,100]],[[100,150],[100,150]],[[100,200],[100,200]]]
        target=np.ones((480,480),np.float32)
        # Explicitly simulate no source ink; there is no arrival time to borrow.
        with patch('calligraphy.contact_continuity.complete_stroke',return_value=np.zeros_like(target)),self.assertRaises(ValueError):
            preserve_final_ink([invisible],target)

    def test_failed_or_unrelated_refit_returns_original_unchanged(self):
        strokes=[{'segments':[{'start':0,'end':.25,'stroke':bar()},
                              {'start':.76,'end':1,'stroke':bar(150)}]}]
        original=copy.deepcopy(strokes)
        with patch('calligraphy.contact_continuity.registered_fields',side_effect=ValueError('unavailable')):
            result,report=repair_contact_continuity('風',strokes,strokes,{})
        self.assertIs(result,strokes);self.assertEqual(report['reason'],'refit-unavailable')
        def unrelated(*args,diagnostics,**kwargs):diagnostics['collapsed_intervals']=[]
        with patch('calligraphy.contact_continuity.registered_fields',side_effect=unrelated):
            result,report=repair_contact_continuity('風',strokes,strokes,{})
        self.assertIs(result,strokes);self.assertEqual(report['reason'],'unrelated-registration-collapse')
        self.assertEqual(strokes,original)

    def test_unresolved_or_low_retention_candidate_is_rejected(self):
        strokes=[{'segments':[{'start':0,'end':.25,'stroke':bar()},
                              {'start':.76,'end':1,'stroke':bar(150)}]}]
        original=copy.deepcopy(strokes)
        def registration(*args, diagnostics, tightness=.3, **kwargs):
            diagnostics['collapsed_intervals'] = [[0,4,8]] if tightness < 2 else []
        for fitted,reason in [(strokes,'unresolved-interior-gap'),([bar()],'shape-retention-guard')]:
            with self.subTest(reason=reason), \
                 patch('calligraphy.contact_continuity.registered_fields',side_effect=registration), \
                 patch('calligraphy.contact_continuity.fit_glyph',return_value=(fitted,{})), \
                 patch('calligraphy.contact_continuity.smooth_kai_contacts',side_effect=lambda s,**kwargs:(s,{})):
                result,report=repair_contact_continuity('風',strokes,strokes,{})
            self.assertIs(result,strokes)
            self.assertEqual(report['reason'],reason)
        self.assertEqual(strokes,original)

    def test_existing_ownership_is_never_refitted(self):
        source=[{'segments':[{'start':0,'end':.25,'stroke':bar()},
                             {'start':.76,'end':1,'stroke':bar(150)}]}]
        for ownership in [{'clip':[[140*480+106,.2]]},
                          {'patches':[[140*480+106,.8,.1]]}]:
            prepared=copy.deepcopy(source)
            prepared[0]['ownership']=ownership
            original=copy.deepcopy(prepared)
            with self.subTest(ownership=ownership), \
                 patch('calligraphy.contact_continuity.registered_fields',side_effect=AssertionError('must not refit')):
                result,report=repair_contact_continuity('風',source,prepared,{})
            self.assertIs(result,prepared)
            self.assertEqual(report['reason'],'existing-ownership-correction')
            self.assertEqual(prepared,original)
            self.assertNotIn('ownership',source[0])

    def test_ambiguous_refit_cannot_silently_add_a_fallback_warning(self):
        strokes=[{'segments':[{'start':0,'end':.25,'stroke':bar()},
                              {'start':.76,'end':1,'stroke':bar(150)}]}]
        original=copy.deepcopy(strokes)
        def registration(*args, diagnostics, tightness=.3, **kwargs):
            diagnostics['collapsed_intervals'] = [[0,4,8]] if tightness < 2 else []
        for metrics in [{'guide_fallback_strokes':[1]}, {'review_required':True},
                        {'guide_fallback_strokes':[1],'review_required':True}]:
            with self.subTest(metrics=metrics), \
                 patch('calligraphy.contact_continuity.registered_fields',side_effect=registration), \
                 patch('calligraphy.contact_continuity.fit_glyph',return_value=([bar()],metrics)), \
                 patch('calligraphy.contact_continuity.smooth_kai_contacts',side_effect=AssertionError('must reject first')):
                result,report=repair_contact_continuity('風',strokes,strokes,{})
            self.assertIs(result,strokes)
            self.assertEqual(report['reason'],'ambiguous-refit')
            self.assertEqual(strokes,original)


class LegacyFontContinuityTests(unittest.TestCase):
    def test_existing_bank_repairs_once_preserving_cache_source_and_final_pixels(self):
        fixture=Path(__file__).parent/'fixtures/masa-wind-legacy.json'
        original=fixture.read_bytes(); data=json.loads(original)
        source=copy.deepcopy(data['glyphs'])
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'derived.db'
            before,_=prepare_contacts(source,source=data['source'],inferred_corners=True,cache_path=cache)
            after,reports=prepare_contacts(source,source=data['source'],inferred_corners=True,
                                          cache_path=cache,templates=data['templates'])
            report=reports['風']['continuityRepair']
            self.assertEqual(report['status'],'applied')
            self.assertTrue(report['finalAlphaEqual'])
            self.assertGreaterEqual(report['glyphRetentionIoU'],.95)
            np.testing.assert_array_equal(union(before['風']),union(after['風']))
            self.assertIn(1,interior_gaps(source['風']))
            self.assertNotIn(1,interior_gaps(after['風']))
            # The former later-owned vertical is now in the second stroke.
            self.assertLess(complete_stroke(before['風'][1])[210,249],.1)
            self.assertGreater(complete_stroke(after['風'][1])[210,249],.9)
            painter=ContactStroke(after['風'][1]); previous=np.zeros((480,480),np.float32)
            for t in np.linspace(0,1,65):
                current=painter.advance(float(t))
                self.assertTrue(np.all(current>=previous))
                previous=current.copy()
            np.testing.assert_array_equal(previous,complete_stroke(after['風'][1]))
            with patch('calligraphy.contact_preparation.repair_contact_continuity',side_effect=AssertionError('cache miss')):
                again,again_reports=prepare_contacts(source,source=data['source'],inferred_corners=True,
                                                    cache_path=cache,templates=data['templates'])
            self.assertEqual(after,again);self.assertEqual(reports,again_reports)
        self.assertEqual(source,data['glyphs'])
        self.assertEqual(fixture.read_bytes(),original)
