"""CI must retain actual results, refuse unknown replays and reject empty test output."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

spec=importlib.util.spec_from_file_location('ci_runner_under_test',Path(__file__).resolve().parents[1]/'ci_v83.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CIRunnerTests(unittest.TestCase):
    def test_generation_84_routes_only_to_84_and_retains_legacy_default(self):
        old=(m.H,m.S,m.GENERATION)
        try:
            def inspect_generation():
                self.assertEqual(m.GENERATION,'8.4')
                self.assertEqual(m.H,m.ROOT/'harnesses/v8.4')
                self.assertEqual(m.S,m.ROOT/'skills/skill-harness-v8-4')
                raise ValueError('Stop before any execution')
            with tempfile.TemporaryDirectory() as temporary,patch.object(m,'resources',side_effect=inspect_generation):
                self.assertEqual(m.main(['--generation','8.4','--output',temporary]),2)
        finally:m.H,m.S,m.GENERATION=old
        self.assertEqual(m.GENERATION,'8.3')
    def test_packager_uses_explicit_portable_path_order(self):
        spec=importlib.util.spec_from_file_location('ci_packager',m.ROOT/'tasks/package_v83.py')
        packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets').mkdir()
            for name in ('SKILL.md','README.md','assets/data.txt'):(root/name).write_text('fixture')
            actual=[p.relative_to(root).as_posix() for p in packager.files(root)]
            self.assertEqual(actual,['README.md','SKILL.md','assets/data.txt'])

    def test_workflow_matrix_and_evidence_policy_are_explicit(self):
        # BaseLoader preserves the YAML key "on" instead of YAML 1.1 boolean coercion.
        doc=yaml.load((m.ROOT/'.github/workflows/ci.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(doc['on']),{'pull_request','push','workflow_dispatch'})
        self.assertEqual(doc['permissions'],{'contents':'read'})
        job=doc['jobs']['qualification'];matrix=job['strategy']['matrix']
        self.assertEqual(set(matrix['os']),{'ubuntu-24.04','windows-2025','macos-15'})
        self.assertEqual(matrix['python'],['3.11','3.14'])
        self.assertEqual(job['strategy']['fail-fast'],'false')
        for step in job['steps']:
            if 'uses' in step:self.assertRegex(step['uses'],r'^actions/[a-z-]+@[0-9a-f]{40}$')
        upload=job['steps'][-1]
        self.assertEqual(upload['if'],'always()')
        self.assertEqual(upload['with']['if-no-files-found'],'error')
        self.assertEqual(doc['jobs']['required']['if'],'always()')
        self.assertIn('= success',doc['jobs']['required']['steps'][0]['run'])

    def test_pipeline_source_identity_covers_packager_and_ci_tests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);h=root/'h';s=root/'s'
            core='test core'
            for folder in (h,s):
                folder.mkdir()
                for name in ('scripts','tests','references','examples','templates'): (folder/name).mkdir()
            (h/'CORE.md').write_text(core)
            (s/'SKILL.md').write_text('---\nname: skill-harness-v8-3\ndescription: test\n---\n'+core)
            for folder in (h,s):
                rows=[{'path':p.name,'bytes':p.stat().st_size,'sha256':m.sha(p)} for p in folder.iterdir() if p.is_file()]
                (folder/'MANIFEST.json').write_text(json.dumps({'files':rows}))
            paths=['tasks/ci_v83.py','tasks/package_v83.py','tasks/tests/test_ci_v83.py',
                   'requirements-ci.txt','.github/workflows/ci.yml']
            for name in paths:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('before')
            with patch.object(m,'ROOT',root),patch.object(m,'H',h),patch.object(m,'S',s):
                before=m.resources()
                for name in paths:
                    p=root/name;p.write_text('after')
                    self.assertNotEqual(before,m.resources(),name)
                    p.write_text('before')

    def test_required_outputs_are_bound_and_cannot_disappear_or_change(self):
        for directory in (False,True):
            for mutation in ('delete','alter','add'):
                with self.subTest(directory=directory,mutation=mutation),tempfile.TemporaryDirectory() as temp:
                    root=Path(temp);out=root/'receipts';out.mkdir()
                    artifact=root/'product';artifact.mkdir() if directory else None
                    file=artifact/'data.zip' if directory else artifact
                    argv=[sys.executable,'-c',f'from pathlib import Path;Path({str(file)!r}).write_text("original")']
                    outputs=[str(artifact)]
                    row=m.execute('output',argv,root,out,'source',30,outputs=outputs)
                    self.assertTrue(row['passed'])
                    if mutation=='delete':file.unlink()
                    elif mutation=='alter':file.write_text('changed')
                    elif directory:(artifact/'unexpected').write_text('extra')
                    else:file.write_text('extra')
                    with self.assertRaises(ValueError):
                        m.execute('output',argv,root,out,'source',30,resume=True,outputs=outputs)

    def test_success_exit_without_required_output_is_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            row=m.execute('missing',[sys.executable,'-c','pass'],root,out,'source',30,outputs=[str(root/'missing')])
            self.assertFalse(row['passed'])
            self.assertIn('output_error',row)

    def test_successful_result_is_reused_without_reexecuting_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            argv=[sys.executable,'-c',"from pathlib import Path; p=Path('counter');p.write_text(str(int(p.read_text())+1) if p.exists() else '1')"]
            first=m.execute('counter',argv,root,out,'source',30)
            second=m.execute('counter',argv,root,out,'source',30,resume=True)
            self.assertTrue(first['passed']);self.assertTrue(second['passed'])
            self.assertEqual((root/'counter').read_text(),'1')

    def test_changed_context_cannot_reuse_prior_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            argv=[sys.executable,'-c','pass']
            m.execute('test',argv,root,out,'before',30)
            with self.assertRaises(ValueError):m.execute('test',argv,root,out,'after',30,resume=True)

    def test_failed_process_is_durable_and_not_retried_implicitly(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            argv=[sys.executable,'-c','raise SystemExit(7)']
            row=m.execute('bad',argv,root,out,'source',30)
            self.assertFalse(row['passed']);self.assertEqual(row['exit_code'],7)
            self.assertEqual(m.execute('bad',argv,root,out,'source',30,resume=True)['exit_code'],7)
            self.assertTrue((out/'bad.result.json').is_file())

    def test_admitted_unknown_process_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            (out/'pending.admitted.json').write_text('{}')
            with self.assertRaises(ValueError):m.execute('pending',[sys.executable,'-c','pass'],root,out,'source',30,resume=True)

    def test_zero_case_success_envelope_is_not_credited(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'receipts';out.mkdir()
            report=out/'cases.json'
            report.write_text(json.dumps({'format':'verimission-results-v1','run_id':'r','context_sha256':'c','complete':True,'cases':[]}))
            row=m.execute('empty',[sys.executable,'-c','pass'],root,out,'source',30,
                cases={'path':str(report),'run_id':'r','context_sha256':'c'})
            self.assertFalse(row['passed'])


if __name__=='__main__':unittest.main()
