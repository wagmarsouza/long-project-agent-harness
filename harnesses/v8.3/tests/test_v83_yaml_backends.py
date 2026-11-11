"""Safe acceleration must preserve old documents, integrity and constructor refusal."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from test_v83_assurance import load


class SafeBackendTests(unittest.TestCase):
    def pairs(self):
        pairs=[(yaml.SafeLoader,yaml.SafeDumper)]
        if hasattr(yaml,'CSafeLoader'):pairs.append((yaml.CSafeLoader,yaml.CSafeDumper))
        return pairs

    def test_backend_report_identifies_only_safe_classes(self):
        m=load('yaml_store');info=m.yaml_backend()
        self.assertIn(info['loader'],('SafeLoader','CSafeLoader'))
        self.assertIn(info['dumper'],('SafeDumper','CSafeDumper'))

    def test_safe_backends_read_legacy_text_and_keep_integrity_checks(self):
        m=load('yaml_store')
        state={'schema':1,'revision':0,'unicode':'ação — 日本語','number':42,'empty':[],
               'null':None,'boolean':False,'date_string':'2026-11-10'}
        for loader,dumper in self.pairs():
            with self.subTest(loader=loader.__name__), tempfile.TemporaryDirectory() as temp, \
                    patch.object(m,'_SAFE_LOADER',loader),patch.object(m,'_SAFE_DUMPER',dumper):
                store=m.YAMLStore(Path(temp)/'state.yaml',lambda:'synthetic-time')
                doc=store._document(state,[])
                store.path.write_text(yaml.safe_dump(doc,allow_unicode=True),encoding='utf-8')
                with store.state() as value:self.assertEqual(value,state)
                with store.state(write=True) as value:value['number']=43
                self.assertTrue(store.validate())
                altered=store._load_unlocked();altered['state']['number']=99
                store.path.write_text(yaml.safe_dump(altered),encoding='utf-8')
                with self.assertRaises(m.StoreError) as caught:store.validate()
                self.assertEqual(caught.exception.code,'STORE_INTEGRITY')

    def test_python_object_tags_are_refused_before_document_validation(self):
        m=load('yaml_store')
        for loader,_ in self.pairs():
            with self.subTest(loader=loader.__name__),tempfile.TemporaryDirectory() as temp,patch.object(m,'_SAFE_LOADER',loader):
                store=m.YAMLStore(Path(temp)/'state.yaml',lambda:'synthetic-time')
                store.path.write_text("!!python/object/apply:builtins.dict []\n",encoding='utf-8')
                with self.assertRaises(m.StoreError) as caught:store.validate()
                self.assertEqual(caught.exception.code,'STORE')
                self.assertIsInstance(caught.exception.__cause__,yaml.constructor.ConstructorError)


if __name__=='__main__':unittest.main()
