"""Native, domain-neutral digest production and protected periodic review.

No domain plugin, provider, cron, agent dispatcher or external command required.
"""
import copy
import base64
import hashlib
import json
import os
import re
import string
import uuid
from pathlib import Path


def extend(Base, require, digest, now, file_digest, nonempty, Refusal):
    class Harness82(Base):
        @staticmethod
        def _json(raw):
            def pairs(rows):
                result = {}
                for key, value in rows:
                    require(key not in result, 'DIGEST_SOURCE', 'Duplicate JSON keys are not inventory evidence')
                    result[key] = value
                return result
            def constant(_):
                raise Refusal('DIGEST_SOURCE', 'Non-finite JSON values are refused')
            return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

        def _source(self, relative):
            try:
                path = self.project_file(relative)
                require(path.stat().st_size <= 16 * 1024 * 1024, 'DIGEST_SOURCE', 'Source exceeds the per-file safety limit')
                raw = path.read_bytes()
                return {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}, raw
            except (OSError, UnicodeError, ValueError, Refusal) as error:
                if isinstance(error, Refusal) and error.code == 'DIGEST_SOURCE':
                    raise
                raise Refusal('DIGEST_SOURCE', 'A declared physical source is missing, unsafe or unreadable') from error

        def _pattern(self, value, fields):
            require(nonempty(value) and len(value) <= 4096, 'PERIODIC_POLICY', 'A bounded relative source/output pattern is required')
            seen = set()
            try:
                for _, key, fmt, conversion in string.Formatter().parse(value):
                    if key is not None:
                        require(key in fields and not conversion and (not fmt or (re.fullmatch(r'0?\d*d', fmt) and int(fmt[:-1] or 0) <= 12)),
                                'PERIODIC_POLICY', 'Only declared integer placeholders are supported')
                        seen.add(key)
                require(seen == set(fields), 'PERIODIC_POLICY', 'Use every required cycle/window placeholder')
                self.project_file(value.format(**{key: 1 for key in fields}), exists=False)
            except (ValueError, KeyError, IndexError):
                raise Refusal('PERIODIC_POLICY', 'Invalid path pattern') from None

        def normalize_mission(self, mission):
            normalized = super().normalize_mission(mission)
            policy = normalized.get('periodic_review')
            if policy is None:
                return normalized
            required = {'notes_pattern', 'digest_pattern', 'governing_file', 'invariant_markers', 'mutable_sections'}
            allowed = required | {'every', 'anchor', 'stale_markers', 'observation_pattern', 'baseline', 'inventory'}
            require(isinstance(policy, dict) and required <= set(policy) <= allowed, 'PERIODIC_POLICY', 'Use the periodic-review policy template')
            policy.setdefault('every', normalized['budget']['consolidate_every'])
            policy.setdefault('anchor', 0)
            policy.setdefault('stale_markers', [])
            require(type(policy['every']) is int and policy['every'] > 0 and type(policy['anchor']) is int and policy['anchor'] >= 0,
                    'PERIODIC_POLICY', 'Cadence is a positive number of cycles with a nonnegative explicit anchor')
            require(policy['every'] == normalized['budget']['consolidate_every'], 'PERIODIC_POLICY', 'Use the consolidation boundary; do not create a second schedule')
            self._pattern(policy['notes_pattern'], {'cycle'})
            self._pattern(policy['digest_pattern'], {'start', 'end'})
            self.project_file(policy['governing_file'], exists=False)
            require(isinstance(policy['invariant_markers'], list) and policy['invariant_markers'] and
                    all(nonempty(x) for x in policy['invariant_markers']) and len(set(policy['invariant_markers'])) == len(policy['invariant_markers']),
                    'PERIODIC_POLICY', 'Declare unique invariant markers')
            require(isinstance(policy['stale_markers'], list) and all(nonempty(x) for x in policy['stale_markers']), 'PERIODIC_POLICY', 'Stale markers must be strings')
            sections = policy['mutable_sections']
            require(isinstance(sections, dict) and set(sections) == {'objectives', 'scenario'}, 'PERIODIC_POLICY', 'Only objectives and scenario may be mutable')
            for section in sections.values():
                require(isinstance(section, dict) and set(section) == {'begin', 'end'} and all(nonempty(v) for v in section.values()),
                        'PERIODIC_POLICY', 'Each section needs explicit begin/end delimiters')
            inventory_fields = {'observation_pattern', 'baseline', 'inventory'}
            require(not (set(policy) & inventory_fields) or inventory_fields <= set(policy), 'PERIODIC_POLICY', 'Inventory reconciliation requires baseline, observation pattern and inventory policy together')
            if 'inventory' in policy:
                self._pattern(policy['observation_pattern'], {'cycle'})
                self.project_file(policy['baseline'], exists=False)
                inventory = policy['inventory']
                require(isinstance(inventory, dict) and set(inventory) == {'categories', 'total', 'monotonic'}, 'PERIODIC_POLICY', 'Declare ordered categories, fixed total and monotonic category counters')
                categories = inventory['categories']
                require(isinstance(categories, list) and categories and all(nonempty(x) for x in categories) and len(set(categories)) == len(categories), 'PERIODIC_POLICY', 'Categories must be unique ordered names')
                require(type(inventory['total']) is int and inventory['total'] > 0, 'PERIODIC_POLICY', 'Declare the project denominator explicitly')
                counters = inventory['monotonic']
                if isinstance(counters, list):
                    require(all(nonempty(x) for x in counters) and len(set(counters)) == len(counters), 'PERIODIC_POLICY', 'Counter names must be unique strings')
                    counters = {name: [name] for name in counters}
                require(isinstance(counters, dict) and all(nonempty(name) and isinstance(group, list) and group and
                        all(nonempty(x) for x in group) and len(set(group)) == len(group) and set(group) <= set(categories)
                        for name, group in counters.items()), 'PERIODIC_POLICY', 'Declare category groups for monotonic counters')
                inventory['monotonic'] = counters
            return normalized

        @staticmethod
        def _window(policy, through):
            return {'start': through - policy['every'] + 1, 'end': through}

        @staticmethod
        def _due(policy, through):
            return bool(policy and type(through) is int and through > policy['anchor'] and (through - policy['anchor']) % policy['every'] == 0)

        def _layout(self, policy, text):
            spans = []
            delimiters = []
            for key, section in policy['mutable_sections'].items():
                begin, end = section['begin'], section['end']
                require(text.count(begin) == text.count(end) == 1, 'CORE_CHANGED', 'Section delimiters must occur exactly once')
                a = text.index(begin) + len(begin)
                b = text.index(end)
                require(a <= b, 'CORE_CHANGED', 'Invalid mutable-section order')
                spans.append((a, b, key))
                delimiters += [begin, end]
            spans.sort()
            require(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])), 'CORE_CHANGED', 'Mutable sections cannot overlap')
            protected, cursor = [], 0
            for a, b, key in spans:
                protected.extend([text[cursor:a], {'mutable_section': key}])
                cursor = b
            protected.append(text[cursor:])
            protected_text = ''.join(x for x in protected if isinstance(x, str))
            missing = [x for x in policy['invariant_markers'] if x not in protected_text]
            require(not missing, 'CORE_CHANGED', 'Configured invariants must remain in protected instructions, outside mutable sections')
            return spans, digest(protected)

        def periodic_init(self, state):
            policy = state['mission'].get('periodic_review')
            if policy:
                require(policy['anchor'] == len(state['cycles']), 'PERIODIC_POLICY',
                        'Adopt periodic controls at the current cycle count; init starts at zero')
                _, raw = self._source(policy['governing_file'])
                text = raw.decode('utf-8')
                _, core_hash = self._layout(policy, text)
                state['periodic_guard'] = {'mission_hash': state['mission_hash'], 'policy_sha256': digest(policy),
                                           'protected_sha256': core_hash, 'trusted_prompt': text}
                if 'baseline' in policy:
                    _, witness = self._observation(policy, policy['anchor'])
                    state['periodic_guard']['baseline'] = witness

        def _revision_preview(self, state, proposal):
            result = super()._revision_preview(state, proposal)
            policy = result['after'].get('periodic_review')
            if policy:
                require(policy['anchor'] == len(state['cycles']), 'PERIODIC_POLICY',
                        'A human mission revision must explicitly anchor the new review epoch at the current cycle count')
                if 'baseline' in policy:
                    self._observation(policy, policy['anchor'])
            return result

        def on_mission_revision(self, state):
            old = state.get('periodic_guard')
            policy = state['mission'].get('periodic_review')
            if old and policy:
                _, raw = self._source(policy['governing_file'])
                _, fingerprint = self._layout(policy, raw.decode('utf-8'))
                require(fingerprint == old['protected_sha256'], 'CORE_CHANGED', 'An unrelated mission revision cannot silently rebaseline weakened instructions')
            self.periodic_init(state)

        def _guard(self, state):
            policy = state['mission']['periodic_review']
            guard = state.get('periodic_guard', {})
            require(guard.get('mission_hash') == state['mission_hash'] and guard.get('policy_sha256') == digest(policy),
                    'PERIODIC_POLICY', 'Periodic controls must be established by init or an explicit human mission revision')
            try:
                _, raw = self._source(policy['governing_file'])
                text = raw.decode('utf-8')
            except (Refusal, UnicodeError):
                raise Refusal('CORE_CHANGED', 'The governing file is missing, unsafe or no longer valid UTF-8') from None
            spans, fingerprint = self._layout(policy, text)
            require(fingerprint == guard['protected_sha256'], 'CORE_CHANGED', 'Protected instruction content changed, even if its marker names remain')
            return text, spans

        def _observation(self, policy, cycle):
            relative = policy['baseline'] if cycle == policy['anchor'] else policy['observation_pattern'].format(cycle=cycle)
            witness, raw = self._source(relative)
            try:
                value = self._json(raw)
                require(isinstance(value, dict) and type(value.get('cycle')) is int and value['cycle'] == cycle, 'DIGEST_SOURCE', 'Observation cycle does not match the requested window')
                require(set(value) <= {'cycle', 'live', 'closed', 'transitions', 'facts_recorded', 'facts_used'}, 'DIGEST_SOURCE', 'Unknown observation field')
                for field in ('live', 'closed'):
                    require(isinstance(value.get(field), dict) and all(nonempty(k) and isinstance(v, str) for k, v in value[field].items()),
                            'DIGEST_SOURCE', 'Observations require ID-to-category live and closed mappings')
                require(isinstance(value.get('transitions', []), list), 'DIGEST_SOURCE', 'Transitions must be a list')
                for field in ('facts_recorded', 'facts_used'):
                    require(isinstance(value.get(field, []), list) and all(nonempty(x) for x in value.get(field, [])), 'DIGEST_SOURCE', 'Fact labels must be string lists')
                return value, witness
            except (ValueError, UnicodeError):
                raise Refusal('DIGEST_SOURCE', 'Invalid structured observation JSON') from None

        def _receipt(self, receipt, identifier, before, after, state):
            if not isinstance(receipt, dict) or set(receipt) - {'id', 'from', 'to', 'kind', 'reason', 'evidence', 'claim_id'}:
                return False
            if (receipt.get('id'), receipt.get('from'), receipt.get('to')) != (identifier, before, after):
                return False
            if not nonempty(receipt.get('reason')) or not isinstance(receipt.get('evidence'), list) or not receipt['evidence']:
                return False
            for evidence in receipt['evidence']:
                if not isinstance(evidence, dict) or set(evidence) != {'path', 'sha256'}:
                    return False
                witness, _ = self._source(evidence['path'])
                if witness['sha256'] != evidence['sha256']:
                    return False
            if receipt.get('claim_id') is not None:
                claim = state['claims'].get(receipt['claim_id'])
                if not claim or (receipt.get('kind') == 'retraction' and claim['status'] != 'retracted'):
                    return False
                if receipt.get('kind') == 'progress':
                    records = self.cycle(state, claim['cycle'])['checks']
                    if claim.get('kind') != 'fact' or not any(r['id'] == claim.get('check_id') and r['passed'] for r in records):
                        return False
            return True

        def _reconcile(self, state, policy, window):
            if 'inventory' not in policy:
                return {'applicable': False, 'passed': True, 'reason': 'No inventory policy declared; no arithmetic coverage asserted'}, []
            config = policy['inventory']
            categories = config['categories']
            previous, baseline = self._observation(policy, window['start'] - 1)
            if window['start'] - 1 == policy['anchor']:
                require(baseline == state['periodic_guard'].get('baseline'), 'DIGEST_SOURCE', 'The initial inventory baseline changed after the contract was established')
            else:
                self._pinned_source(state, window['start'] - 1, baseline)
            sources = [baseline]
            issues, rows, retractions = [], [], []
            all_facts = set(previous.get('facts_recorded', [])) | set(previous.get('facts_used', []))
            universe = set(previous['closed'])
            rank = {name: position for position, name in enumerate(categories)}
            require(len(universe) == config['total'] and previous['live'] == previous['closed'] and all(x in rank for x in previous['closed'].values()),
                    'RECONCILIATION_FAILED', 'Baseline does not match the declared inventory universe and denominator')
            last_used = set()
            for cid in range(window['start'], window['end'] + 1):
                value, witness = self._observation(policy, cid)
                sources.append(witness)
                live, closed = value['live'], value['closed']
                counts = {name: sum(x == name for x in closed.values()) for name in categories}
                unknown = [key for key, val in closed.items() if val not in rank]
                flags = []
                if len(closed) != config['total'] or sum(counts.values()) != config['total']:
                    flags.append('conservation')
                if set(closed) != universe:
                    flags.append('universe_changed')
                if unknown:
                    flags.append('unmarked_categories')
                if live != closed:
                    flags.append('live_close_mismatch')
                unmarked, regressions, corrected = [], [], []
                receipts = value.get('transitions', [])
                changed = {key for key in universe & set(closed) if previous['closed'].get(key) != closed[key]}
                receipt_ids = [r['id'] for r in receipts if isinstance(r, dict) and nonempty(r.get('id'))]
                if len(receipt_ids) != len(receipts) or len(set(receipt_ids)) != len(receipt_ids) or not set(receipt_ids) <= changed:
                    flags.append('invalid_transition_receipts')
                for identifier in sorted(universe & set(closed)):
                    old, new = previous['closed'].get(identifier), closed[identifier]
                    if old == new or old not in rank or new not in rank:
                        continue
                    kind = 'progress' if rank[new] > rank[old] else 'retraction'
                    valid = any(r.get('kind') == kind and self._receipt(r, identifier, old, new, state)
                                for r in receipts if isinstance(r, dict))
                    if kind == 'progress' and not valid:
                        unmarked.append(identifier)
                    elif kind == 'retraction':
                        (corrected if valid else regressions).append(identifier)
                if unmarked:
                    flags.append('unmarked_promotions')
                if regressions:
                    flags.append('unexplained_regression')
                deltas = {name: sum(counts[x] for x in group) - sum(x in group for x in previous['closed'].values())
                          for name, group in config['monotonic'].items()}
                if any(delta < 0 for delta in deltas.values()) and not corrected:
                    flags.append('monotonicity')
                rows.append({'cycle': cid, 'counts': counts, 'total': len(closed), 'unmarked_promotions': unmarked,
                             'regressions': regressions, 'justified_retractions': corrected, 'metric_deltas': deltas,
                             'coverage': {name: {'numerator': sum(counts[x] for x in group), 'denominator': config['total'],
                                                'percent': round(100 * sum(counts[x] for x in group) / config['total'], 6)}
                                          for name, group in config['monotonic'].items()},
                             'issues': flags, 'live_equals_closed': live == closed})
                issues.extend({'cycle': cid, 'kind': flag} for flag in flags)
                retractions.extend({'cycle': cid, 'id': key} for key in corrected)
                all_facts.update(value.get('facts_recorded', []))
                last_used = set(value.get('facts_used', []))
                previous = value
            return {'applicable': True, 'passed': not issues, 'declared_total': config['total'], 'cycles': rows,
                    'issues': issues, 'justified_retractions': retractions, 'possible_losses': sorted(all_facts - last_used),
                    'semantic_correctness_verified': False, 'claim_promotion_authorized': False}, sources

        def _build_digest(self, state, through):
            policy = state['mission']['periodic_review']
            window = self._window(policy, through)
            require(through <= len(state['cycles']) and window['start'] > policy['anchor'], 'DIGEST_WINDOW', 'Choose a complete existing N-cycle window')
            notes = []
            for cid in range(window['start'], through + 1):
                witness, raw = self._source(policy['notes_pattern'].format(cycle=cid))
                if self.cycle(state, cid)['status'] != 'active':
                    self._pinned_source(state, cid, witness)
                notes.append({'cycle': cid, **witness, 'text': raw.decode('utf-8')})
            require(len({n['path'] for n in notes}) == policy['every'], 'DIGEST_SOURCE', 'Each cycle requires its own physical note')
            paths = [self.project_file(n['path']) for n in notes]
            require(not any(os.path.samefile(a, b) for i, a in enumerate(paths) for b in paths[i + 1:]), 'DIGEST_SOURCE', 'Cycle notes cannot alias one physical file')
            reconciliation, sources = self._reconcile(state, policy, window)
            for source in sources:
                for cid in range(window['start'], through + 1):
                    if source['path'] == policy.get('observation_pattern', '').format(cycle=cid) and self.cycle(state, cid)['status'] != 'active':
                        self._pinned_source(state, cid, source)
            cycles = state['cycles'][window['start'] - 1:through]
            payload = {'format': 'verimission-digest-v1', 'mission_hash': state['mission_hash'], 'window': window,
                       'notes': notes, 'sources': sources, 'reconciliation': reconciliation,
                       'cycle_evidence': [{'id': c['id'], 'criteria': c['criteria'], 'checks': [r['id'] for r in c['checks']]} for c in cycles],
                       'claims': {key: {'status': c['status'], 'cycle': c['cycle']} for key, c in state['claims'].items() if window['start'] <= c['cycle'] <= through},
                       'reread_required': True, 'semantic_correctness_verified': False, 'mission_change_authorized': False}
            packet = {**payload, 'digest_sha256': digest(payload)}
            return packet

        def _atomic(self, relative, raw):
            path = self.project_file(relative, exists=False)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                with temporary.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()

        def _digest_state(self, state, through):
            packet = self._build_digest(state, through)
            policy = state['mission']['periodic_review']
            output = policy['digest_pattern'].format(**packet['window'])
            require(output not in {policy['governing_file'], *[n['path'] for n in packet['notes']], *[s['path'] for s in packet['sources']]},
                    'PROTECTED_OUTPUT', 'A digest cannot overwrite its physical inputs or governing instructions')
            raw = (json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
            path = self.project_file(output, exists=False)
            known = state.setdefault('digests', {})
            if path.exists() and path.read_bytes() != raw:
                require(any(r['output'] == output and r['output_sha256'] == file_digest(path) for r in known.values()),
                        'DIGEST_DRIFT', 'Refusing to overwrite an unrelated or modified digest')
            if not path.exists() or path.read_bytes() != raw:
                self._atomic(output, raw)
            record = {'digest_sha256': packet['digest_sha256'], 'window': packet['window'], 'output': output,
                      'output_sha256': hashlib.sha256(raw).hexdigest(), 'packet': packet, 'mission_hash': state['mission_hash']}
            if packet['digest_sha256'] not in known:
                known[packet['digest_sha256']] = record
                self.event(state, 'digest-produced', through, {'window': packet['window'], 'digest_sha256': packet['digest_sha256'],
                           'passed': packet['reconciliation']['passed'], 'notes_physically_read': len(packet['notes'])})
            key = f"{state['mission_hash']}:{through}"
            state.setdefault('digest_windows', {})[key] = packet['digest_sha256']
            require(packet['reconciliation']['passed'], 'RECONCILIATION_FAILED', 'Digest records failed consistency checks; repair the source evidence before reviewing')
            return record

        def _digest_result(self, record):
            packet = record['packet']
            result = {'applicable': True, 'digest_sha256': record['digest_sha256'], 'window': record['window'], 'output': record['output'],
                    'notes': [{k: v for k, v in n.items() if k != 'text'} for n in packet['notes']],
                    'reconciliation': packet['reconciliation'], 'reread_required': True, 'semantic_correctness_verified': False}
            with self.state() as current:
                path = self.project_file(current['mission']['periodic_review']['governing_file'], exists=False)
                result['review_template'] = {'window': record['window'], 'digest_sha256': record['digest_sha256'],
                    'prompt_sha256': file_digest(path) if path.is_file() else None,
                    'reread': [{'cycle': n['cycle'], 'sha256': n['sha256'], 'finding': ''} for n in packet['notes']],
                    'updates': {}, 'reason': '', 'loss_acknowledgements': [{'id': name, 'reason': ''} for name in packet['reconciliation'].get('possible_losses', [])]}
            return result

        def digest(self, through=None):
            with self.state() as state:
                policy = state['mission'].get('periodic_review')
                through = len(state['cycles']) if through is None else through
                if not self._due(policy, through):
                    return {'applicable': False, 'reason': 'Not a configured cycle boundary'}
            failure = None
            with self.state(write=True) as state:
                self.contract_valid(state)
                try:
                    result = self._digest_result(self._digest_state(state, through))
                except Refusal as error:
                    self.event(state, 'digest-failed', through, {'code': error.code, 'window': self._window(policy, through)})
                    failure = error
            if failure:
                raise failure
            return result

        def _current_digest(self, state, through):
            identifier = state.get('digest_windows', {}).get(f"{state['mission_hash']}:{through}")
            record = state.get('digests', {}).get(identifier)
            require(record is not None, 'DIGEST_REQUIRED', 'Produce the digest for this exact boundary first')
            path = self.project_file(record['output'], exists=False)
            require(path.is_file(), 'DIGEST_REQUIRED', 'The registered digest artifact is missing')
            require(file_digest(path) == record['output_sha256'], 'DIGEST_DRIFT', 'Digest bytes or declared window changed')
            packet = self._json(path.read_bytes())
            window = self._window(state['mission']['periodic_review'], through)
            require(packet.get('window') == record['window'] == window, 'DIGEST_WINDOW', 'Digest and review must cover the same N-cycle window')
            for source in [*packet['notes'], *packet['sources']]:
                witness, _ = self._source(source['path'])
                require(witness['sha256'] == source['sha256'], 'DIGEST_STALE', 'A physical source changed after digest production')
            fresh = self._build_digest(state, through)
            # Later retractions legitimately change current claim status. A
            # historical digest is not rewritten into a competing current ledger.
            relevant = lambda p: {key: p[key] for key in ('mission_hash', 'window', 'notes', 'sources', 'reconciliation', 'cycle_evidence')}
            require(relevant(fresh) == relevant(packet), 'DIGEST_STALE', 'Physical notes, observations or cycle evidence changed; regenerate and reread')
            require(packet['reconciliation']['passed'], 'RECONCILIATION_FAILED', 'A failed digest cannot authorize a review')
            return record

        def _review_state(self, state, through, proposal):
            require(through == len(state['cycles']), 'REVIEW_WINDOW', 'A historical boundary cannot retarget a later active or closed cycle')
            policy = state['mission']['periodic_review']
            record = self._current_digest(state, through)
            text, spans = self._guard(state)
            before = hashlib.sha256(text.encode('utf-8')).hexdigest()
            previous = state.get('periodic_reviews', {}).get(record['digest_sha256'])
            if proposal is None:
                require(previous and previous['after_prompt_sha256'] == before, 'PERIODIC_REVIEW_REQUIRED',
                        'Read every physical note and submit an objectives/scenario review; production is not semantic rereading')
                return previous
            fields = {'window', 'digest_sha256', 'prompt_sha256', 'reread', 'updates', 'reason', 'loss_acknowledgements'}
            require(isinstance(proposal, dict) and set(proposal) == fields and proposal['window'] == record['window']
                    and proposal['digest_sha256'] == record['digest_sha256'], 'REVIEW_INPUT', 'Use the exact review template for the current digest/window')
            require(proposal['prompt_sha256'] == before, 'REVIEW_STALE', 'Governing instructions changed after the proposal')
            require(nonempty(proposal['reason']), 'REVIEW_INPUT', 'Explain the review decision, including an unchanged decision')
            notes = {n['cycle']: n for n in record['packet']['notes']}
            rows = proposal['reread']
            require(isinstance(rows, list) and len(rows) == len(notes) and all(isinstance(r, dict) and set(r) == {'cycle', 'sha256', 'finding'} and type(r['cycle']) is int for r in rows),
                    'REREAD_REQUIRED', 'Declare one substantive reread finding for every physical note')
            require(len({r['cycle'] for r in rows}) == len(notes) and all(r['cycle'] in notes and r['sha256'] == notes[r['cycle']]['sha256'] and nonempty(r['finding']) for r in rows),
                    'REREAD_REQUIRED', 'Reread declarations must cover every note exactly once with matching hashes')
            losses = record['packet']['reconciliation'].get('possible_losses', [])
            acknowledgements = proposal['loss_acknowledgements']
            require(isinstance(acknowledgements, list) and all(isinstance(r, dict) and set(r) == {'id', 'reason'} and nonempty(r['id']) and nonempty(r['reason']) for r in acknowledgements)
                    and {r['id'] for r in acknowledgements} == set(losses), 'LOSS_REVIEW_REQUIRED', 'Explain every recorded fact that is no longer used; do not silently drop it')
            updates = proposal['updates']
            require(isinstance(updates, dict) and set(updates) <= {'objectives', 'scenario'} and all(nonempty(v) for v in updates.values()),
                    'REVIEW_INPUT', 'Only nonempty objectives/scenario replacements are accepted')
            candidate = text
            changes = {}
            for a, b, key in reversed(spans):
                if key in updates:
                    if text[a:b] != updates[key]:
                        changes[key] = {'before': text[a:b], 'after': updates[key]}
                    candidate = candidate[:a] + updates[key] + candidate[b:]
            _, protected = self._layout(policy, candidate)
            require(protected == state['periodic_guard']['protected_sha256'], 'CORE_CHANGED', 'Review cannot modify protected instructions')
            require(not any(marker in candidate for marker in policy['stale_markers']), 'STALE_REFERENCES', 'Stale references remain; update them only inside the allowed sections')
            require(file_digest(self.project_file(policy['governing_file'])) == before, 'REVIEW_STALE', 'Instructions changed before replacement')
            after = hashlib.sha256(candidate.encode('utf-8')).hexdigest()
            if candidate != text:
                self._atomic(policy['governing_file'], candidate.encode('utf-8'))
            state['periodic_guard']['trusted_prompt'] = candidate
            result = {'window': record['window'], 'digest_sha256': record['digest_sha256'], 'before_prompt_sha256': before,
                      'after_prompt_sha256': after, 'updated_sections': sorted(changes), 'changes': changes, 'reread': copy.deepcopy(rows),
                      'reason': proposal['reason'], 'loss_acknowledgements': copy.deepcopy(acknowledgements), 'at': now(),
                      'tripwire_passed': True, 'reread_is_declared_not_authenticated': True, 'mission_changed': False}
            state.setdefault('periodic_reviews', {})[record['digest_sha256']] = result
            self.event(state, 'periodic-review-passed', through, result)
            return result

        def decade_review(self, through=None, proposal=None):
            with self.state() as state:
                through = len(state['cycles']) if through is None else through
                policy = state['mission'].get('periodic_review')
                if not self._due(policy, through):
                    return {'applicable': False, 'reason': 'Not a configured cycle boundary'}
            failure = None
            with self.state(write=True) as state:
                self.contract_valid(state)
                try:
                    result = self._review_state(state, through, proposal)
                except Refusal as error:
                    self.event(state, 'periodic-review-failed', through, {'code': error.code, 'window': self._window(policy, through), 'tripwire_passed': self._tripwire_outcome(error.code)})
                    failure = error
            if failure:
                raise failure
            return {'applicable': True, 'passed': True, **result}

        def restore_prompt(self):
            with self.state(write=True) as state:
                self.contract_valid(state)
                policy = state['mission'].get('periodic_review')
                require(policy, 'PERIODIC_POLICY', 'No governing prompt is configured')
                guard = state.get('periodic_guard', {})
                require(guard.get('mission_hash') == state['mission_hash'], 'PERIODIC_POLICY', 'No trusted snapshot for this contract')
                trusted = guard['trusted_prompt']
                _, protected = self._layout(policy, trusted)
                require(protected == guard['protected_sha256'], 'CORE_CHANGED', 'Trusted snapshot failed validation')
                path = self.project_file(policy['governing_file'], exists=False)
                damaged = path.read_bytes() if path.exists() else b''
                repair = {'at': now(), 'path': policy['governing_file'], 'before_sha256': hashlib.sha256(damaged).hexdigest(),
                          'damaged_base64': base64.b64encode(damaged).decode('ascii'), 'after_sha256': hashlib.sha256(trusted.encode()).hexdigest()}
                self._atomic(policy['governing_file'], trusted.encode('utf-8'))
                state.setdefault('prompt_repairs', []).append(repair)
                self.event(state, 'prompt-restored', policy['governing_file'], {k: v for k, v in repair.items() if k != 'damaged_base64'})
                return {'restored': True, 'damaged_version_preserved_in_yaml': True, 'sha256': repair['after_sha256']}

        def periodic_close(self, state, cycle, proposal, outcome='verified'):
            policy = state['mission'].get('periodic_review')
            if not self._due(policy, cycle['id']):
                try:
                    require(proposal is None, 'REVIEW_INPUT', 'Review input applies only at a configured boundary')
                    if policy:
                        self._guard(state)
                        self._pin_cycle(state, cycle['id'])
                except Refusal as error:
                    self.event(state, 'periodic-review-failed', cycle['id'], {'code': error.code, 'applicable': False, 'tripwire_passed': self._tripwire_outcome(error.code)})
                    return {'blocked': True, 'code': error.code, 'detail': error.detail}
                return {}
            try:
                record = self._digest_state(state, cycle['id'])
                result = self._review_state(state, cycle['id'], proposal)
                if outcome == 'verified':
                    for cid in cycle['criteria']:
                        self.current_check(state, cycle, cid)
                audit = super().validate()
                require(audit['passed'], 'STORE_INVALID', 'Existing evidence must be valid before automatic consolidation')
                self._pin_cycle(state, cycle['id'])
                return {'periodic_review': result, 'digest_sha256': record['digest_sha256'], 'audit': audit}
            except Refusal as error:
                kind = 'periodic-review-pending' if error.code == 'PERIODIC_REVIEW_REQUIRED' else 'periodic-review-failed'
                self.event(state, kind, cycle['id'], {'window': self._window(policy, cycle['id']), 'code': error.code,
                                                    'tripwire_passed': self._tripwire_outcome(error.code)})
                return {'blocked': True, 'code': error.code, 'detail': error.detail}

        @staticmethod
        def _tripwire_outcome(code):
            if code == 'CORE_CHANGED':
                return False
            if code in {'PERIODIC_REVIEW_REQUIRED', 'REVIEW_INPUT', 'REVIEW_STALE', 'REREAD_REQUIRED', 'LOSS_REVIEW_REQUIRED',
                        'STALE_REFERENCES', 'EVIDENCE', 'STALE_ARTIFACT', 'STORE_INVALID'}:
                return True
            return None  # Not reached; absence of a test is not a passing test.

        def _pin_cycle(self, state, cycle):
            policy = state['mission']['periodic_review']
            witnesses = [self._source(policy['notes_pattern'].format(cycle=cycle))[0]]
            if 'observation_pattern' in policy:
                witnesses.append(self._source(policy['observation_pattern'].format(cycle=cycle))[0])
            key = f"{state['mission_hash']}:{cycle}"
            previous = state.setdefault('cycle_sources', {}).get(key)
            require(previous is None or previous == witnesses, 'DIGEST_SOURCE', 'Closed-cycle source hashes cannot be silently replaced')
            state['cycle_sources'][key] = witnesses
            self.event(state, 'cycle-sources-pinned', cycle, {'sources': witnesses})

        def _pinned_source(self, state, cycle, witness):
            key = f"{state['mission_hash']}:{cycle}"
            require(witness in state.get('cycle_sources', {}).get(key, []), 'DIGEST_SOURCE', 'A closed-cycle source is missing its original hash or was changed')

        def periodic_interrupt(self, state, cycle):
            if state['mission'].get('periodic_review'):
                try:
                    self._pin_cycle(state, cycle)
                except Refusal as error:
                    self.event(state, 'interrupted-sources-unavailable', cycle, {'code': error.code})

        def finish_periodic_close(self, state, cycle, boundary):
            if not boundary:
                return
            previous = state['consolidations'][-1]['through_cycle'] if state['consolidations'] else 0
            cycles = state['cycles'][previous:cycle['id']]
            state['consolidations'].append({'at': now(), 'through_cycle': cycle['id'], 'cycle_ids_read': [c['id'] for c in cycles],
                'cycle_records_sha256': digest(cycles), 'audit': boundary['audit'], 'digest_sha256': boundary['digest_sha256'],
                'note': {'failures_and_dead_ends': [c['id'] for c in cycles if c['status'] != 'verified'],
                         'retractions_and_repairs': boundary['periodic_review']['loss_acknowledgements'],
                         'established_facts': [key for key, c in state['claims'].items() if c['status'] == 'verified' and previous < c['cycle'] <= cycle['id']],
                         'open_questions': ['Review declarations and arithmetic do not prove semantic truth'],
                         'patterns_and_actions': [boundary['periodic_review']['reason']]}})
            self.event(state, 'periodic-consolidation', cycle['id'], {'digest_sha256': boundary['digest_sha256']})

        def start(self, plan):
            with self.state() as state:
                policy = state['mission'].get('periodic_review')
                if policy:
                    self.contract_valid(state)
                    self._guard(state)
                    for through in range(policy['anchor'] + policy['every'], len(state['cycles']) + 1, policy['every']):
                        if self.cycle(state, through)['status'] == 'active':
                            continue
                        identifier = state.get('digest_windows', {}).get(f"{state['mission_hash']}:{through}")
                        require(identifier in state.get('periodic_reviews', {}), 'PERIODIC_REVIEW_REQUIRED', 'An interrupted or unreviewed boundary cannot be bypassed')
                return super().start(plan)

        def validate_operation_boundary(self, state, cycle_id, criterion=None, closing=False):
            if state['mission'].get('periodic_review') and not closing:
                self._guard(state)
            return super().validate_operation_boundary(state, cycle_id, criterion, closing)

        def operation_binding(self, state, operation):
            if state['mission'].get('periodic_review'):
                self._guard(state)
            return super().operation_binding(state, operation)

        def validate(self):
            result = super().validate()
            with self.state() as state:
                if state['mission'].get('periodic_review'):
                    try:
                        self._guard(state)
                    except Refusal as error:
                        result['issues'].append({'kind': error.code})
                    policy = state['mission']['periodic_review']
                    for through in range(policy['anchor'] + policy['every'], len(state['cycles']) + 1, policy['every']):
                        if self.cycle(state, through)['status'] == 'active':
                            continue
                        try:
                            record = self._current_digest(state, through)
                            require(record['digest_sha256'] in state.get('periodic_reviews', {}), 'PERIODIC_REVIEW_REQUIRED', 'Boundary review missing')
                        except Refusal as error:
                            result['issues'].append({'kind': error.code, 'cycle': through})
            result['passed'] = not result['issues']
            return result

        def capabilities(self):
            result = super().capabilities()
            result['v82'] = {'native_digest': True, 'domain_plugin_required': False, 'cycle_boundary_review': True,
                             'protected_prompt_sections': True, 'reread_declaration_authenticates_cognition': False,
                             'automatic_mission_revision': False}
            return result

        def resume(self):
            with self.state() as state:
                result = super().resume()
                policy = state['mission'].get('periodic_review')
                if policy:
                    pending = []
                    for through in range(policy['anchor'] + policy['every'], len(state['cycles']) + 1, policy['every']):
                        identifier = state.get('digest_windows', {}).get(f"{state['mission_hash']}:{through}")
                        if identifier not in state.get('periodic_reviews', {}):
                            pending.append(through)
                    next_boundary = policy['anchor'] + (max(0, len(state['cycles']) - policy['anchor']) // policy['every'] + 1) * policy['every']
                    result['periodic_review'] = {'every': policy['every'], 'anchor': policy['anchor'],
                        'next_boundary': min(pending) if pending else next_boundary, 'pending_boundaries': pending,
                        'digest_count': len(state.get('digests', {})), 'review_count': len(state.get('periodic_reviews', {})),
                        'reread_is_declared_not_authenticated': True, 'domain_plugin_required': False}
                return result

    return Harness82
