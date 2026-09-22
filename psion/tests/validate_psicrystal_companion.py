#!/usr/bin/env python3
"""Companion runtime transactions and generated native-resource invariants."""
from pathlib import Path
import copy
import importlib.util
import json
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load("companion_state_fixture", "common/tests/validate_actor_state_failures.py")
builder = load("companion_builder", "psion/tools/generate_psicrystal.py")


class Companion(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.ActorStateFailures()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.runtime = self.fx.psion
        self.engine = self.fx.gemrb
        self.core = self.fx.core
        self.globals = {}
        self.bodies = {}
        self.next_id = 2000
        self.combat = False
        self.area = "AR0001"
        self.areas = {1: self.area, 2: self.area, 3: self.area, 4: self.area}
        self.classes = {1: "PSION_SEER", 2: "CIPHER", 3: "SORCERER_MONK", 4: "PSION_EGOIST"}
        self.fx.effects[4] = []
        self.fx.known[4] = []
        self.fx.stats[1, 0] = 60
        self.fx.stats[1, 1] = 81
        self.fx.stats[4, 0] = 60
        self.fx.stats[4, 1] = 70
        self.fail = None
        self.engine.GetGameVar = lambda name: self.globals.get(name, 0)
        self.engine.SetGlobal = self.set_global
        self.engine.GetPartySize = lambda: 4
        self.engine.GetPlayerStat = self.stat
        self.engine.SetPlayerStat = self.set_stat
        self.engine.CreateCreature = self.create
        self.engine.EvaluateString = self.evaluate
        self.engine.ApplyEffect = self.apply
        self.engine.LearnSpell = self.learn
        self.engine.RemoveSpell = self.remove
        self.engine.GetMemorizedSpellsCount = lambda *args: 0
        self.engine.MemorizeSpell = lambda *args: True
        self.engine.Roll = lambda dice, sides, bonus: 10 + bonus
        sys.modules["GUICommon"].GetClassRowName = lambda actor: self.classes.get(actor, "")
        self.fx.tables["pscrlvl"] = fixtures.Table(ROOT / "psion/tables/pscrlvl.2da")
        self.fx.tables["pscrcfg"] = type("Config", (), {
            "GetValue": lambda self, row, column: {"OWNER_LIMIT": 255, "PARTY_SLOTS": 6, "OWNER_STAT": 163}[row],
        })()
        for actor in (1, 4):
            self.fx.seed(self.runtime.PSICRYSTAL_PERSONALITY_MARKER,
                         self.runtime.PSICRYSTAL_PERSONALITY_RESOURCE, 4, actor)

    def stat(self, actor, stat, base=0):
        if not base and stat == 163:
            tags = [effect for effect in self.fx.effects.get(actor, [])
                    if effect["Opcode"] == "ScriptingState" and effect["Param2"] == 7]
            if tags:
                return tags[-1]["Param1"]
        return self.fx.stats.get((actor, stat), {34: 1, 38: 16, 39: 14, 41: 14}.get(stat, 0))

    def set_stat(self, actor, stat, value):
        if self.fail == "stat" and actor > 1000:
            raise RuntimeError("stat write failed")
        self.fx.set_stat(actor, stat, value)

    def set_global(self, name, scope, value):
        self.assertEqual(scope, "GLOBAL")
        if self.fail == "global":
            return
        self.globals[name] = value

    def apply(self, actor, opcode, p1, p2, r1="", r2="", r3="", source="", *args):
        if opcode == "ModifyLocalVariable":
            if self.fail == r1:
                raise RuntimeError("local write failed")
            self.bodies[actor]["locals"][r1] = p1
        elif opcode == "UnsummonCreature":
            self.bodies[actor]["destroyed"] = True
        elif opcode == "ScriptingState" and self.fail == "tag":
            return
        else:
            self.fx.apply(actor, opcode, p1, p2, r1, r2, r3, source)

    def create(self, actor, resource):
        if self.fail == "create":
            return 0
        self.next_id += 1
        self.bodies[self.next_id] = {"name": resource, "area": self.area, "locals": {}, "destroyed": False}
        self.fx.effects[self.next_id] = []
        return self.next_id

    def evaluate(self, trigger, quiet=False):
        if self.fail == "trigger":
            raise RuntimeError("trigger evaluation failed")
        if trigger == "ActuallyInCombat()":
            return self.combat
        match = re.fullmatch(r"InMyArea\(Player(\d+)\)", trigger)
        if match:
            return self.areas.get(int(match[1])) == self.area
        match = re.fullmatch(r'Exists\("(PSCR\d+)"\)', trigger)
        if match:
            return any(body["name"] == match[1] and body["area"] == self.area and not body["destroyed"]
                       for body in self.bodies.values())
        raise AssertionError(trigger)

    def learn(self, actor, resource, *args):
        if resource not in self.fx.known[actor]:
            self.fx.known[actor].append(resource)
        return 0

    def remove(self, actor, resource, *args):
        self.fx.known[actor][:] = [known for known in self.fx.known[actor] if known != resource]

    def begin(self, actor=1, resource="PXCSUM"):
        book = type("Book", (), {"GetUsableMemorizedSpells": lambda self, actor, kind: [
            {"SpellIndex": 4000, "SpellResRef": resource, "BookType": 2},
        ]})()
        return self.core.begin_spell(book, actor, 4000)

    def cast(self, actor=1, resource="PXCSUM"):
        self.assertTrue(self.begin(actor, resource))
        return self.core.confirm_spell(actor, resource)

    def test_selection_only_reserves_and_confirmation_spawns_once(self):
        self.assertTrue(self.begin())
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {})
        self.assertTrue(self.core.confirm_spell(1, "PXCSUM"))
        self.assertTrue(self.core.confirm_spell(1, "PXCSUM"))
        self.assertEqual(len(self.bodies), 1)
        self.assertEqual(self.bodies[2001]["locals"], {"PSCREP": 1, "PSREADY": 1})
        self.assertEqual(self.globals, {"PSCRNEXT": 1, "PSCR001": 1})

    def test_cancellation_neither_allocates_nor_spawns(self):
        self.assertTrue(self.begin())
        self.core.cancel_pending(1)
        self.assertFalse(self.core.confirm_spell(1, "PXCSUM"))
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {})
        self.assertEqual(self.fx.writes, [])

    def test_existing_companion_blocks_a_second_cast(self):
        self.assertTrue(self.cast())
        self.assertFalse(self.begin())
        self.assertEqual(len(self.bodies), 1)
        self.assertEqual(self.globals["PSCR001"], 1)

    def test_dismissal_invalidates_epoch_without_erasing_personality(self):
        self.cast()
        effects = copy.deepcopy(self.fx.effects[1])
        self.assertTrue(self.cast(resource="PXCDISM"))
        self.assertEqual(self.globals["PSCR001"], 2)
        self.assertEqual(self.bodies[2001]["locals"]["PSCREP"], 1)
        self.assertEqual(self.fx.effects[1], effects)
        self.assertTrue(self.core.confirm_spell(1, "PXCDISM"))
        self.assertEqual(self.globals["PSCR001"], 2)

    def test_death_and_remanifest_keep_owner_and_personality(self):
        self.cast()
        self.bodies[2001]["destroyed"] = True
        self.assertTrue(self.cast())
        self.assertEqual(self.globals, {"PSCRNEXT": 1, "PSCR001": 2})
        self.assertEqual(self.runtime.psicrystal_personality(1), 4)
        self.assertEqual(self.bodies[2002]["locals"]["PSCREP"], 2)

    def test_travel_invalidates_old_area_generation(self):
        self.cast()
        self.area = self.areas[1] = "AR0002"
        self.assertTrue(self.cast())
        self.assertEqual(self.bodies[2001]["area"], "AR0001")
        self.assertEqual(self.bodies[2001]["locals"]["PSCREP"], 1)
        self.assertEqual(self.bodies[2002]["area"], "AR0002")
        self.assertEqual(self.globals["PSCR001"], 2)

    def test_cannot_create_in_current_area_for_owner_elsewhere(self):
        self.areas[1] = "AR9999"
        self.assertFalse(self.begin())
        self.assertEqual(self.bodies, {})

    def test_two_psions_have_separate_identity_and_generations(self):
        self.cast(1)
        self.cast(4)
        self.assertEqual(self.globals, {"PSCRNEXT": 2, "PSCR001": 1, "PSCR002": 1})
        self.cast(1, "PXCDISM")
        self.assertEqual(self.globals["PSCR002"], 1)
        self.assertEqual(self.runtime._psicrystal_owner_token(4), 2)

    def test_identity_follows_actor_after_party_reordering(self):
        self.cast(1)
        self.cast(4)
        self.fx.effects[1], self.fx.effects[4] = self.fx.effects[4], self.fx.effects[1]
        self.classes[1], self.classes[4] = self.classes[4], self.classes[1]
        self.assertEqual(self.runtime._psicrystal_owner_token(1), 2)
        self.assertEqual(self.runtime._psicrystal_owner_token(4), 1)
        self.cast(4, "PXCDISM")
        self.assertEqual(self.globals["PSCR001"], 2)
        self.assertEqual(self.globals["PSCR002"], 1)

    def test_serialized_boundary_snapshot_uses_no_transient_actor_ids(self):
        self.cast()
        snapshot = json.loads(json.dumps({"effects": self.fx.effects, "globals": self.globals, "bodies": self.bodies}))
        self.core.cancel_pending()
        self.fx.effects = {int(key): value for key, value in snapshot["effects"].items()}
        self.globals = snapshot["globals"]
        self.bodies = {9001: snapshot["bodies"]["2001"]}
        self.assertEqual(self.runtime._psicrystal_owner_token(1), 1)
        self.assertFalse(self.begin())
        self.assertTrue(self.cast(resource="PXCDISM"))
        self.assertEqual(self.globals["PSCR001"], 2)

    def test_combat_is_checked_at_reservation_and_confirmation(self):
        self.combat = True
        self.assertFalse(self.begin())
        self.combat = False
        self.assertTrue(self.begin())
        self.combat = True
        self.assertFalse(self.core.confirm_spell(1, "PXCSUM"))
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {})

    def test_dismissal_is_allowed_in_combat(self):
        self.cast()
        self.combat = True
        self.assertTrue(self.cast(resource="PXCDISM"))

    def test_no_choice_no_companion_or_automatic_default(self):
        self.fx.effects[1] = []
        self.assertFalse(self.begin())
        self.assertFalse(self.begin(resource="PXCDISM"))
        self.assertEqual(self.runtime.psicrystal_personality(1), 0)
        self.assertEqual(self.bodies, {})

    def test_lazy_actions_are_idempotent_and_do_not_spawn(self):
        for _ in range(3):
            self.runtime._sync_psicrystal_selector(1)
        self.assertEqual(self.fx.known[1], ["PXCSUM", "PXCDISM"])
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {})

    def test_refresh_and_rest_do_not_spawn_or_heal_companion(self):
        self.cast()
        self.fx.stats[2001, 0] = 1
        self.runtime.refresh_innate_charges(1)
        self.runtime.restore_party()
        self.assertEqual(len(self.bodies), 1)
        self.assertEqual(self.stat(2001, 0), 1)
        self.assertEqual(self.globals["PSCR001"], 1)

    def test_levels_one_to_twenty_across_six_disciplines(self):
        for class_name in self.runtime.PSION_CLASSES:
            self.classes[1] = class_name
            for level in range(1, 21):
                with self.subTest(discipline=class_name, level=level):
                    self.fx.stats[1, 34] = level
                    for stat in range(9, 14):
                        self.fx.stats[1, stat] = stat + 2
                    profile = self.runtime.psicrystal_profile(1)
                    self.assertEqual(profile[0], 40)
                    self.assertEqual(profile[1], 40)
                    self.assertEqual(profile[2], 10 - (level - 1) // 2)
                    self.assertEqual(profile[38], 6 + (level - 1) // 2)
                    self.assertEqual(profile[8], 0)
                    self.assertEqual(profile[34], level)
                    for stat in range(9, 14):
                        self.assertEqual(profile[stat], stat + 2)

    def test_small_and_large_hp_are_bounded(self):
        for maximum, expected in ((1, 1), (0, 1), (7, 3), (100000, 32767)):
            self.fx.stats[1, 1] = maximum
            self.assertEqual(self.runtime.psicrystal_profile(1)[0], expected)

    def test_post_spawn_failure_destroys_incomplete_body_and_vetoes_cast(self):
        for failure in ("stat", "PSCREP", "PSREADY"):
            with self.subTest(failure=failure):
                self.fail = failure
                self.assertTrue(self.begin())
                with self.assertRaises(RuntimeError):
                    self.core.confirm_spell(1, "PXCSUM")
                self.assertTrue(self.bodies[self.next_id]["destroyed"])
                self.assertNotIn(1, self.core._pending_casts)
                self.assertEqual(self.fx.transactions._pending, {})
                self.fail = None

    def test_failed_creation_does_not_commit_epoch(self):
        self.fail = "create"
        self.assertTrue(self.begin())
        with self.assertRaises(RuntimeError):
            self.core.confirm_spell(1, "PXCSUM")
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {"PSCRNEXT": 1})

    def test_missing_tag_application_aborts_before_spawn(self):
        self.fail = "tag"
        self.assertTrue(self.begin())
        with self.assertRaisesRegex(RuntimeError, "tag was not applied"):
            self.core.confirm_spell(1, "PXCSUM")
        self.assertEqual(self.bodies, {})

    def test_global_write_failure_aborts_before_spawn(self):
        self.fail = "global"
        self.assertTrue(self.begin())
        with self.assertRaisesRegex(RuntimeError, "allocation failed"):
            self.core.confirm_spell(1, "PXCSUM")
        self.assertEqual(self.bodies, {})

    def test_missing_api_and_trigger_errors_fail_closed(self):
        create = self.engine.CreateCreature
        del self.engine.CreateCreature
        with self.assertRaises(RuntimeError):
            self.begin()
        self.engine.CreateCreature = create
        self.fail = "trigger"
        with self.assertRaises(RuntimeError):
            self.begin()
        self.assertEqual(self.bodies, {})

    def test_exhausted_identity_counter_does_not_spawn(self):
        self.globals["PSCRNEXT"] = 255
        self.assertTrue(self.begin())
        with self.assertRaises(RuntimeError):
            self.core.confirm_spell(1, "PXCSUM")
        self.assertEqual(self.bodies, {})
        self.assertEqual(self.globals, {"PSCRNEXT": 255})

    def test_exhausted_epoch_does_not_spawn(self):
        self.cast()
        self.bodies[2001]["destroyed"] = True
        self.globals["PSCR001"] = 0x7fffffff
        with self.assertRaises(RuntimeError):
            self.begin()
        self.assertEqual(len(self.bodies), 1)

    def test_imported_identity_from_another_save_is_rejected(self):
        self.fx.seed(self.runtime.PSICRYSTAL_OWNER_MARKER, "PSCRID", 2)
        with self.assertRaises(RuntimeError):
            self.begin()
        self.assertEqual(self.bodies, {})

    def test_duplicate_imported_owner_is_rejected(self):
        self.cast()
        self.fx.seed(self.runtime.PSICRYSTAL_OWNER_MARKER, "PSCRID", 1, 4)
        with self.assertRaisesRegex(RuntimeError, "same imported"):
            self.begin(4)

    def test_foreign_scripting_slot_is_not_overwritten(self):
        self.fx.effects[1].append({"Opcode": "ScriptingState", "Param1": 1, "Param2": 7, "Resource1": "FOREIGN"})
        before = copy.deepcopy(self.fx.effects[1])
        with self.assertRaises(RuntimeError):
            self.begin()
        self.assertEqual(self.fx.effects[1], before)
        self.assertEqual(self.globals, {})

    def test_foreign_base_scripting_stat_is_not_overwritten(self):
        self.fx.stats[1, 163] = 42
        with self.assertRaises(RuntimeError):
            self.begin()
        self.assertEqual(self.fx.stats[1, 163], 42)

    def test_native_classes_cannot_manifest_companion(self):
        self.assertFalse(self.begin(2))
        self.assertFalse(self.begin(3))
        self.assertEqual(self.bodies, {})


class Generator(unittest.TestCase):
    def test_party_selectors_are_contiguous_and_bounded(self):
        self.assertEqual(builder.party_slots("21 Player1\n22 Player2\n"), [1, 2])
        for text in ("", "22 Player2", "21 Player1\n23 Player3", "\n".join(f"{20+i} Player{i}" for i in range(1, 34))):
            with self.assertRaises(ValueError):
                builder.party_slots(text)

    def test_trigger_ids_fit_actual_engine_array_and_do_not_collide(self):
        text = "0x4100 Existing()\n0x101 Alias()\n"
        extended = builder.extend_triggers(text)
        self.assertTrue(extended.startswith(text))
        ids = [int(code, 0) for code in re.findall(r"(?m)^(\S+) Global(?:LT|GT)Global", extended)]
        self.assertEqual(ids, [0x4102, 0x4103])
        self.assertTrue(all((value & 0x3fff) < 300 for value in ids))
        full = "\n".join(f"{value:#x} Other{value}()" for value in range(0x4100, 0x412c))
        with self.assertRaises(ValueError):
            builder.extend_triggers(full)

    def test_engine_trigger_overrides_reserve_numeric_aliases(self):
        engine = "16640 NextTriggerObject(O:Target*)\n0x4101 MovementRate(O:Target*,I:Rate*)\n"
        extended = builder.extend_triggers("", engine)
        self.assertIn("0x4102 GlobalLTGlobal", extended)
        with self.assertRaisesRegex(ValueError, "overridden"):
            builder.extend_triggers("0x4100 GlobalLTGlobal(S:A*,S:B*,S:C*,S:D*)", engine)
        native = "0x411c GlobalLTGlobal(S:A*,S:B*,S:C*,S:D*)\n0x4120 ActuallyInCombat()\n"
        extended = builder.extend_triggers("", native)
        self.assertIn("0x411c GlobalLTGlobal", extended)
        self.assertIn("0x4120 ActuallyInCombat()", extended)

    def test_invalid_trigger_signatures_and_duplicate_ids_are_rejected(self):
        for text in ("0x4100 GlobalLTGlobal(S:A*,S:B*)", "0x4300 GlobalGTGlobal(S:A*,S:B*,S:C*,S:D*)",
                     "0x4100 ActuallyInCombat(I:A*)", "0x4100 ActuallyInCombat()\n0x4101 ActuallyInCombat()"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                builder.extend_triggers(text)

    def test_animation_allocation_preserves_existing_rows(self):
        original = "2DA V1.0\n*\nAT_1 AT_2 AT_3 AT_4 TYPE SPACE PALETTE SIZE\n0xe000 OTHER OTHER OTHER OTHER 13 1 1 *\n"
        animation, extended = builder.extend_avatars(original)
        self.assertEqual(animation, 0xe001)
        self.assertTrue(extended.startswith(original))
        with self.assertRaises(ValueError):
            builder.extend_avatars(extended)

    def test_original_bam_has_valid_frames_palette_and_direction_cycles(self):
        data = builder.crystal_bam()
        magic, frames, cycles, transparent, frame_offset, palette, lookup = struct.unpack_from("<8sHBBIII", data)
        self.assertEqual((magic, frames, cycles, transparent), (b"BAM V1  ", 4, 5, 0))
        for index in range(frames):
            width, height, x, y, pixels = struct.unpack_from("<HHhhI", data, frame_offset + 12 * index)
            self.assertTrue(pixels & 0x80000000)
            pixels &= 0x7fffffff
            self.assertLessEqual(pixels + width * height, len(data))
            self.assertGreater(len(set(data[pixels:pixels + width * height])), 3)
        for direction in range(cycles):
            count, first = struct.unpack_from("<HH", data, frame_offset + frames * 12 + direction * 4)
            self.assertEqual(count, frames)
            self.assertEqual(struct.unpack_from("<4H", data, lookup + 2 * first), (0, 1, 2, 3))
        self.assertLessEqual(palette + 1024, lookup)
        self.assertEqual(data, builder.crystal_bam())

    def test_owner_bank_scripts_do_not_depend_on_party_slot_identity(self):
        for token in range(1, 256):
            script = builder.lifecycle_script(token, range(1, 7))
            self.assertIn(f'GlobalLTGlobal("PSCREP","LOCALS","PSCR{token:03d}","GLOBAL")', script)
            self.assertIn(f'GlobalGTGlobal("PSCREP","LOCALS","PSCR{token:03d}","GLOBAL")', script)
            self.assertEqual(script.count("DestroySelf()"), 9)
            for slot in range(1, 7):
                self.assertIn(f"CheckStat(Player{slot},{token},163)", script)
            self.assertNotIn("Familiar", script)


if __name__ == "__main__":
    unittest.main()
