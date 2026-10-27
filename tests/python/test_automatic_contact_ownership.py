"""Behavioral regressions for shared, font-independent ownership cleanup."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from calligraphy.contact_stroke import complete_stroke
from calligraphy.automatic_contact_ownership import automatic_ownership, find_candidates


def vertical(x=80):
    return {'name': 'vertical', 'contacts': [[[x, y], [x+20, y]] for y in range(20, 201, 10)]}


def crossing():
    donor = vertical()
    donor['contacts'][8][1][0] = 130
    recipient = {'name': 'horizontal', 'contacts': [[[x, 92], [x, 108]] for x in range(85, 166, 10)]}
    return [donor, recipient]


class AutomaticOwnershipTests(unittest.TestCase):
    def test_detects_and_cleans_attached_branch_without_losing_source_ink(self):
        strokes = crossing(); saved = copy.deepcopy(strokes)
        result, report = automatic_ownership(strokes)
        self.assertGreater(report['acceptedCount'], 0)
        self.assertLess(complete_stroke(result[0]).sum(), complete_stroke(strokes[0]).sum())
        np.testing.assert_array_equal(np.maximum.reduce([complete_stroke(s) for s in strokes]),
                                      np.maximum.reduce([complete_stroke(s) for s in result]))
        self.assertEqual(strokes, saved)
        self.assertEqual(result[0]['contacts'], strokes[0]['contacts'])

    def test_shared_preparation_applies_to_any_registered_font_and_caches(self):
        from calligraphy.contact_preparation import prepare_contacts
        for font in ['thin-font', 'thick-font']:
            with self.subTest(font=font), tempfile.TemporaryDirectory() as directory, patch(
                    'calligraphy.contact_preparation.smooth_kai_contacts',
                    return_value=(crossing(), {})) as smooth:
                kwargs = {'source': {'font': {'sha256': font}}, 'inferred_corners': True,
                          'cache_path': Path(directory)/'contacts.db'}
                cold = prepare_contacts({'字': crossing()}, **kwargs)
                warm = prepare_contacts({'字': crossing()}, **kwargs)
                self.assertGreater(cold[1]['字']['automaticOwnership']['acceptedCount'], 0)
                self.assertEqual(cold, warm)
                self.assertEqual(smooth.call_count, 1)

    def test_early_floating_transfer_is_rejected(self):
        strokes = [vertical(200), vertical(80)]
        envelope = vertical(84)
        proposal = {'donor': 1, 'owner': 0, 'cut': [0, 2, 5], 'pixels': 500,
                    'ownerMargin': 10., 'meanOwnerDistance': 5., 'envelope': envelope}
        with patch('calligraphy.automatic_contact_ownership.find_candidates', return_value=[proposal]):
            result, report = automatic_ownership(strokes)
        self.assertEqual(result, strokes)
        self.assertEqual(report['acceptedCount'], 0)
        self.assertEqual(report['edits'][0]['reason'], 'new-detached-ink')

    def test_existing_and_overlapping_ownership_is_not_overwritten(self):
        strokes = crossing()
        proposals = find_candidates(strokes)
        self.assertTrue(proposals)
        with patch('calligraphy.automatic_contact_ownership.find_candidates', return_value=proposals*2):
            result, report = automatic_ownership(strokes)
        self.assertEqual(report['acceptedCount'], 1)
        self.assertTrue(any(e.get('reason') == 'stroke-already-corrected' for e in report['edits']))
        again, repeat = automatic_ownership(result)
        self.assertEqual(again, result)
        self.assertEqual(repeat['acceptedCount'], 0)

    def test_single_stroke_and_terminals_are_unchanged(self):
        source = [vertical()]
        result, report = automatic_ownership(source)
        self.assertEqual(result, source)
        self.assertEqual(report['acceptedCount'], 0)
        strokes = crossing()
        strokes[0] = vertical()
        strokes[0]['contacts'][0][1][0] += 30
        self.assertFalse(find_candidates(strokes))

    def test_disjoint_corrections_are_validated_as_one_combined_glyph(self):
        strokes = crossing()
        extra = copy.deepcopy(strokes)
        for stroke in extra:
            stroke['contacts'] = (np.asarray(stroke['contacts']) + [190, 190]).tolist()
        source = strokes + extra
        result, report = automatic_ownership(source)
        self.assertEqual(report['acceptedCount'], 2)
        self.assertEqual(len(result), len(source))
        np.testing.assert_array_equal(np.maximum.reduce([complete_stroke(s) for s in source]),
                                      np.maximum.reduce([complete_stroke(s) for s in result]))

    def test_ambiguous_owner_is_not_guessed(self):
        strokes = crossing()
        strokes.append(copy.deepcopy(strokes[1]))
        self.assertFalse(find_candidates(strokes))

    def test_authored_contacts_do_not_opt_in(self):
        from calligraphy.contact_preparation import prepare_contacts
        with tempfile.TemporaryDirectory() as directory, patch(
                'calligraphy.contact_preparation.smooth_kai_contacts', return_value=(crossing(), {})), patch(
                'calligraphy.contact_preparation.automatic_ownership') as automatic:
            prepare_contacts({'字': crossing()}, source={'kind': 'built-in'},
                             cache_path=Path(directory)/'contacts.db')
            automatic.assert_not_called()
