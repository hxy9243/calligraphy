import copy
import unittest
import numpy as np
from calligraphy.contact_stroke import ContactStroke, complete_stroke


def line(x):
    return {'name': 'line', 'contacts': [[[x, 30], [x+10, 30]], [[x, 60], [x+10, 60]], [[x, 90], [x+10, 90]]]}


class ContactOwnershipTests(unittest.TestCase):
    def test_clip_and_reassigned_ink_follow_owner_progress(self):
        donor, owner = line(30), line(100)
        original = complete_stroke(donor)
        index = 50 * 480 + 35
        self.assertGreater(original.flat[index], .5)
        donor['ownership'] = {'clip': [[index, 0.]], 'patches': []}
        owner['ownership'] = {'clip': [], 'patches': [[index, float(original.flat[index]), .6]]}
        saved = copy.deepcopy([donor, owner])
        self.assertEqual(complete_stroke(donor).flat[index], 0)
        painter = ContactStroke(owner)
        self.assertEqual(painter.advance(.5).flat[index], 0)
        self.assertEqual(painter.advance(.7).flat[index], original.flat[index])
        np.testing.assert_array_equal(np.maximum(original, complete_stroke(line(100))),
                                      np.maximum(complete_stroke(donor), complete_stroke(owner)))
        self.assertEqual([donor, owner], saved)

    def test_invalid_ownership_rejected(self):
        for patch in [[-1, 1, .5], [480*480, 1, .5], [0, 2, .5], [0, 1, float('nan')], [0, 1, -1]]:
            stroke=line(30);stroke['ownership']={'patches':[patch]}
            with self.assertRaises(ValueError): ContactStroke(stroke)

    def test_transfer_preserves_alpha_metadata_segments_and_motion(self):
        from calligraphy.contact_ownership import transfer_ownership
        donor = line(30)
        owner = {'name': 'owner', 'custom': {'provenance': 'fixture'}, 'segments': [
            {'start': .3, 'end': .8, 'stroke': line(100)}]}
        envelope = line(32)
        source = [donor, owner]; saved = copy.deepcopy(source)
        result, report = transfer_ownership(source, 0, [1], envelope)
        self.assertEqual(source, saved)
        self.assertEqual(result[1]['segments'], owner['segments'])
        self.assertEqual(result[1]['custom'], owner['custom'])
        self.assertTrue(report['finalAlphaEqual'])
        self.assertGreater(report['movedPixels'], 0)
        np.testing.assert_array_equal(np.maximum.reduce([complete_stroke(s) for s in source]),
                                      np.maximum.reduce([complete_stroke(s) for s in result]))
        for stroke in result:
            painter=ContactStroke(stroke); previous=np.zeros((480,480),np.float32)
            for progress in np.linspace(0,1,65):
                current=painter.advance(float(progress))
                self.assertTrue(np.all(current>=previous));previous=current
            np.testing.assert_array_equal(previous,complete_stroke(stroke))
        self.assertTrue(all(p[2]>=.3 for p in result[1]['ownership']['patches']))

    def test_review_rejects_unmatched_font_and_changed_geometry(self):
        from calligraphy.contact_ownership import apply_reviewed_ownership, FONT_SHA256
        strokes=[line(30)]
        unchanged,report=apply_reviewed_ownership('月',strokes,strokes,{'font':{'sha256':'other'}})
        self.assertIs(unchanged,strokes);self.assertIsNone(report)
        unchanged,report=apply_reviewed_ownership('月',strokes,strokes,{'font':{'sha256':FONT_SHA256}})
        self.assertIs(unchanged,strokes);self.assertEqual(report['status'],'skipped')
        unchanged,report=apply_reviewed_ownership('人',strokes,strokes,{'font':{'sha256':FONT_SHA256}})
        self.assertIs(unchanged,strokes);self.assertIsNone(report)

    def test_preparation_applies_review_and_round_trips_cache(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from calligraphy.contact_ownership import FONT_SHA256, geometry_digest
        from calligraphy.contact_preparation import prepare_contacts
        donor = line(30)
        donor['contacts'][1][0][0] = 10
        glyphs = {'月': [donor, line(100)]}
        saved = copy.deepcopy(glyphs)
        review = {'source': geometry_digest(glyphs['月']),
                  'prepared': geometry_digest(glyphs['月']), 'donor': 0,
                  'owners': [1], 'cuts': [(0, 0, 2)]}
        with tempfile.TemporaryDirectory() as directory, patch(
                'calligraphy.contact_ownership.REVIEWS', {'月': review}), patch(
                'calligraphy.contact_preparation.smooth_kai_contacts',
                return_value=(copy.deepcopy(glyphs['月']), {})) as smooth:
            kwargs = {'source': {'font': {'sha256': FONT_SHA256}},
                      'inferred_corners': True, 'cache_path': Path(directory)/'contacts.db'}
            cold = prepare_contacts(glyphs, **kwargs)
            warm = prepare_contacts(glyphs, **kwargs)
            self.assertEqual(cold, warm)
            self.assertEqual(smooth.call_count, 1)
            self.assertEqual(cold[1]['月']['reviewedOwnership']['status'], 'applied')
            self.assertGreater(cold[1]['月']['reviewedOwnership']['movedPixels'], 0)
            self.assertEqual(glyphs, saved)
            np.testing.assert_array_equal(
                np.maximum.reduce([complete_stroke(s) for s in glyphs['月']]),
                np.maximum.reduce([complete_stroke(s) for s in cold[0]['月']]))
