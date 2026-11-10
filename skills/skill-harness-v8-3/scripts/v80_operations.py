"""Optional governed local command adapter. Does not intercept host tools."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import uuid


def extend(Base, require, digest, now, file_digest, nonempty, Refusal, human_input):
    class GovernedHarness(Base):
        def operation_binding(self, state, operation):
            cycle = self.cycle(state, operation['cycle'])
            require(cycle['mission_hash'] == state['mission_hash'], 'MISSION_CHANGED', 'Operation belongs to another contract')
            require(cycle['status'] == 'active', 'OPERATION_STATE', 'Operation cycle must still be active')
            criterion = self.criterion(state, operation['criterion'])
            fields = {key: operation[key] for key in ('id', 'cycle', 'criterion', 'effect', 'risk', 'reason', 'request_ref')}
            fields.update(mission_hash=state['mission_hash'], argv=criterion['argv'],
                          artifacts={name: file_digest(self.project_file(name)) for name in criterion.get('artifacts', [])})
            return digest(fields)

        def operation_prepare(self, entry):
            fields = {'id', 'cycle', 'criterion', 'effect', 'risk', 'reason', 'request_ref'}
            require(isinstance(entry, dict) and set(entry) == fields and all(nonempty(entry.get(k)) for k in ('id', 'criterion', 'reason', 'request_ref')),
                    'OPERATION', 'Use the exact template; argv comes only from the approved acceptance contract')
            require(entry['effect'] in ('local', 'external') and entry['risk'] in ('read', 'write', 'destructive', 'publish'), 'OPERATION', 'Declare effect and risk; labels do not prove safety')
            with self.state(write=True) as state:
                self.contract_valid(state)
                cycle = self.cycle(state, entry['cycle'])
                require(cycle['status'] == 'active' and entry['criterion'] in cycle['criteria'], 'OPERATION', 'Bind the operation to an active cycle and its selected criterion')
                operations = state.setdefault('operations', {})
                require(entry['id'] not in operations, 'OPERATION', 'Operation IDs are single-use; previous records cannot be replaced')
                operation = {**entry, 'status': 'prepared', 'created': now(), 'approval': None, 'checkpoints': []}
                operation['binding'] = self.operation_binding(state, operation)
                operations[entry['id']] = operation
                self.event(state, 'operation-prepared', entry['id'], {'effect_declared': entry['effect'], 'risk_declared': entry['risk']})
                return {'id': entry['id'], 'status': 'prepared', 'approval_required': True, 'executed': False}

        def operation_status(self, identifier):
            with self.state() as state:
                operation = state.get('operations', {}).get(identifier)
                require(operation is not None, 'OPERATION', 'Unknown operation')
                return {**operation, 'confirmation': 'AUTORIZAR ' + operation['binding'][:12],
                        'approval_consumed': bool(operation.get('approval', {}).get('consumed')) if operation.get('approval') else False,
                        'reconciliation_required': operation['status'] in ('running', 'unknown'),
                        'limit': 'A running checkpoint may be live or interrupted. Inspect the actual process/external outcome before reconciling; never replay an unknown operation.'}

        def operation_approve(self, identifier):
            with self.state() as state:
                operation = state.get('operations', {}).get(identifier)
                require(operation and operation['status'] == 'prepared' and not operation['approval'], 'OPERATION_STATE', 'Approve a prepared, unapproved operation only')
                binding = self.operation_binding(state, operation)
                require(binding == operation['binding'], 'APPROVAL_STALE', 'Operation inputs changed; prepare a new concrete request')
                preview = {'id': identifier, 'argv': self.criterion(state, operation['criterion'])['argv'],
                           'effect_declared': operation['effect'], 'risk_declared': operation['risk'], 'reason': operation['reason'],
                           'confirmation': 'AUTORIZAR ' + binding[:12], 'limit': 'Single operation only; no mission revision or standing permission is granted.'}
            require(sys.stdin.isatty() and sys.stdout.isatty(), 'INTERACTIVE_REQUIRED', 'A human must confirm the concrete operation in an interactive terminal')
            require(all(os.environ.get(key, '').strip().casefold() in ('', '0', 'false', 'no') for key in ('CI', 'HARNESS_AUTOMATION')), 'AUTOMATION_FORBIDDEN', 'Automation cannot create human approvals')
            print(json.dumps(preview, ensure_ascii=True, indent=2))
            try:
                confirmation = human_input('User: type ' + preview['confirmation'] + ' to authorize this exact operation: ')
            except (EOFError, KeyboardInterrupt):
                raise Refusal('CONFIRMATION', 'Operation approval cancelled')
            require(confirmation == preview['confirmation'], 'CONFIRMATION', 'Exact human confirmation is required')
            with self.state(write=True) as state:
                current = state['operations'][identifier]
                require(current['status'] == 'prepared' and not current['approval'] and self.operation_binding(state, current) == binding, 'APPROVAL_STALE', 'Operation changed while approval was pending')
                current['approval'] = {'at': now(), 'binding': binding, 'confirmed_interactively': True, 'consumed': False}
                self.event(state, 'operation-approved', identifier)
                return {'approved': identifier, 'single_use': True, 'mission_revision_authorized': False}

        def operation_issues(self, state, cycle_id=None):
            issues = []
            for operation in state.get('operations', {}).values():
                if cycle_id is not None and operation['cycle'] != cycle_id:
                    continue
                if operation['status'] in ('prepared', 'running', 'unknown'):
                    issues.append({'id': operation['id'], 'kind': 'unresolved'})
                if operation['status'] == 'reconciled':
                    original_cycle = self.cycle(state, operation['cycle'])
                    if original_cycle['mission_hash'] != state['mission_hash']:
                        continue  # The user explicitly revised the contract; preserve this reconciliation as history.
                    reverified = False
                    for cycle in state['cycles']:
                        if cycle['mission_hash'] != state['mission_hash'] or operation['criterion'] not in cycle['criteria']:
                            continue
                        try:
                            check = self.current_check(state, cycle, operation['criterion'])
                            if cycle['status'] in ('active', 'verified') and check['at'] > operation['reconciliation']['at']:
                                reverified = True
                                break
                        except (Refusal, OSError):
                            continue
                    if not reverified:
                        issues.append({'id': operation['id'], 'kind': 'recheck_required'})
            return issues

        def validate_task_cycle(self, state, plan):
            super().validate_task_cycle(state, plan)
            require(not any(op['status'] in ('running', 'unknown') for op in state.get('operations', {}).values()), 'OPERATION_PENDING', 'Reconcile interrupted/unknown operations before starting another execution')

        def validate_operation_boundary(self, state, cycle_id, criterion=None, closing=False):
            operations = [op for op in state.get('operations', {}).values() if op['cycle'] == cycle_id]
            if closing:
                issues = self.operation_issues(state, cycle_id)
                require(not any(issue['kind'] == 'unresolved' for issue in issues), 'OPERATION_PENDING', 'Resolve pending or unknown operations before verified closure')
                require(not issues, 'OPERATION_RECHECK', 'Reconciliation does not grant verification; execute a fresh check')
            else:
                require(not any(op['status'] in ('running', 'unknown') or (op['status'] == 'prepared' and op['criterion'] == criterion) for op in operations),
                        'OPERATION_PENDING', 'Use the approved operation adapter or reconcile the unknown outcome; direct check cannot bypass a pending governed operation')

        def operation_run(self, identifier):
            with self.state(write=True) as state:
                self.contract_valid(state)
                operation = state.get('operations', {}).get(identifier)
                require(operation and operation['status'] == 'prepared', 'OPERATION_STATE', 'Operation cannot be replayed; inspect its checkpoint')
                approval = operation.get('approval')
                require(approval and not approval['consumed'], 'APPROVAL_REQUIRED', 'Concrete single-use human approval required')
                require(self.operation_binding(state, operation) == operation['binding'] == approval['binding'], 'APPROVAL_STALE', 'Approved resources, command or contract changed')
                require(not any(op['status'] in ('running', 'unknown') for op in state['operations'].values()), 'OPERATION_PENDING', 'Another outcome is unresolved')
                cycle = self.cycle(state, operation['cycle'])
                require(cycle['status'] == 'active', 'OPERATION_STATE', 'Execution cycle is no longer active')
                criterion = self.criterion(state, operation['criterion'])
                remaining = state['mission']['budget']['max_cycle_seconds'] - (datetime.now(timezone.utc) - datetime.fromisoformat(cycle['started'])).total_seconds()
                require(remaining > 0, 'TIMEBOX', 'Cycle timebox exceeded')
                timeout = min(remaining, state['mission']['budget']['max_check_seconds'])
                preservation = self.regression_prepare(state, cycle, criterion) if hasattr(self, 'regression_prepare') else None
                if preservation:
                    preservation['env']['VERIMISSION_TIMEOUT'] = str(timeout)
                artifacts = {name: file_digest(self.project_file(name)) for name in criterion.get('artifacts', [])}
                argv, cycle_id, criterion_id = criterion['argv'], cycle['id'], criterion['id']
                execution_argv = preservation['argv'] if preservation else argv
                checkpoint = {'at': now(), 'phase': 'admitted_before_launch', 'cycle': cycle_id, 'criterion': criterion_id,
                              'state_before_sha256': digest(state), 'artifact_preconditions': artifacts, 'argv_sha256': digest(argv)}
                operation['checkpoints'].append(checkpoint)
                operation.update(status='running', admitted=now())
                approval['consumed'] = True
                self.event(state, 'operation-admitted', identifier)
            # Admission is committed before launch. If this process dies at any
            # point before completion commits, the next session MUST reconcile.
            started = time.monotonic()
            try:
                result = subprocess.run(execution_argv, cwd=self.root, shell=False, capture_output=True, timeout=timeout,
                                        env=preservation['env'] if preservation else None)
                exit_code, outcome = result.returncode, 'executed'
                output_hash = hashlib.sha256(result.stdout + b'\x00' + result.stderr).hexdigest()
            except subprocess.TimeoutExpired:
                exit_code, outcome, output_hash = None, 'timeout', None
            except OSError:
                exit_code, outcome, output_hash = None, 'launch_failed', None
            try:
                unchanged = all(file_digest(self.project_file(name)) == value for name, value in artifacts.items())
            except (OSError, Refusal):
                unchanged = False
            check = {'id': str(uuid.uuid4()), 'criterion': criterion_id, 'at': now(), 'argv_hash': digest(argv),
                     'exit_code': exit_code, 'outcome': outcome, 'seconds': time.monotonic() - started,
                     'passed': exit_code == 0 and unchanged, 'artifacts': artifacts, 'output_sha256': output_hash}
            with self.state(write=True) as state:
                operation = state['operations'][identifier]
                cycle = self.cycle(state, cycle_id)
                require(operation['status'] == 'running' and cycle['status'] == 'active', 'OPERATION_CONFLICT', 'Execution was interrupted/reconciled concurrently; inspect the actual outcome before proceeding')
                cycle['checks'].append(check)
                if hasattr(self, 'regression_finish'):
                    self.regression_finish(state, cycle, check, preservation)
                operation.update(status='unknown' if outcome == 'timeout' else 'completed', result=check)
                operation['checkpoints'].append({'at': now(), 'phase': 'result_recorded', 'check_id': check['id'], 'outcome': outcome})
                self.event(state, 'operation-result', identifier, {'outcome': outcome, 'exit_code': exit_code, 'passed': check['passed']})
            return {'id': identifier, 'check': check, 'reconciliation_required': outcome == 'timeout'}

        def operation_reconcile(self, entry):
            require(set(entry) == {'id', 'outcome', 'evidence', 'reason'} and entry['outcome'] in ('completed', 'failed', 'not_executed', 'abandoned') and nonempty(entry['reason']),
                    'RECONCILIATION', 'Record an observed outcome, reason and evidence; never replay to discover whether it happened')
            proof = file_digest(self.project_file(entry['evidence']))
            with self.state(write=True) as state:
                operation = state.get('operations', {}).get(entry['id'])
                require(operation and operation['status'] in ('prepared', 'running', 'unknown'), 'OPERATION_STATE', 'Reconcile an unresolved operation only; first ensure no live process is still executing')
                operation.update(status='reconciled', reconciliation={**entry, 'at': now(), 'evidence_sha256': proof, 'verification_granted': False})
                self.event(state, 'operation-reconciled', entry['id'], {'outcome_declared': entry['outcome']})
                return {'reconciled': entry['id'], 'verification_granted': False, 'next': 'Execute the relevant fresh acceptance check; reconciliation does not fabricate a passing result.'}

        def usage_report(self, entry):
            require(set(entry) == {'id', 'source', 'model', 'tokens', 'usd', 'reference'} and all(nonempty(entry.get(key)) for key in ('id', 'model', 'reference')),
                    'USAGE', 'Identify usage source and evidence reference')
            require(entry['source'] in ('measured', 'provider_reported', 'agent_reported', 'estimated') and type(entry['tokens']) is int and entry['tokens'] >= 0 and
                    type(entry['usd']) in (int, float) and math.isfinite(entry['usd']) and entry['usd'] >= 0, 'USAGE', 'Usage must be finite and nonnegative with explicit provenance')
            with self.state(write=True) as state:
                usage = state.setdefault('usage_reports', {})
                require(entry['id'] not in usage, 'USAGE', 'Preserve original usage records')
                usage[entry['id']] = {**entry, 'at': now(), 'source_authenticated_by_harness': False}
                return usage[entry['id']]

        def trace(self):
            with self.state() as state:
                return {'events': state.get('events', []), 'operations': [
                    {'id': op['id'], 'status': op['status'], 'cycle': op['cycle'], 'criterion': op['criterion'], 'effect_declared': op['effect'], 'risk_declared': op['risk'], 'checkpoints': op['checkpoints']}
                    for op in state.get('operations', {}).values()], 'usage': list(state.get('usage_reports', {}).values()),
                    'all_runtime_tools_observed': False,
                    'coverage': ['harness cycle/check audit', 'registered tasks', 'governed local command adapter'],
                    'not_covered': ['direct host tools', 'browser actions', 'unadapted MCP tools', 'model calls not reported by the client'],
                    'limit': 'Local metadata only; no raw tool output or automatic external telemetry. Reported labels and usage are not automatically authenticated.'}

        def capabilities(self):
            return {'core': ['legacy_v79_controls', 'task_graph', 'derived_fts_search', 'requirements_traceability', 'task_context', 'diagnostics', 'final_assessment'],
                    'adapter': 'optional_governed_local_command', 'host_tools_intercepted': False,
                    'human_approval': 'interactive_single_operation_bound_to_command_contract_and_declared_artifacts',
                    'checkpoint_recovery': 'explicit_reconciliation_no_automatic_replay',
                    'external_sdks_required': False, 'parallel_writers_supported': False,
                    'later_optional_modules': ['multi_agent_review_orchestration', 'automatic_tdd_orchestration', 'ai_planner', 'parallel_execution', 'host_tool_profile_loading']}

    return GovernedHarness
