#!/usr/bin/env python3
"""Equipped lenses must preserve exact DCs and canonical PP costs."""
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("lens_actor_state", ROOT / "common/tests/validate_actor_state_failures.py")
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


class EquipmentDCTests(unittest.TestCase):
    def test_two_lenses_cover_intelligence_cap_for_normal_and_augmented_powers(self):
        for intelligence in (24, 25):
            for lenses in (0, 1, 2):
                for resource, cost, index in (("PS1CHAR", 1, 4000), ("PSMT03", 3, 255000)):
                    with self.subTest(intelligence=intelligence, lenses=lenses, resource=resource):
                        fx = fixture.ActorStateFailures()
                        fx.setUp()
                        try:
                            psion = fx.psion
                            sys.modules["GUICommon"].GetClassRowName = lambda actor: "PSION_TELEPATH"
                            fx.stats[1, 38] = intelligence
                            fx.stats[1, 34] = 20
                            fx.seed(psion.POOL_EFFECT_MARKER, psion.POOL_EFFECT_RESOURCE, 100)
                            for _ in range(lenses):
                                fx.seed(0, "PSIDC1", 0)
                            modifier = 7 + lenses
                            replacement = resource + str(modifier)
                            fx.gemrb.GetSpell = lambda ref, *args: {"SpellResRef": ref} if ref == replacement else None
                            book = types.SimpleNamespace(GetUsableMemorizedSpells=lambda *args: [{"SpellResRef": "PS1MTHR"}])
                            effects = copy.deepcopy(fx.effects)
                            stats = dict(fx.stats)
                            known = copy.deepcopy(fx.known)
                            plan = psion.manifestation_plan(1, resource)
                            self.assertEqual(psion.equipment_dc_bonus(1), lenses)
                            self.assertEqual(psion._dc_modifier(1), modifier)
                            self.assertTrue(plan["allowed"])
                            self.assertEqual(plan["cost"], cost)
                            self.assertEqual(plan["cast_resref"], replacement)
                            self.assertEqual(psion.power_info(replacement)["resref"], resource)
                            entry = {"SpellIndex": index, "SpellResRef": resource}
                            self.assertIs(psion.prepare_action_entry(book, 1, entry), entry)
                            self.assertEqual(entry["CastResRef"], replacement)
                            self.assertEqual(fx.effects, effects)
                            self.assertEqual(fx.stats, stats)
                            self.assertEqual(fx.known, known)
                            self.assertTrue(psion.commit_manifestation(1, resource))
                            self.assertEqual(psion._pool_snapshot(1), 100 - cost)
                            self.assertEqual(fx.known, known)
                        finally:
                            fx.doCleanups()


if __name__ == "__main__":
    unittest.main()
