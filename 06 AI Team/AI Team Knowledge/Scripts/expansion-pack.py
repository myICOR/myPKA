#!/usr/bin/env python3
"""Expansion file management: copy reviewed pack files into the vault; run none of them.

See GL-1012 and WS-1006.

WHAT "EXECUTES NOTHING" MEANS HERE. It means THIS TOOL runs nothing from a
pack: no installer, no hook, no lifecycle command, not even to unpack. It has
never meant that an installed file is inert. Whatever normally reads a folder
goes on reading it afterwards, so a file placed somewhere the interpreter or
the dynamic loader looks is executable by definition. That is why schema 1
refuses `Scripts/` targets outright, refuses `__pycache__` and every
importable or loadable file type vault-wide, and keeps its install receipt
outside the pack (Vex ruling, batch b2, 2026-09-15), in the folder the
install mode gives it (resolve.py `expansion_receipts_dir`).
"""
import argparse
import importlib.util
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# resolve.py sits beside this script and is loaded by path, like noteio.py.
# It is the one code that finds the team root and turns a concept into a
# place (GL-1013 sections 6 and 9).
_rs_path = Path(__file__).resolve().parent / "resolve.py"
if not _rs_path.is_file():
    raise SystemExit("FAIL resolve.py is missing from %s. Scripts/ is half "
                     "upgraded; restore resolve.py beside this script and run "
                     "this again." % _rs_path.parent)
_rs = importlib.util.spec_from_file_location("mypka_resolve", _rs_path)
resolver = importlib.util.module_from_spec(_rs)
_rs.loader.exec_module(resolver)


def _team_root(explicit=None):
    """GL-1013 section 6: explicit, then CLAUDE_PROJECT_DIR when it holds the
    marker, then the walk up from this file."""
    try:
        return resolver.find_team_root(explicit=explicit, start=__file__).path
    except resolver.ResolveError as e:
        raise SystemExit("FAIL %s" % e)

CORE = {'Larry', 'Nolan', 'Pax', 'Penn', 'Mack', 'Silas', 'Iris', 'Charta', 'Flint',
        'Ada', 'Mason'}

# F1 (CRITICAL). `Scripts` is NOT in this set and must not be added. A pack
# file under Scripts/ is imported by every script the session-start hook runs:
# a `Scripts/json.py` shadowed the standard library for expansion-pack.py
# itself and locked `remove` out of its own vault. There is no allow-list
# version of this that is safe, because the danger is the folder, not the file.
KINDS = {'SOPs', 'Workstreams', 'Guidelines', 'Templates'}

# F2 (HIGH). Suffixes the interpreter or the dynamic loader picks up without
# anybody opening them. `.pth` is the worst of them: a single line in one runs
# at interpreter start. Checked on the FINAL segment only, case-folded,
# everywhere `safe()` is used, which is every path this tool touches.
LOADABLE_SUFFIXES = ('.pyc', '.pyo', '.pyd', '.so', '.dylib', '.pth',
                     '.plist', '.pyw', '.egg-link')

# F5 (HIGH). The receipt is the VAULT's record, not the pack's. One inside the
# pack is written by whoever shipped the pack, and a forged one made `remove`
# delete files the pack never installed.
#
# WHERE the vault keeps it follows the install mode, and the resolver answers
# that, not this file: `.icor-for-life/expansions` in mode A (one folder),
# `.mypka/expansions` in mode B (myPKA beside its content, where the team root
# has no `.icor-for-life/` at all). Until 6.0.2 this was a literal here, and a
# mode B install created an `.icor-for-life/` inside the myPKA folder.
PACK_ID = re.compile(r'[a-z][a-z0-9-]{0,79}')
NAMESPACE_NOTE = ('a pack namespace keeps an installed file distinguishable '
                  'from the scaffold\'s own numbered knowledge')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(base, value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Invalid path')
    parts = value.split('/')
    if any(x in ('', '.', '..') or x.startswith('.') for x in parts):
        raise ValueError('Hidden, absolute or traversal path rejected: ' + value)
    for x in parts:
        if x.casefold() == '__pycache__':
            raise ValueError('Compiled-module cache rejected: a pack may not write '
                             'into a __pycache__ folder, whose contents Python loads '
                             'without checking anyone reviewed them: ' + value)
    tail = parts[-1].casefold()
    for suffix in LOADABLE_SUFFIXES:
        if tail.endswith(suffix):
            raise ValueError('Importable or loadable file type rejected (%s): schema 1 '
                             'copies text a person can read, never a file the '
                             'interpreter or the dynamic loader picks up: %s'
                             % (suffix, value))
    p = base
    for part in parts:
        p = p / part
        if p.is_symlink():
            raise ValueError('Symbolic link rejected: ' + value)
    if not p.resolve().is_relative_to(base.resolve()):
        raise ValueError('Path escapes allowed root')
    return p


def agent_case_clash(root, name):
    """The real `Agents/` entry that differs from `name` only by case, if any.

    F3. Case-folding against the CORE names caught `larry` and missed every
    agent hired since, so this reads the directory instead of a list. The
    count in CORE is not a fact to restate anywhere: it grew from nine to ten
    when Ada shipped, and a sentence naming a number is the thing that goes
    stale on the next hire.
    """
    try:
        entries = list((root / '06 AI Team' / 'Agents').iterdir())
    except OSError:
        return None
    for e in entries:
        if e.name != name and e.name.casefold() == name.casefold():
            return e.name
    return None


def target(root, value, pack_id=None):
    p = safe(root, value)
    parts = Path(value).parts
    if len(parts) >= 3 and parts[:2] == ('06 AI Team', 'AI Team Knowledge') \
            and parts[2] == 'Scripts':
        raise ValueError('Scripts targets are not supported in schema 1: a pack cannot '
                         'install anything under Scripts/, reviewed or not, because '
                         'every script the session start runs imports from that folder: '
                         + value)
    in_agents = len(parts) >= 4 and parts[:2] == ('06 AI Team', 'Agents')
    in_knowledge = (len(parts) >= 4 and parts[:2] == ('06 AI Team', 'AI Team Knowledge')
                    and parts[2] in KINDS)
    allowed = in_knowledge or (in_agents
                               and parts[2].casefold() not in {x.casefold() for x in CORE})
    if not allowed or p.name.casefold() in {'agent-index.md', 'index.md'}:
        raise ValueError('Protected or unsupported target: ' + value)
    if in_agents:
        clash = agent_case_clash(root, parts[2])
        if clash:
            raise ValueError('Agent folder "%s" differs only by case from the existing '
                             '"%s"; install into that folder or pick another name: %s'
                             % (parts[2], clash, value))
    if in_knowledge and pack_id is not None:
        if not (p.name.startswith(pack_id + '-') or p.name[:3].upper() == 'EP-'):
            raise ValueError('Missing pack namespace on an installed %s file: name it '
                             '"%s-%s" or "EP-%s" (%s): %s'
                             % (parts[2], pack_id, p.name, p.name, NAMESPACE_NOTE, value))
    return p


def check_id(identifier):
    if not identifier or not PACK_ID.fullmatch(identifier):
        raise ValueError('Pack id must be lowercase letters, digits and hyphens')
    return identifier


def pack_path(root, identifier):
    return safe(root, '06 AI Team/Expansions/' + check_id(identifier))


def receipt_dir(root):
    """The folder this vault keeps its receipts in: resolve.py's one answer
    (`expansion_receipts_dir`). A sources.yaml that does not load stops the
    operation; a guessed folder is an ownership record `remove` never finds."""
    try:
        return resolver.expansion_receipts_dir(root)
    except resolver.ResolveError as e:
        raise ValueError('cannot tell where this folder keeps its expansion receipts, '
                         'because its binding does not load (%s); run resolve.py --check' % e)


def receipt_rel(root):
    """The receipt folder as the member reads it, relative to the team root."""
    return receipt_dir(root).relative_to(Path(root).resolve()).as_posix()


def receipt_path(root, identifier):
    """Where the install receipt lives: `<receipt_dir>/<id>.json`.

    Not built with safe(), which refuses dotted segments by design. The id is
    already constrained to lowercase letters, digits and hyphens, so there is
    no traversal to make.
    """
    return receipt_dir(root) / (check_id(identifier) + '.json')


def stray_receipts(pack):
    """Receipt-shaped files sitting INSIDE a pack. Never read, always reported.

    Either a pack from before the receipt moved, or a forgery. Both are
    ambiguous enough that install refuses rather than guessing (F5c).
    """
    found = []
    try:
        if (pack / 'installation.json').is_file():
            found.append('installation.json')
        found += sorted(p.name for p in pack.glob('removed-*.json') if p.is_file())
    except OSError:
        pass
    return found


def _stops(root):
    stops = {(root / '06 AI Team' / 'Agents').resolve()}
    stops |= {(root / '06 AI Team' / 'AI Team Knowledge' / k).resolve() for k in KINDS}
    return stops


def missing_dirs(root, targets):
    """The folders install is about to create: the absent parents of every
    target, up to (never including) a fixed home. Recorded in the receipt so
    `remove` takes away only what install made (Vex C2 X2)."""
    stops, base, out = _stops(root), root.resolve(), set()
    for p in targets:
        q = p.parent
        while not q.exists() and q.resolve() not in stops and q.resolve() != base:
            out.add(q.relative_to(root).as_posix())
            q = q.parent
    return sorted(out)


def prune_empty(root, created_dirs):
    """Remove the folders install created, deepest first, once they are empty.

    Only a folder the receipt lists as created by install is a candidate
    (Vex C2 X2): an empty folder the member already had stays. A receipt
    written before 6.0.2 lists none, so nothing is pruned for it. The fixed
    homes (`06 AI Team/Agents`, the knowledge kind folders) are never
    removed. An empty `Agents/<Name>/Journal/` left behind made
    `validate-team.py` fail on the next run (C1 G3). A folder that still
    holds anything, a member's own note included, stays: rmdir refuses it,
    and that refusal is the rule.
    """
    stops, base = _stops(root), root.resolve()
    candidates = set()
    for rel in created_dirs or []:
        try:
            q = safe(root, rel)
        except ValueError:
            continue    # a receipt entry that is not a plain vault path is ignored
        if q.resolve() in stops or q.resolve() == base:
            continue
        candidates.add(q)
    gone = []
    for q in sorted(candidates, key=lambda x: len(x.parts), reverse=True):
        try:
            if q.is_dir() and not q.is_symlink() and not any(q.iterdir()):
                q.rmdir()
                gone.append(q.relative_to(root).as_posix())
        except OSError:
            pass
    return sorted(gone)


def inspect(root, identifier):
    pack = pack_path(root, identifier)
    manifest = safe(pack, 'expansion.json')
    m = json.loads(manifest.read_text())
    if m.get('schema') != 1 or m.get('id') != identifier:
        raise ValueError('Unsupported schema or mismatched id')
    for k in ('version', 'name', 'description'):
        if not isinstance(m.get(k), str) or not m[k].strip():
            raise ValueError('Missing manifest field: ' + k)
    if not safe(pack, 'README.md').is_file():
        raise ValueError('Pack README.md is required')
    files = m.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= 500:
        raise ValueError('Expected 1-500 file mappings')
    seen = set()
    for f in files:
        if not isinstance(f, dict) or not re.fullmatch(r'[a-f0-9]{64}', f.get('sha256', '')):
            raise ValueError('Each file needs a SHA-256 hash')
        src = safe(pack, 'payload/' + f['source'])
        dst = target(root, f['target'], identifier)
        key = f['target'].casefold()
        if key in seen:
            raise ValueError('Duplicate target: ' + f['target'])
        seen.add(key)
        if not src.is_file() or src.stat().st_size > 25_000_000:
            raise ValueError('Missing or oversized payload: ' + f['source'])
        if digest(src) != f['sha256']:
            raise ValueError('Payload hash mismatch: ' + f['source'])
        if dst.exists() and not dst.is_file():
            raise ValueError('Destination is not a regular file')
    return pack, m


def run(args):
    root = _team_root(args.root)
    if args.command == 'list':
        folder = safe(root, '06 AI Team/Expansions')
        result = []
        if folder.is_dir():
            # Asked once, before the loop: a binding that does not load stops
            # the listing, rather than reading as "no pack installed" per pack.
            receipts = receipt_dir(root)
            for p in sorted(folder.iterdir()):
                if p.is_symlink():
                    result.append({'id': p.name, 'status': 'rejected-symlink'})
                elif p.is_dir():
                    try:
                        installed = (receipts / (check_id(p.name) + '.json')).is_file()
                    except ValueError:
                        installed = False   # not a legal pack id, so not installed
                    row = {'id': p.name,
                           'status': 'installed-files' if installed else 'needs-inspection'}
                    stray = stray_receipts(p)
                    if stray:
                        row['ignored_in_pack_receipts'] = stray
                    result.append(row)
                elif p.suffix.lower() == '.zip':
                    result.append({'id': p.name, 'status': 'needs-safe-extraction'})
        return result
    check_id(args.id)
    receipt = receipt_path(root, args.id)
    if args.command == 'remove':
        if not args.approved:
            raise ValueError('Removal requires the approved plan and --approved')
        if receipt.is_symlink() or not receipt.is_file():
            raise ValueError('No install receipt at %s/%s.json, so this tool did not '
                             'install this pack and will not delete anything. A receipt '
                             'inside the pack folder is never read.'
                             % (receipt_rel(root), args.id))
        r = json.loads(receipt.read_text())
        if r.get('schema') != 1 or r.get('id') != args.id:
            raise ValueError('Invalid ownership receipt')
        paths = []
        for f in r['files']:
            p = target(root, f['target'], args.id)
            if not p.is_file() or digest(p) != f['sha256']:
                raise ValueError('Owned file changed or missing; nothing removed: ' + f['target'])
            paths.append(p)
        for p in paths:
            p.unlink()
        pruned = prune_empty(root, r.get('created_dirs'))
        receipt.rename(receipt.with_name(
            'removed-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json'))
        return {'id': args.id, 'removed_files': len(paths), 'removed_empty_folders': pruned,
                'registration': 'must be reviewed separately'}
    pack, m = inspect(root, args.id)
    conflicts = [f['target'] for f in m['files'] if target(root, f['target'], args.id).exists()]
    if args.command == 'inspect':
        return {'manifest': m, 'conflicts': conflicts,
                'receipt': '%s/%s.json' % (receipt_rel(root), args.id),
                'receipt_exists': receipt.exists(),
                'in_pack_receipts_ignored': stray_receipts(pack),
                'executes_payload': False,
                'executes_payload_means': 'this tool runs nothing from the pack. It does '
                                          'NOT mean an installed file cannot run later, '
                                          'through whatever normally reads that folder.'}
    if not args.approved:
        raise ValueError('Installation requires the approved plan and --approved')
    stray = stray_receipts(pack)
    if stray:
        raise ValueError('Pack folder carries %s. The receipt belongs in %s/, and a '
                         'receipt shipped inside a pack is either stale or forged; '
                         'review it, move it aside, then install.'
                         % (', '.join(stray), receipt_rel(root)))
    if receipt.exists() or conflicts:
        raise ValueError('Existing installation or targets; use a reviewed migration, never overwrite')
    # Read and hash all bytes before writing; exclusive creation also catches races.
    payload = []
    for f in m['files']:
        b = safe(pack, 'payload/' + f['source']).read_bytes()
        if hashlib.sha256(b).hexdigest() != f['sha256']:
            raise ValueError('Payload changed after inspection')
        payload.append((target(root, f['target'], args.id), b))
    created = []
    made_dirs = missing_dirs(root, [p for p, _b in payload])
    try:
        for p, b in payload:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as out:
                created.append((p, hashlib.sha256(b).hexdigest()))
                out.write(b)
        r = {'schema': 1, 'id': m['id'], 'version': m['version'],
             'installed_at': datetime.now(timezone.utc).isoformat(),
             'files': [{'target': f['target'], 'sha256': f['sha256']} for f in m['files']],
             'created_dirs': made_dirs}
        receipt.parent.mkdir(parents=True, exist_ok=True)
        # 'x', never 'w': an existing receipt is somebody else's ownership record
        # and must never be overwritten without a person seeing it.
        with receipt.open('x') as out:
            json.dump(r, out, indent=2)
    except Exception:
        for p, h in created:
            if p.is_file() and not p.is_symlink() and digest(p) == h:
                p.unlink()
        raise
    return {'id': m['id'], 'installed_files': len(created),
            'receipt': '%s/%s.json' % (receipt_rel(root), m['id']),
            'activation': 'pending registration and bounded example'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['list', 'inspect', 'install', 'remove'])
    ap.add_argument('id', nargs='?')
    ap.add_argument('--root', help='Vault root, for testing or another vault')
    ap.add_argument('--approved', action='store_true')
    args = ap.parse_args()
    try:
        print(json.dumps(run(args), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as e:
        print('Expansion operation stopped: ' + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
