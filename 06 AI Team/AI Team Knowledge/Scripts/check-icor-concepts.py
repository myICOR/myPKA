#!/usr/bin/env python3
"""check-icor-concepts.py: prove .mypka/icor-concepts-1.json covers the spec it was built from.

Read-only. Writes nothing. Exit 0 when every check passes, 1 when any fails, 2 on bad input.

What it proves (split plan step 3 acceptance):
  1. every room in GL-1001's room table is a schema room, and no schema room is unknown to GL-1001
  2. every type in GL-1002's "Per type" table (plus GL-1015's team rows) is a schema type
  3. every GL-1002 REQUIRED field is in the schema with required: true (and every
     "at least one of" group is a required_any_of group); the reverse drift is reported too
  4. every GL-1002 optional field name is in the schema (prose fragments are skipped and counted)
  5. the pdf-highlight field table and the skill-field table agree with the schema
  6. internal integrity: every type points at a known concept, every concept at a known room,
     every default_path sits under its room and exists under the source root, every relation
     target is a known type
  7. the ICOR manifest declares implements: <schema id> and exposes only known concepts;
     the myPKA manifest's requires range admits the schema major
  8. every concept in .mypka/sources.yaml.example is a schema concept (and the reverse is listed)
  9. with --adr: the concept ids, default homes, slots and max write scopes in the sources.yaml
     ADR tables (section 2.1 content, 2.2 team) equal the schema's

--self-test runs the negative control (GL-070): the clean schema must pass, and three planted
defects (a dropped required field, a dropped room, a renamed concept) must each fail.

Usage:
  python3 check-icor-concepts.py [--mypka-root DIR] [--source-root DIR] [--adr FILE] [--json] [--self-test]
Roots: --mypka-root defaults to the folder holding .mypka/ above this script. --source-root
defaults to the myPKA root when it holds .icor-for-life/ (mode A), else ../icor-for-life (lab).
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCHEMA_REL = Path('.mypka') / 'icor-concepts-1.json'
ICOR_MANIFEST_REL = Path('.icor-for-life') / 'manifest.json'
MYPKA_MANIFEST_REL = Path('.mypka') / 'manifest.json'
SOURCES_EXAMPLE_REL = Path('.mypka') / 'sources.yaml.example'
NAME = re.compile(r'^[a-z][a-z0-9_]*$')
NON_TYPE_TARGETS = {'any', 'canvas'}


def find_mypka_root(start):
    for p in [start, *start.parents]:
        if (p / SCHEMA_REL).is_file():
            return p
    return None


def strip_parens(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\([^()]*\)', '', s)
    return s


def table_rows(text, header_startswith):
    """Rows of the first markdown table whose header row starts with header_startswith."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(header_startswith):
            rows = []
            for row in lines[i + 2:]:
                if not row.strip().startswith('|'):
                    break
                cells = [c.strip() for c in row.strip().strip('|').split('|')]
                rows.append(cells)
            return rows
    return []


def all_table_rows(text, header_startswith):
    """Rows of EVERY markdown table whose header row starts with header_startswith,
    in order. GL-1002 and GL-1015 each carry a per-type table with the same header."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.strip().startswith(header_startswith):
            out.extend(table_rows('\n'.join(lines[i:]), header_startswith))
    return out


def parse_rooms(gl1001):
    rooms = []
    for cells in table_rows(gl1001, '| Room |'):
        name = cells[0]
        if re.match(r'^\d\d ', name):
            rooms.append(name)
    return rooms


def split_names(cell):
    """Field names in a GL-1002 cell. Returns (names, any_of_groups, skipped_fragments)."""
    cell = cell.replace('`', '')
    if cell.strip() in ('-', ''):
        return [], [], 0
    names, groups, skipped = [], [], 0
    for part in strip_parens(cell).split(';'):
        part = part.strip()
        m = re.match(r'^at least one of (.+)$', part)
        if m:
            groups.append(sorted(x.strip() for x in m.group(1).split('/')))
            continue
        for tok in part.split(','):
            tok = tok.strip()
            if not tok:
                continue
            if NAME.match(tok):
                names.append(tok)
            else:
                skipped += 1
    return names, groups, skipped


def parse_gl1002(gl1002):
    types = {}
    skipped = 0
    for cells in all_table_rows(gl1002, '| type | required fields'):
        tnames = [t.strip() for t in cells[0].split('/')]
        req, groups, s1 = split_names(cells[1])
        opt, _, s2 = split_names(cells[2])
        skipped += s1 + s2
        for t in tnames:
            types[t] = {'required': req, 'any_of': groups, 'optional': opt}
    pdf = {}
    for cells in table_rows(gl1002, '| Field | Value | Required |'):
        field = cells[0].strip('`')
        pdf[field] = cells[2].strip().lower() == 'yes'
    skill = {}
    lines = gl1002.split('## Skills:', 1)
    if len(lines) == 2:
        for cells in table_rows(lines[1], '| field | type | required?'):
            skill[cells[0].strip('`')] = cells[2]
    return types, pdf, skill, skipped


def type_fields(schema, tname):
    t = schema['types'][tname]
    if 'fields' in t:
        fields = dict(t['fields'])
    else:
        fields = {k: v for k, v in schema.get(t.get('fields_ref', ''), {}).items()
                  if k not in t.get('excluded_fields', [])}
    fields.update(t.get('extra_fields', {}))
    for k, v in schema.get('common_fields', {}).items():
        fields.setdefault(k, v)
    return fields


def run_checks(schema, gl1001, gl1002, source_root, icor_manifest, mypka_manifest, sources_example, adr=None):
    fails, notes = [], []
    counts = {}

    # 1. rooms
    gl_rooms = parse_rooms(gl1001)
    s_rooms = {r['path']: r for r in schema.get('rooms', [])}
    counts['gl1001_rooms'] = len(gl_rooms)
    for r in gl_rooms:
        if r not in s_rooms:
            fails.append(f'room missing from schema: {r}')
    for r in s_rooms:
        if r not in gl_rooms:
            fails.append(f'schema room not in GL-1001: {r}')
    if not gl_rooms:
        fails.append('GL-1001 room table not found or empty')

    # 2 to 4. types and fields
    gl_types, pdf, skill, skipped = parse_gl1002(gl1002)
    counts['gl1002_types'] = len(gl_types)
    counts['gl1002_prose_fragments_skipped'] = skipped
    req_total = opt_total = 0
    if not gl_types:
        fails.append('GL-1002 "Per type" table not found or empty')
    for t, spec in gl_types.items():
        if t not in schema.get('types', {}):
            fails.append(f'type missing from schema: {t}')
            continue
        fields = type_fields(schema, t)
        for f in spec['required']:
            req_total += 1
            if f not in fields:
                fails.append(f'required field missing: {t}.{f}')
            elif not fields[f].get('required'):
                fails.append(f'field not marked required: {t}.{f}')
        s_groups = sorted(sorted(g) for g in schema['types'][t].get('required_any_of', []))
        if sorted(spec['any_of']) != s_groups:
            fails.append(f'any_of mismatch on {t}: GL-1002 {spec["any_of"]} schema {s_groups}')
        excluded = set(schema['types'][t].get('excluded_fields', []))
        for f in spec['optional']:
            opt_total += 1
            if f in excluded:
                notes.append(f'{t}.{f} declared not meaningful on {t} (shared type row)')
            elif f not in fields:
                fails.append(f'optional field missing: {t}.{f}')
        gl_req = set(spec['required']) | {x for g in spec['any_of'] for x in g}
        for f, v in fields.items():
            if v.get('required') and f not in gl_req and f not in schema.get('common_fields', {}):
                notes.append(f'schema marks {t}.{f} required but GL-1002 table does not')
    counts['gl1002_required_fields'] = req_total
    counts['gl1002_optional_fields'] = opt_total

    # 5. detail tables
    if 'pdf-highlight' in schema.get('types', {}):
        pf = type_fields(schema, 'pdf-highlight')
        for f, is_req in pdf.items():
            if f not in pf:
                fails.append(f'pdf-highlight detail field missing: {f}')
            elif is_req and not pf[f].get('required'):
                fails.append(f'pdf-highlight detail field not required: {f}')
    counts['pdf_highlight_detail_fields'] = len(pdf)
    pf = schema.get('procedure_fields', {})
    for f, req_cell in skill.items():
        if f not in pf:
            fails.append(f'skill field missing: {f}')
        elif 'required whenever' in req_cell and not pf[f].get('required_when'):
            fails.append(f'skill field lacks required_when: {f}')
    counts['skill_fields'] = len(skill)

    # 6. integrity
    concepts = schema.get('concepts', {})
    homes = {k: v for k, v in schema.get('team_concepts', {}).items() if not k.startswith('$')}
    all_types = set(schema.get('types', {}))
    room_concepts = set()
    for r in schema.get('rooms', []):
        for c in r.get('concepts', []):
            room_concepts.add(c)
            if c not in concepts:
                fails.append(f'room {r["path"]} lists unknown concept {c}')
    for c, spec in concepts.items():
        dp = spec.get('default_path', '')
        if spec.get('max_write_scope') not in ('none', 'frontmatter', 'full'):
            fails.append(f'concept {c} has no valid max_write_scope')
        if spec.get('machine_layer'):
            if source_root is not None and not (source_root / dp).is_dir():
                notes.append(f'machine-layer concept {c} not on disk yet (created by the source scripts): {dp}')
            continue
        if c not in room_concepts:
            fails.append(f'concept {c} is in no room')
        if spec.get('room') not in s_rooms:
            fails.append(f'concept {c} has unknown room {spec.get("room")}')
        if not (dp == spec.get('room') or dp.startswith(str(spec.get('room')) + '/')):
            fails.append(f'concept {c} default_path {dp} is not under its room')
        if source_root is not None and not (source_root / dp).is_dir():
            fails.append(f'concept {c} default_path missing under source root: {dp}')
        if source_root is not None and not spec.get('slots_created_on_demand'):
            for sl, sp in spec.get('slots', {}).items():
                if not (source_root / dp / sp).is_dir():
                    fails.append(f'slot {c}/{sl} missing under source root: {dp}/{sp}')
        for t in spec.get('types', []):
            if t not in all_types:
                fails.append(f'concept {c} lists unknown type {t}')
    for t, spec in schema.get('types', {}).items():
        if spec.get('side') == 'source' and spec.get('concept') not in concepts:
            fails.append(f'source type {t} has unknown concept {spec.get("concept")}')
        if spec.get('side') == 'team' and spec.get('concept') is None and spec.get('home') not in homes:
            fails.append(f'team type {t} has unknown home {spec.get("home")}')
        for f, v in type_fields(schema, t).items():
            tgt = v.get('target')
            if tgt and tgt not in all_types and tgt not in NON_TYPE_TARGETS:
                fails.append(f'relation {t}.{f} targets unknown type {tgt}')
            tc = v.get('target_concept')
            if tc and tc not in concepts:
                fails.append(f'relation {t}.{f} targets unknown concept {tc}')
            ts = v.get('target_slot')
            if tc in concepts and ts and ts not in concepts[tc].get('slots', {}):
                fails.append(f'relation {t}.{f} targets unknown slot {tc}/{ts}')
        sl = spec.get('slot')
        if sl and sl not in concepts.get(spec.get('concept'), {}).get('slots', {}):
            fails.append(f'type {t} names unknown slot {spec.get("concept")}/{sl}')
    counts['schema_rooms'] = len(s_rooms)
    counts['schema_concepts'] = len(concepts)
    counts['schema_types'] = len(all_types)

    # 7. manifests
    sid = schema.get('id', '')
    major = sid.rsplit('/', 1)[-1]
    if icor_manifest is not None:
        if icor_manifest.get('implements') != sid:
            fails.append(f'ICOR manifest implements {icor_manifest.get("implements")!r}, schema is {sid!r}')
        exp = icor_manifest.get('exposes')
        if exp is None:
            fails.append('ICOR manifest declares no exposes list')
        else:
            for c in exp:
                if c not in concepts:
                    fails.append(f'ICOR manifest exposes unknown concept {c}')
            if 'wip' not in exp:
                fails.append('ICOR manifest does not expose wip (ruling p2t)')
            for c in sorted(set(concepts) - set(exp)):
                notes.append(f'ICOR manifest does not expose {c}')
        tools = icor_manifest.get('tools', {})
        for n in schema.get('tools', {}).get('names', []):
            if n not in tools:
                fails.append(f'ICOR manifest tools lacks {n}')
            elif source_root is not None and not (source_root / tools[n]).is_file():
                fails.append(f'ICOR manifest tool {n} points at a missing file {tools[n]}')
    else:
        notes.append('no ICOR manifest found under the source root')
    if mypka_manifest is not None:
        req = mypka_manifest.get('requires', '')
        m = re.match(r'^icor-concepts >=(\d+) <(\d+)$', req)
        if not m or not (int(m.group(1)) <= int(major) < int(m.group(2))):
            fails.append(f'myPKA manifest requires {req!r} does not admit {sid}')

    # 8. sources.yaml.example
    if sources_example is not None:
        block = sources_example.split('\nconcepts:', 1)
        ex = re.findall(r'^\s{2}([a-z_]+):\s*\{', block[1], re.M) if len(block) == 2 else []
        counts['sources_example_concepts'] = len(ex)
        for c in ex:
            if c not in concepts:
                fails.append(f'sources.yaml.example concept not in schema: {c}')
        for c in re.findall(r'^\s{2}([a-z_]+):\s*task_attachment', sources_example, re.M):
            if c not in concepts:
                fails.append(f'sources.yaml.example fallback names unknown concept: {c}')

    if adr is not None:
        a2, a_team = parse_adr(adr)
        counts['adr_content_concepts'] = len(a2)
        counts['adr_team_concepts'] = len(a_team)
        for cid, row in a2.items():
            if cid not in concepts:
                fails.append(f'ADR concept not in schema: {cid}')
                continue
            sc = concepts[cid]
            if row['home'] != sc.get('default_path'):
                fails.append(f'ADR home mismatch {cid}: ADR {row["home"]!r} schema {sc.get("default_path")!r}')
            s_slots = set(sc.get('slots', {}))
            missing = sorted(set(row['slots']) - s_slots)
            extra = sorted(s_slots - set(row['slots']))
            if missing:
                fails.append(f'ADR slot not in schema {cid}: {missing}')
            if extra:
                notes.append(f'schema slots beyond ADR table {cid}: {extra} (schema is the slot SSOT; ADR table to follow)')
            if row['scope'] != sc.get('max_write_scope'):
                fails.append(f'ADR scope mismatch {cid}: ADR {row["scope"]} schema {sc.get("max_write_scope")}')
        for cid in concepts:
            if cid not in a2:
                fails.append(f'schema concept not in ADR 2.1: {cid}')
        for cid in a_team:
            if cid not in homes:
                fails.append(f'ADR team concept not in schema team_concepts: {cid}')
        for cid in homes:
            if cid not in a_team:
                fails.append(f'schema team concept not in ADR 2.2: {cid}')

    return fails, notes, counts


def parse_adr(text):
    content, team = {}, set()
    for cells in table_rows(text, '| id | Default home'):
        ids = re.findall(r'`([a-z_]+)`', cells[0])
        home = re.match(r'`([^`]+)`', cells[1])
        slots = [x for x in re.findall(r'`([a-z_]+)`', cells[2])]
        scope = re.match(r'`([a-z]+)`', cells[3])
        for i in ids:
            content[i] = {'home': home.group(1) if home else None, 'slots': slots,
                          'scope': scope.group(1) if scope else None}
    for cells in table_rows(text, '| id | Home under the team root'):
        team.update(re.findall(r'`([a-z_]+)`', cells[0]))
    return content, team


def load_inputs(mypka_root, source_root):
    schema = json.loads((mypka_root / SCHEMA_REL).read_text(encoding='utf-8'))
    src = schema['derived_from']
    gl1001 = (source_root / src['rooms']).read_text(encoding='utf-8')
    gl1002 = (source_root / src['fields']).read_text(encoding='utf-8')
    # The team half of the per-type table and the skill-field table moved to
    # myPKA's GL-1015 at the split (step 10). It is read from the myPKA root
    # and appended, so checks 2 to 5 see one table, as before the split.
    team_rel = src.get('team_fields')
    if team_rel and (mypka_root / team_rel).is_file():
        gl1002 += '\n\n' + (mypka_root / team_rel).read_text(encoding='utf-8')
    im = source_root / ICOR_MANIFEST_REL
    mm = mypka_root / MYPKA_MANIFEST_REL
    se = mypka_root / SOURCES_EXAMPLE_REL
    return (schema, gl1001, gl1002,
            json.loads(im.read_text(encoding='utf-8')) if im.is_file() else None,
            json.loads(mm.read_text(encoding='utf-8')) if mm.is_file() else None,
            se.read_text(encoding='utf-8') if se.is_file() else None)


def self_test(schema, gl1001, gl1002, source_root, im, mm, se, adr=None):
    results = []
    f, _, _ = run_checks(schema, gl1001, gl1002, source_root, im, mm, se, adr)
    results.append(('clean schema passes', not f, f))

    s = copy.deepcopy(schema)
    del s['types']['project']['fields']['goal']
    f, _, _ = run_checks(s, gl1001, gl1002, source_root, im, mm, se, adr)
    results.append(('planted: project.goal removed -> fails', any('project.goal' in x for x in f), f))

    s = copy.deepcopy(schema)
    s['rooms'] = [r for r in s['rooms'] if r['path'] != '03 WiP']  # T2: fixture
    f, _, _ = run_checks(s, gl1001, gl1002, source_root, im, mm, se, adr)
    results.append(('planted: room 03 WiP removed -> fails', any('03 WiP' in x for x in f), f))  # T2: fixture

    s = copy.deepcopy(schema)
    s['concepts']['work_in_progress'] = s['concepts'].pop('wip')
    f, _, _ = run_checks(s, gl1001, gl1002, source_root, im, mm, se, adr)
    results.append(('planted: concept wip renamed -> fails', any('wip' in x for x in f), f))
    if adr is not None:
        s = copy.deepcopy(schema)
        s['concepts']['icor_journey_notes'] = s['concepts'].pop('journey_notes')
        f, _, _ = run_checks(s, gl1001, gl1002, source_root, im, mm, se, adr)
        results.append(('planted: journey_notes renamed against the ADR -> fails',
                        any('journey_notes' in x and 'ADR' in x for x in f), f))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--mypka-root')
    ap.add_argument('--source-root')
    ap.add_argument('--adr', help='the sources.yaml ADR; compares concept ids, homes, slots, scopes')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()

    mypka_root = Path(a.mypka_root).resolve() if a.mypka_root else find_mypka_root(Path(__file__).resolve().parent)
    if mypka_root is None or not (mypka_root / SCHEMA_REL).is_file():
        print(f'error: no {SCHEMA_REL} found; pass --mypka-root', file=sys.stderr)
        return 2
    if a.source_root:
        source_root = Path(a.source_root).resolve()
    elif (mypka_root / ICOR_MANIFEST_REL).is_file():
        source_root = mypka_root
    else:
        source_root = (mypka_root.parent / 'icor-for-life').resolve()
    if not source_root.is_dir():
        print(f'error: source root not found: {source_root}', file=sys.stderr)
        return 2

    inputs = load_inputs(mypka_root, source_root)
    adr = Path(a.adr).read_text(encoding='utf-8') if a.adr else None
    if a.self_test:
        results = self_test(*inputs[:3], source_root, *inputs[3:], adr)
        ok = all(r[1] for r in results)
        if a.json:
            print(json.dumps({'ok': ok, 'cases': [{'case': c, 'ok': o, 'failures': f} for c, o, f in results]}, indent=2))
        else:
            for c, o, f in results:
                print(f'{"PASS" if o else "FAIL"}  {c}' + ('' if o else f'  ({f[:3]})'))
            print('self-test ' + ('green' if ok else 'RED'))
        return 0 if ok else 1

    fails, notes, counts = run_checks(*inputs[:3], source_root, *inputs[3:], adr)
    ok = not fails
    if a.json:
        print(json.dumps({'ok': ok, 'schema': inputs[0]['id'], 'mypka_root': str(mypka_root),
                          'source_root': str(source_root), 'counts': counts,
                          'failures': fails, 'notes': notes}, indent=2))
    else:
        print(f'schema {inputs[0]["id"]}  mypka_root={mypka_root}  source_root={source_root}')
        for k, v in counts.items():
            print(f'  {k}: {v}')
        for n in notes:
            print(f'  note: {n}')
        for f in fails:
            print(f'  FAIL: {f}')
        print('check ' + ('green' if ok else f'RED ({len(fails)} failures)'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
