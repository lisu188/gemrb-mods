#!/usr/bin/env python3
"""Exercise actual Psion companion runtime with a native-lifecycle boundary."""
import copy
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture = load("actor_state_fixture", ROOT / "common/tests/validate_actor_state_failures.py")
builder = load("crystal_resources", ROOT / "psion/tools/generate_psicrystal.py")


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.ActorStateFailures()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.psion = self.fx.psion
        self.gemrb = self.fx.gemrb
        self.gemrb.GetPartySize = lambda: 4
        sys.modules["GUICommon"].GetClassRowName = lambda actor: {
            1: "PSION_SEER", 2: "CIPHER", 3: "SORCERER_MONK", 4: "PSION_SHAPER",
        }.get(actor, "NO_CLASS")
        self.fx.effects[4] = []
        self.fx.known[4] = []
        self.fx.stats[1, 1] = 30
        self.fx.stats[1, 0] = 30
        self.fx.stats[4, 1] = 80
        self.fx.stats[4, 0] = 80
        self.fx.stats[4, 34] = 12
        self.fx.seed(self.psion.PSICRYSTAL_PERSONALITY_MARKER, self.psion.PSICRYSTAL_PERSONALITY_RESOURCE, 4)
        self.fx.seed(self.psion.PSICRYSTAL_PERSONALITY_MARKER, self.psion.PSICRYSTAL_PERSONALITY_RESOURCE, 1, 4)
        self.bodies = {}
        self.next_id = 3001
        self.calls = []
        self.failure = None
        self.gemrb.ManageCompanion = self.manage

        def learn(actor, resref, flags):
            self.fx.writes.append(("learn", actor, resref))
            self.fx.known[actor].append(resref)
            return 0
        self.gemrb.LearnSpell = learn

    def manage(self, actor, resource, mode):
        self.assertEqual(resource, "PSCRBODY")
        self.calls.append((actor, mode))
        if self.failure is not None and mode == self.failure:
            raise RuntimeError("native companion unavailable")
        body = self.bodies.get(actor)
        if mode == 2:
            self.bodies.pop(actor, None)
            return None
        created = False
        if mode == 1 and (not body or not body["Alive"]):
            body = {"ActorID": self.next_id, "Alive": True, "Created": False, "InArea": True}
            self.next_id += 1
            self.fx.effects[body["ActorID"]] = []
            self.fx.stats[body["ActorID"], 0] = 1
            self.bodies[actor] = body
            created = True
        if body and body["Alive"] and mode in (1, 3):
            body["InArea"] = True
        return {**body, "Created": created} if body else None

    def manifest(self, actor=1):
        self.psion.cancel_pending(actor)
        self.assertTrue(self.psion.begin_manifest(actor, "PXCRSUM"))
        self.assertTrue(self.psion.begin_manifest(actor, "PXCRSUM"))
        return self.bodies[actor]["ActorID"]

    def test_action_metadata_and_capability_gate(self):
        for resref, kind in (("PXCRSUM", "psicrystal_summon"), ("PXCRDIS", "psicrystal_dismiss")):
            self.assertEqual(self.psion.action_info(resref)["kind"], kind)
            self.assertEqual(self.psion.action_info(resref)["cost"], 0)
        del self.gemrb.ManageCompanion
        self.assertFalse(self.psion.can_summon_psicrystal(1))
        self.psion._ensure_psicrystal_actions(1)
        self.assertEqual(self.fx.writes, [])
        self.assertFalse(self.psion.begin_manifest(1, "PXCRSUM"))

    def test_migration_grants_actions_once_and_never_spawns(self):
        self.psion._ensure_psicrystal_actions(1)
        self.psion._ensure_psicrystal_actions(1)
        self.assertEqual(self.fx.known[1], ["PXCRSUM", "PXCRDIS"])
        self.assertEqual(self.bodies, {})
        self.assertFalse(self.psion._psicrystal_used(1))
        self.assertEqual(self.psion.psicrystal_personality(1), 4)

    def test_choice_required_and_non_psion_rejected(self):
        self.fx.effects[1] = []
        for actor in (1, 2, 3):
            self.assertFalse(self.psion.can_summon_psicrystal(actor))
            self.assertFalse(self.psion.begin_manifest(actor, "PXCRSUM"))
        self.assertEqual(self.bodies, {})

    def test_creation_is_once_at_confirmation_and_costs_no_pp(self):
        self.assertTrue(self.psion.begin_manifest(1, "PXCRSUM"))
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.fx.writes, [])
        self.assertTrue(self.psion.begin_manifest(1, "PXCRSUM"))
        self.assertTrue(self.psion.begin_manifest(1, "PXCRSUM"))
        self.assertEqual(sum(mode == 1 for _, mode in self.calls), 1)
        self.assertEqual(len(self.bodies), 1)
        self.assertTrue(self.psion._psicrystal_used(1))
        self.assertNotIn((1, self.psion.CURRENT_POOL_STAT), self.fx.stats)

    def test_cancellation_leaves_use_and_world_untouched(self):
        self.assertTrue(self.psion.begin_manifest(1, "PXCRSUM"))
        self.psion.cancel_pending(1)
        self.assertTrue(self.psion.begin_manifest(1, "PXCRSUM"))
        self.assertEqual(self.bodies, {})
        self.assertFalse(self.psion._psicrystal_used(1))

    def test_native_confirmation_routes_companion_action(self):
        book = type("Book", (), {"GetUsableMemorizedSpells": staticmethod(
            lambda actor, kind: [{"SpellIndex": 4000, "SpellResRef": "PXCRSUM"}])})
        self.assertTrue(self.fx.core.begin_spell(book, 1, 4000))
        self.assertEqual(self.bodies, {})
        self.assertTrue(self.fx.core.confirm_spell(1, "PXCRSUM"))
        self.assertEqual(len(self.bodies), 1)
        self.assertTrue(self.fx.core.confirm_spell(1, "PXCRSUM"))
        self.assertEqual(sum(mode == 1 for _, mode in self.calls), 1)

    def test_recall_preserves_injury_and_does_not_duplicate(self):
        body = self.manifest()
        self.assertEqual(self.fx.stats[body, 1], 15)
        self.fx.stats[body, 0] = 3
        self.fx.effects[body].append({"Opcode": "Other", "Param2": 1, "Param1": 7})
        effects = copy.deepcopy(self.fx.effects[body])
        self.assertEqual(self.manifest(), body)
        self.assertEqual(self.fx.stats[body, 0], 3)
        self.assertEqual(self.fx.effects[body], effects)
        self.assertEqual(len(self.bodies), 1)

    def test_death_and_dismissal_do_not_refund_creation(self):
        self.manifest()
        self.bodies[1]["Alive"] = False
        self.assertFalse(self.psion.can_summon_psicrystal(1))
        self.psion.cancel_pending(1)
        self.assertTrue(self.psion.begin_manifest(1, "PXCRDIS"))
        self.assertTrue(self.psion.begin_manifest(1, "PXCRDIS"))
        self.assertNotIn(1, self.bodies)
        self.assertFalse(self.psion.can_summon_psicrystal(1))
        self.assertEqual(self.psion.psicrystal_personality(1), 4)

    def test_completed_rest_allows_replacement_without_automatic_spawn(self):
        old = self.manifest()
        self.bodies[1]["Alive"] = False
        with patch.object(self.psion, "_base_restore_party"):
            self.psion.restore_party()
        self.assertEqual(self.bodies[1]["ActorID"], old)
        self.assertFalse(self.bodies[1]["Alive"])
        self.assertTrue(self.psion.can_summon_psicrystal(1))
        self.assertNotEqual(self.manifest(), old)
        self.assertTrue(self.psion._psicrystal_used(1))

    def test_rest_does_not_heal_companion(self):
        body = self.manifest()
        self.fx.stats[body, 0] = 2
        with patch.object(self.psion, "_base_restore_party"):
            self.psion.restore_party()
        self.assertEqual(self.fx.stats[body, 0], 2)
        self.assertEqual(self.bodies[1]["ActorID"], body)

    def test_level_scaling_uses_owner_and_never_refills_hp(self):
        body = self.manifest()
        self.fx.stats[body, 0] = 3
        self.fx.stats[1, 34] = 20
        self.fx.stats[1, 1] = 100
        self.fx.stats[1, 9] = 7
        self.psion.sync_psicrystal_party()
        self.assertEqual(self.fx.stats[body, 1], 50)
        self.assertEqual(self.fx.stats[body, 0], 3)
        self.assertEqual(self.fx.stats[body, 2], -5)
        self.assertEqual(self.fx.stats[body, 38], 15)
        self.assertEqual(self.fx.stats[body, 9], 7)
        self.assertEqual(self.fx.stats[body, 8], 0)

    def test_level_drain_clamps_hp(self):
        body = self.manifest(4)
        self.assertEqual(self.fx.stats[body, 1], 40)
        self.fx.stats[4, 34] = 1
        self.fx.stats[4, 1] = 8
        self.psion.sync_psicrystal_party()
        self.assertEqual(self.fx.stats[body, 1], 4)
        self.assertEqual(self.fx.stats[body, 0], 4)

    def test_two_owners_are_independent(self):
        first, second = self.manifest(1), self.manifest(4)
        self.assertNotEqual(first, second)
        self.psion._dismiss_psicrystal(1)
        self.assertEqual(self.bodies[4]["ActorID"], second)
        self.assertEqual(self.fx.stats[second, 1], 40)
        self.assertEqual(self.psion.psicrystal_personality(4), 1)

    def test_owner_death_cleans_up_companion(self):
        self.manifest()
        self.fx.stats[1, 0] = 0
        self.assertIsNone(self.psion.psicrystal_companion(1))
        self.assertNotIn(1, self.bodies)

    def test_area_and_selection_sync_never_spawns_missing_bodies(self):
        body = self.manifest()
        self.bodies[1]["InArea"] = False
        self.psion.refresh_innate_charges(3)
        self.assertTrue(self.bodies[1]["InArea"])
        self.assertEqual(self.bodies[1]["ActorID"], body)
        self.assertNotIn(4, self.bodies)
        self.assertEqual(sum(mode == 1 for _, mode in self.calls), 1)

    def test_saved_used_marker_survives_runtime_reload(self):
        self.manifest()
        self.psion._dismiss_psicrystal(1)
        reloaded = fixture.load("PsionicsReload", "psion/guiscripts/Psionics.py")
        self.assertFalse(reloaded.can_summon_psicrystal(1))
        self.assertEqual(reloaded.psicrystal_personality(1), 4)
        self.assertEqual(self.bodies, {})

    def test_missing_scaling_table_does_not_consume_use(self):
        self.fx.tables.pop("pscrlvl")
        with self.assertRaises(KeyError):
            self.psion._summon_psicrystal(1)
        self.assertFalse(self.psion._psicrystal_used(1))
        self.assertEqual(self.bodies, {})

    def test_failed_ownership_read_never_authorizes_replacement(self):
        self.failure = 0
        with self.assertRaises(RuntimeError):
            self.psion.can_summon_psicrystal(1)
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.fx.writes, [])

    def test_failed_state_write_prevents_spawn(self):
        self.gemrb.ApplyEffect = lambda *args: None
        with self.assertRaises(RuntimeError):
            self.psion._summon_psicrystal(1)
        self.assertEqual(self.bodies, {})
        self.assertNotIn((1, 1), self.calls)

    def test_failed_initialization_removes_partial_body(self):
        self.gemrb.SetPlayerStat = lambda *args: (_ for _ in ()).throw(RuntimeError("stat write failed"))
        with self.assertRaises(RuntimeError):
            self.psion._summon_psicrystal(1)
        self.assertEqual(self.bodies, {})
        self.assertTrue(self.psion._psicrystal_used(1))


class ResourceTests(unittest.TestCase):
    def test_bam_cycles_all_stances_directions_and_frame_bounds(self):
        bam = builder.animation_bytes()
        self.assertEqual(bam[:8], b"BAM V1  ")
        frames, cycles, transparent, frame_off, palette, lookup = struct.unpack_from("<HBBIII", bam, 8)
        self.assertEqual((frames, cycles, transparent), (5, 80, 0))
        self.assertEqual(palette, frame_off + frames * 12 + cycles * 4)
        for i in range(cycles):
            count, start = struct.unpack_from("<HH", bam, frame_off + frames * 12 + i * 4)
            self.assertEqual(count, 1 if i >= 64 else 4)
            for j in range(count):
                self.assertLess(struct.unpack_from("<H", bam, lookup + 2 * (start + j))[0], frames)
        for i in range(frames):
            w, h, x, y, offset = struct.unpack_from("<HHhhI", bam, frame_off + i * 12)
            self.assertEqual((w, h, x, y), (32, 40, 16, 34))
            self.assertTrue(offset & 0x80000000)
            self.assertLessEqual((offset & 0x7FFFFFFF) + w * h, len(bam))
        self.assertEqual(bam, builder.animation_bytes())

    def test_creature_has_no_foreign_inventory_dialog_or_effects(self):
        cre = builder.creature_bytes(0xF123)
        self.assertEqual(cre[:8], b"CRE V1.0")
        self.assertEqual(len(cre), 0x324)
        self.assertEqual(struct.unpack_from("<I", cre, 0x28)[0], 0xF123)
        self.assertEqual(cre[0x248:0x250].rstrip(b"\0"), b"PSCRAI")
        self.assertEqual(cre[0x280:0x2A0].rstrip(b"\0"), b"PSCRBODY")
        self.assertEqual(cre[0x2CC:0x2D4], b"\0" * 8)
        for offset in (0x2A4, 0x2AC, 0x2B4, 0x2C0, 0x2C8):
            self.assertEqual(struct.unpack_from("<I", cre, offset)[0], 0)
        self.assertEqual(cre[0x2D4:0x322], b"\xff" * 78)

    def test_avatar_allocation_preserves_foreign_rows_and_is_idempotent(self):
        text = "2DA V1.0\n*\n" + " ".join(builder.COLUMNS) + "\n0xf000 OTHER OTHER OTHER OTHER 1 1 1 *\n"
        number, result = builder.avatar_table(text)
        self.assertEqual(number, 0xF001)
        self.assertTrue(result.startswith(text))
        self.assertEqual(builder.avatar_table(result), (number, result))
        with self.assertRaises(ValueError):
            builder.avatar_table(result.replace("PSCRANI PSCRANI", "PSCRANI FOREIGN", 1))

    def test_level_table_covers_exact_twenty_owner_levels(self):
        table = fixture.Table(ROOT / "psion/tables/pscrlvl.2da")
        self.assertEqual(table.GetRowCount(), 20)
        for level in range(1, 21):
            self.assertEqual(int(table.GetValue(str(level), "AC")), 4 - (level - 1) // 2)
            self.assertEqual(int(table.GetValue(str(level), "INT")), 6 + (level - 1) // 2)

    def test_resource_builder_is_deterministic_and_rejects_foreign_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            avatars = root / "avatars.2da"
            avatars.write_text("2DA V1.0\n*\n" + " ".join(builder.COLUMNS) + "\n")
            builder.generate(avatars, root / "a")
            builder.generate(avatars, root / "b")
            self.assertEqual({p.name:p.read_bytes() for p in (root/"a").iterdir()},
                             {p.name:p.read_bytes() for p in (root/"b").iterdir()})
            (root/"a/foreign.txt").write_text("preserve")
            with self.assertRaises(ValueError):
                builder.generate(avatars, root/"a")
            self.assertEqual((root/"a/foreign.txt").read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
