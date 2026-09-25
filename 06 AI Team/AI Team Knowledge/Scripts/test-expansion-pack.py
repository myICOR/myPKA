#!/usr/bin/env python3
"""Exercise additive installation, rejected paths, conflicts and custom-work preservation.

The second half of this file is the Vex batch-b2 security ruling of
2026-09-15 (decision b2x), one case per finding, each watched RED against the
code as it stood before the fix:

  F1  a pack cannot place anything under `Scripts/`
  F2  `__pycache__` segments and importable or loadable file types are refused
  F3  an Agents folder that differs only by case from a real one is refused
  F4  an installed SOP / Workstream / Guideline / Template must be namespaced
  F5  the install receipt lives OUTSIDE the pack, and a forged in-pack one
      neither reports a pack installed nor enables `remove`

Everything runs in a temporary directory. Nothing here touches a real vault.

`--break-me` inverts one assertion so the suite itself can be watched going
red; run-red-tests.py uses it, because a fixture suite nobody watched fail is
a green that proves nothing (GL-1005 rule 4).
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Every child spawned from here runs with bytecode writing OFF. The scripts this
# file drives import siblings by path, and stock CPython drops the .pyc beside
# whatever copy it loaded; under a fixture root that is a file inside the
# fixture, which then shows up in a tree walk as bytes nobody wrote on purpose.
# Same cure as run-red-tests.py, for the same reason (1.24.0 CI).
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

SCRIPT = Path(__file__).with_name('expansion-pack.py')
BREAK_ME = '--break-me' in sys.argv[1:]
RECEIPTS = '.icor-for-life/expansions'


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack = self.root / '06 AI Team/Expansions/sample-pack'
        (self.pack / 'payload').mkdir(parents=True)
        (self.pack / 'README.md').write_text('Example pack')
        self.data = b'# Example procedure\n'
        (self.pack / 'payload/procedure.md').write_bytes(self.data)
        self.dest = '06 AI Team/AI Team Knowledge/SOPs/EP-sample.md'
        self.manifest = dict(schema=1, id='sample-pack', version='1.0.0', name='Example', description='Test', files=[dict(source='procedure.md', target=self.dest, sha256=hashlib.sha256(self.data).hexdigest())])
        self.save()

    def save(self):
        (self.pack / 'expansion.json').write_text(json.dumps(self.manifest))

    def call(self, command, approved=True):
        args = [sys.executable, str(SCRIPT), command, 'sample-pack', '--root', str(self.root)]
        if approved:
            args.append('--approved')
        return subprocess.run(args, capture_output=True, text=True,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def receipt(self, identifier='sample-pack'):
        return self.root / RECEIPTS / (identifier + '.json')

    def retarget(self, dest):
        self.manifest['files'][0]['target'] = dest
        self.save()

    def refuses(self, dest, because=''):
        """Install must be refused for `dest`, and nothing may be created."""
        self.retarget(dest)
        r = self.call('install')
        self.assertNotEqual(r.returncode, 0, 'accepted %r' % dest)
        self.assertNotIn('Traceback', r.stderr, 'crashed instead of refusing %r' % dest)
        if because:
            self.assertIn(because.casefold(), (r.stderr or '').casefold(),
                          'refused %r, but not for %r: %s' % (dest, because, r.stderr))
        return r

    # -- the original contract -------------------------------------------

    def test_install_and_remove(self):
        self.assertEqual(self.call('install').returncode, 0)
        self.assertEqual((self.root / self.dest).read_bytes(), self.data)
        self.assertTrue(self.receipt().is_file())
        self.assertEqual(self.call('remove').returncode, 0)
        self.assertFalse((self.root / self.dest).exists())
        self.assertTrue((self.pack / 'payload/procedure.md').exists())

    def test_approval_and_conflicts(self):
        self.assertNotEqual(self.call('install', False).returncode, 0)
        p = self.root / self.dest
        p.parent.mkdir(parents=True)
        p.write_text('Personal custom work')
        self.assertNotEqual(self.call('install').returncode, 0)
        self.assertEqual(p.read_text(), 'Personal custom work')

    def test_custom_changes_block_removal(self):
        self.assertEqual(self.call('install').returncode, 0)
        p = self.root / self.dest
        p.write_text('My edited procedure')
        self.assertNotEqual(self.call('remove').returncode, 0)
        self.assertEqual(p.read_text(), 'My edited procedure')
        self.assertTrue(self.receipt().exists())

    def test_bad_hash(self):
        (self.pack / 'payload/procedure.md').write_text('Changed download')
        self.assertNotEqual(self.call('install').returncode, 0)
        self.assertFalse((self.root / self.dest).exists())

    def test_target_escape_and_core_contract(self):
        for dest in ['../escape.md', '/tmp/escape.md', '06 AI Team/Agents/Larry/AGENT.md', '06 AI Team/Agents/larry/AGENT.md', '06 AI Team/Agents/Ada/AGENT.md', 'AGENTS.md', '04 Inner World/Notes/overwrite.md', '06 AI Team/AI Team Knowledge/SOPs/.env', '06 AI Team/Agents/new/../../escape.md']:
            with self.subTest(dest=dest):
                self.refuses(dest)

    def test_payload_and_target_symlinks(self):
        source = self.pack / 'payload/procedure.md'
        source.unlink()
        elsewhere = self.root / 'outside.md'
        elsewhere.write_bytes(self.data)
        source.symlink_to(elsewhere)
        self.assertNotEqual(self.call('install').returncode, 0)
        source.unlink()
        source.write_bytes(self.data)
        parent = self.root / '06 AI Team/AI Team Knowledge'
        parent.mkdir(parents=True)
        (parent / 'SOPs').symlink_to(self.root, target_is_directory=True)
        self.assertNotEqual(self.call('install').returncode, 0)

    def test_duplicate_destinations(self):
        self.manifest['files'].append(dict(self.manifest['files'][0]))
        self.save()
        self.assertNotEqual(self.call('install').returncode, 0)
        self.assertFalse((self.root / self.dest).exists())

    def test_entire_batch_preflight(self):
        self.manifest['files'].append(dict(source='procedure.md', target='AGENTS.md', sha256=hashlib.sha256(self.data).hexdigest()))
        self.save()
        self.assertNotEqual(self.call('install').returncode, 0)
        self.assertFalse((self.root / self.dest).exists())

    # -- F1: no Scripts targets, at all -----------------------------------

    def test_f1_scripts_targets_are_refused(self):
        """A pack may not place a file under Scripts/, reviewed or not.

        `Scripts/json.py` shadowed the standard library for every script the
        session-start hook runs, including expansion-pack.py itself, which is
        what locked `remove` out (Darshan Achar, thread 17)."""
        for dest in ['06 AI Team/AI Team Knowledge/Scripts/json.py',
                     '06 AI Team/AI Team Knowledge/Scripts/sample-pack-helper.py',
                     '06 AI Team/AI Team Knowledge/Scripts/EP-tool.py',
                     '06 AI Team/AI Team Knowledge/Scripts/nested/os.py',
                     '06 AI Team/AI Team Knowledge/Scripts/notes.md']:
            with self.subTest(dest=dest):
                self.refuses(dest, 'Scripts')
                self.assertFalse((self.root / dest).exists())
        self.assertFalse((self.root / '06 AI Team/AI Team Knowledge/Scripts').exists())

    # -- F2: no compiled or loadable file types, anywhere ------------------

    def test_f2_pycache_segments_are_refused(self):
        for dest in ['06 AI Team/Agents/Newby/__pycache__/notes.md',
                     '06 AI Team/Agents/Newby/__PyCache__/notes.md',
                     '06 AI Team/AI Team Knowledge/SOPs/__pycache__/EP-x.md']:
            with self.subTest(dest=dest):
                self.refuses(dest, '__pycache__')
                self.assertFalse((self.root / dest).exists())

    def test_f2_loadable_file_types_are_refused(self):
        for suffix in ['.pyc', '.pyo', '.pyd', '.so', '.dylib', '.pth',
                       '.plist', '.pyw', '.egg-link']:
            dest = '06 AI Team/Agents/Newby/module' + suffix
            with self.subTest(dest=dest):
                self.refuses(dest, suffix)
                self.assertFalse((self.root / dest).exists())

    def test_f2_loadable_payload_source_is_refused(self):
        (self.pack / 'payload/module.pyc').write_bytes(self.data)
        self.manifest['files'][0]['source'] = 'module.pyc'
        self.save()
        r = self.call('install')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('.pyc', r.stderr)

    # -- F3: an Agents name that differs only by case ----------------------

    def test_f3_agent_folder_case_clash_is_refused(self):
        (self.root / '06 AI Team/Agents/Aegis').mkdir(parents=True)
        r = self.refuses('06 AI Team/Agents/aegis/AGENT.md')
        # Case-insensitive on purpose: the message names the folder as the
        # filesystem spells it, and this suite must pass on either kind.
        self.assertIn('aegis', (r.stderr or '').casefold())
        # and the control: an Agents folder that clashes with nothing installs
        self.retarget('06 AI Team/Agents/Newby/AGENT.md')
        self.assertEqual(self.call('install').returncode, 0)

    # -- F4: a pack namespace on every installed knowledge file ------------

    def test_f4_official_looking_names_are_refused(self):
        for dest in ['06 AI Team/AI Team Knowledge/Guidelines/GL-1013-x.md',
                     '06 AI Team/AI Team Knowledge/SOPs/SOP-1099-x.md',
                     '06 AI Team/AI Team Knowledge/Workstreams/WS-1007-x.md',
                     '06 AI Team/AI Team Knowledge/Templates/note.md']:
            with self.subTest(dest=dest):
                self.refuses(dest, 'namespace')
                self.assertFalse((self.root / dest).exists())

    def test_f4_namespaced_names_install(self):
        """The negative control. A prefix rule that refuses everything proves
        as little as no rule at all."""
        for dest in ['06 AI Team/AI Team Knowledge/SOPs/EP-sample.md',
                     '06 AI Team/AI Team Knowledge/Guidelines/sample-pack-house-style.md',
                     '06 AI Team/AI Team Knowledge/Templates/EP-recipe.md']:
            with self.subTest(dest=dest):
                self.retarget(dest)
                r = self.call('install')
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue((self.root / dest).is_file())
                self.assertEqual(self.call('remove').returncode, 0)

    # -- F5: the receipt is the vault's, never the pack's ------------------

    def test_f5a_forged_in_pack_receipt_is_ignored(self):
        """A receipt shipped inside the pack must neither report the pack
        installed nor let `remove` delete anything."""
        victim = self.root / self.dest
        victim.parent.mkdir(parents=True)
        victim.write_bytes(self.data)          # the member's own file
        (self.pack / 'installation.json').write_text(json.dumps(
            {'schema': 1, 'id': 'sample-pack', 'version': '1.0.0',
             'installed_at': '2026-09-15T00:00:00+00:00',
             'files': [{'target': self.dest,
                        'sha256': hashlib.sha256(self.data).hexdigest()}]}))
        listed = subprocess.run(
            [sys.executable, str(SCRIPT), 'list', '--root', str(self.root)],
            capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(listed.returncode, 0, listed.stderr)
        rows = json.loads(listed.stdout)
        row = [x for x in rows if x['id'] == 'sample-pack'][0]
        self.assertNotEqual(row['status'], 'installed-files')
        r = self.call('remove')
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(victim.is_file())
        self.assertEqual(victim.read_bytes(), self.data)

    def test_f5b_receipt_lives_outside_the_pack(self):
        self.assertEqual(self.call('install').returncode, 0)
        self.assertTrue(self.receipt().is_file())
        self.assertFalse((self.pack / 'installation.json').exists())
        doc = json.loads(self.receipt().read_text())
        self.assertEqual(doc['id'], 'sample-pack')
        # Forging one inside the pack changes nothing either way.
        (self.pack / 'installation.json').write_text(self.receipt().read_text())
        # Deleting the real receipt disarms `remove`, whatever the pack ships.
        self.receipt().unlink()
        r = self.call('remove')
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.root / self.dest).is_file())
        # and the receipt is not overwritten in place on a second install
        self.assertNotEqual(self.call('install').returncode, 0)

    def test_f5b_remove_files_the_receipt_names_and_files_it_survives(self):
        self.assertEqual(self.call('install').returncode, 0)
        self.assertEqual(self.call('remove').returncode, 0)
        self.assertFalse(self.receipt().exists())
        gone = sorted((self.root / RECEIPTS).glob('removed-*.json'))
        self.assertEqual(len(gone), 1, 'expected one removed-*.json receipt')
        self.assertEqual(json.loads(gone[0].read_text())['id'], 'sample-pack')

    def test_f5c_install_refuses_a_pack_carrying_a_receipt(self):
        for name in ['installation.json', 'removed-20260101T000000000000.json']:
            with self.subTest(name=name):
                stray = self.pack / name
                stray.write_text(json.dumps(
                    {'schema': 1, 'id': 'sample-pack', 'files': []}))
                r = self.call('install')
                self.assertNotEqual(r.returncode, 0)
                self.assertFalse((self.root / self.dest).exists())
                self.assertFalse(self.receipt().exists())
                stray.unlink()

    def test_f5_remove_needs_the_vault_receipt(self):
        r = self.call('remove')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('Traceback', r.stderr)

    # -- the suite must be able to fail -----------------------------------

    def test_break_me_control(self):
        """`--break-me` must make this suite exit non-zero, or run-red-tests
        is asserting on a suite that cannot go red."""
        if BREAK_ME:
            self.fail('--break-me: deliberate failure, the suite can go red')


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + [a for a in sys.argv[1:] if a != '--break-me'])
