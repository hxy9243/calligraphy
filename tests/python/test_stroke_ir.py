import copy
import json
import unittest

import numpy as np

from calligraphy.brush_grammar import ContactBrush
from calligraphy.stroke_ir import compile_program, render_program, validate_program


def line(a, b):
    return [a, [a[0] * 2 / 3 + b[0] / 3, a[1] * 2 / 3 + b[1] / 3],
            [a[0] / 3 + b[0] * 2 / 3, a[1] / 3 + b[1] * 2 / 3], b]


def glyph():
    return {
        "schemaVersion": "kai-stroke-ir/0.1",
        "character": "永",
        "script": "kai",
        "provenance": {"source": "unit-test", "inferred": True},
        "strokes": [
            {
                "id": "horizontal",
                "kind": "heng",
                "path": [line([0.15, 0.5], [0.85, 0.5])],
                "profile": [
                    {"s": 0, "left": 0.015, "right": 0.035, "angle": 0},
                    {"s": 1, "left": 0.035, "right": 0.015, "angle": 0},
                ],
                "corners": [],
                "duration": 1,
                "liftAfter": 0.25,
            },
            {
                "id": "turn",
                "kind": "zhe",
                "path": [line([0.5, 0.2], [0.5, 0.5]), line([0.5, 0.5], [0.8, 0.5])],
                "profile": [
                    {"s": 0, "left": 0.025, "right": 0.025},
                    {"s": 0.5, "left": 0.045, "right": 0.045},
                    {"s": 1, "left": 0, "right": 0},
                ],
                "corners": [0.5],
                "duration": 2,
                "liftAfter": 0.15,
            },
        ],
        "relations": [{"kind": "cross", "a": "horizontal", "b": "turn"}],
    }


class StrokeIRTests(unittest.TestCase):
    def test_json_roundtrip_and_compile_to_contact_records(self):
        program = json.loads(json.dumps(glyph()))
        self.assertIs(validate_program(program), program)
        records = compile_program(program)
        self.assertEqual(json.dumps(records, sort_keys=True), json.dumps(compile_program(program), sort_keys=True))
        self.assertEqual(len(records), 2)
        self.assertEqual(len(records[1]["corners"]), 1)
        self.assertNotEqual(records[0]["contacts"][0][0], records[0]["contacts"][0][1])
        self.assertGreater(ContactBrush(records[0]).advance(1).sum(), 0)

    def test_malformed_data_names_glyph_and_stroke(self):
        cases = []
        bad = glyph(); bad["strokes"][0]["path"][0][0][0] = 2; cases.append(bad)
        bad = glyph(); bad["strokes"][0]["profile"][0]["s"] = 0.1; cases.append(bad)
        bad = glyph(); bad["relations"][0]["b"] = "missing"; cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "glyph '永'"):
                validate_program(bad)
        with self.assertRaisesRegex(ValueError, "horizontal"):
            validate_program(cases[0])

    def test_malformed_json_values_raise_contextual_value_errors(self):
        mutations = [
            lambda p: p["relations"][0].update(kind=[]),
            lambda p: p["relations"][0].update(a={"not": "an id"}),
            lambda p: p["strokes"][0]["profile"][0].update(left=1e300),
            lambda p: p["strokes"][0].update(path=[[[0.2, 0.2]] * 4]),
            lambda p: [s.update(duration=1e308, liftAfter=1e308) for s in p["strokes"]],
        ]
        for mutate in mutations:
            program = glyph()
            mutate(program)
            with self.subTest(program=program), self.assertRaisesRegex(ValueError, "glyph '永'"):
                validate_program(program)

    def test_crossing_does_not_reveal_future_arm(self):
        program = glyph()
        self.assertFalse(render_program(program, 0).any())
        # Halfway through stroke one, the later vertical/turn stroke is absent.
        frame = render_program(program, 0.5 / 3.4)
        self.assertGreater(frame[240, 120:240].sum(), 0)
        self.assertEqual(frame[80:200, 240].sum(), 0)

    def test_lift_interval_adds_no_deposition(self):
        program = glyph()
        total = 3.4
        end_first = render_program(program, 1 / total)
        during_lift = render_program(program, 1.2 / total)
        np.testing.assert_array_equal(end_first, during_lift)

    def test_multi_segment_turn_is_one_continuous_record(self):
        record = compile_program(glyph())[1]
        self.assertEqual(len(record["corners"]), 1)
        corner = record["corners"][0]
        contacts = np.asarray(record["contacts"])
        centers = contacts.mean(axis=1)
        self.assertLess(np.linalg.norm(centers[corner] - np.array([240, 240])), 2)
        self.assertGreater(ContactBrush(record).advance(1).sum(), 0)

    def test_stateless_backward_and_random_seek_matches_fresh_replay(self):
        program = glyph()
        order = [0.8, 0.15, 1.0, 0.42, 0.0, 0.67]
        first = {p: render_program(program, p) for p in order}
        second = {p: render_program(program, p) for p in reversed(order)}
        for p in order:
            np.testing.assert_array_equal(first[p], second[p])

    def test_final_is_seek_independent_and_size_is_square(self):
        program = glyph()
        render_program(program, 0.7)
        final_a = render_program(program, 1)
        render_program(program, 0.1)
        final_b = render_program(program, 1)
        np.testing.assert_array_equal(final_a, final_b)
        small = render_program(program, 1, size=96)
        self.assertEqual(small.shape, (96, 96))
        self.assertEqual(small.dtype, np.float32)
        self.assertGreaterEqual(float(small.min()), 0)
        self.assertLessEqual(float(small.max()), 1)


class PairedContactIRTests(unittest.TestCase):
    def program(self):
        p = glyph()
        p['schemaVersion'] = 'kai-stroke-ir/0.2'
        compiled = compile_program(glyph())
        p['strokes'] = [
            {'id': s['id'], 'kind': s['kind'], 'duration': s['duration'],
             'liftAfter': s['liftAfter'], 'geometry': {
                 'type': 'paired-contacts',
                 'stations': (np.asarray(r['contacts']) / 480).tolist(),
                 'corners': r['corners'], 'tension': r['tension']}}
            for s, r in zip(p['strokes'], compiled)]
        return p

    def test_contact_roundtrip_preserves_final_and_partial_deposition(self):
        p = json.loads(json.dumps(self.program()))
        validate_program(p)
        for progress in [0, .15, .3, .5, .9, 1]:
            np.testing.assert_array_equal(render_program(p, progress), render_program(glyph(), progress))
        self.assertEqual(len(p['strokes']), 2)

    def test_contact_geometry_rejects_invalid_or_ambiguous_fields(self):
        for mutate in [
            lambda g: g.update(stations=[[[0, 0], [0, 0]]] * 65),
            lambda g: g['stations'][0][0].__setitem__(0, float('nan')),
            lambda g: g.update(corners=[999]),
            lambda g: g.update(tension=2),
            lambda g: g.update(targetMask='not allowed'),
        ]:
            p = self.program()
            mutate(p['strokes'][0]['geometry'])
            with self.assertRaisesRegex(ValueError, "glyph '永' stroke 'horizontal'"):
                validate_program(p)

    def test_paired_replay_is_monotonic_and_lifts_are_blank(self):
        p = self.program()
        previous = render_program(p, 0)
        for t in np.linspace(0, 1, 25):
            current = render_program(p, float(t))
            self.assertTrue(np.all(current >= previous))
            previous = current
        np.testing.assert_array_equal(render_program(p, 1/3.4), render_program(p, 1.2/3.4))
        np.testing.assert_array_equal(render_program(p, .2), render_program(p, .2))


if __name__ == "__main__":
    unittest.main()
