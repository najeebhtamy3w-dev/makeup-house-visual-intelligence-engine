import copy
import hashlib
import unittest

from engine.calibration import evaluate, create_split, evaluate_split, dataset_sha256


def row(name, label='packshot', a=.8, b=.2, group=None, **extra):
    result={'sha256':hashlib.sha256(name.encode()).hexdigest(),'label':label,
            'scores':{'packshot':a,'advertising':b},'margin':abs(a-b),**extra}
    if group is not None:
        result['group_id']=group
    return result


class CalibrationTests(unittest.TestCase):
    def test_counts_include_abstention_in_recall(self):
        rows=[row('correct'),row('incorrect',label='advertising'),
              row('uncertain',label='advertising',a=.51,b=.49)]
        result=evaluate(rows,.1)
        self.assertEqual(result['accepted'],2)
        self.assertEqual(result['false_accepts'],1)
        self.assertEqual(result['abstained'],1)
        self.assertEqual(result['selective_accuracy'],.5)
        self.assertEqual(result['coverage'],2/3)
        self.assertEqual(result['per_class']['packshot']['precision'],.5)
        self.assertEqual(result['per_class']['advertising']['recall'],0)
        self.assertEqual(result['confusion_matrix']['advertising']['__ABSTAIN__'],1)

    def test_no_accepted_is_not_zero_accuracy(self):
        result=evaluate([row('a')],1)
        self.assertIsNone(result['selective_accuracy'])
        self.assertIsNone(result['selective_error_rate'])
        self.assertEqual(result['coverage'],0)
        self.assertEqual(result['missing_classes'],['advertising'])

    def test_ties_abstain_even_at_zero(self):
        result=evaluate([row('tie',a=.5,b=.5)],0)
        self.assertEqual(result['ties'],1)
        self.assertEqual(result['accepted'],0)

    def test_forged_margin_nonfinite_and_bad_schema_rejected(self):
        cases=[row('a',margin=1),row('a',a=float('nan')),row('a',label='unknown'),
               row('a',sha256='not-a-sha')]
        for sample in cases:
            with self.subTest(sample=sample),self.assertRaises(ValueError):
                evaluate([sample],.01)
        for threshold in (float('inf'),float('nan'),-1,True):
            with self.subTest(threshold=threshold),self.assertRaises(ValueError):
                evaluate([row('a')],threshold)

    def test_duplicates_and_inconsistent_classes_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_IMAGE'):
            evaluate([row('same'),row('same')],0)
        sample=row('different')
        sample['scores']['newclass']=.1
        with self.assertRaisesRegex(ValueError,'INCONSISTENT_CLASS_SCHEMA'):
            evaluate([row('first'),sample],0)

    def test_split_does_not_invent_independent_groups(self):
        with self.assertRaisesRegex(ValueError,'GROUP_METADATA_REQUIRED'):
            create_split([row('one'),row('two')])
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_INDEPENDENT_GROUPS'):
            create_split([row('one',group='product'),row('two',group='product')])

    def test_split_is_order_independent_and_grouped(self):
        rows=[row('one',group='a'),row('two',group='a'),row('three',group='b'),row('four',group='c')]
        manifest=create_split(rows)
        self.assertEqual(manifest,create_split(list(reversed(rows))))
        self.assertEqual(manifest['assignments'][rows[0]['sha256']],manifest['assignments'][rows[1]['sha256']])
        self.assertEqual(dataset_sha256(rows),dataset_sha256(list(reversed(rows))))
        self.assertFalse(manifest['independent_acceptance_eligible'])

    def test_shared_source_pages_merge_product_groups(self):
        rows=[row('one',group='a',source_url='https://brand.example/p?utm_source=ig'),
              row('two',group='b',source_url='https://brand.example/p#photo2'),row('three',group='c')]
        manifest=create_split(rows)
        self.assertEqual(manifest['independent_groups'],2)
        self.assertEqual(manifest['assignments'][rows[0]['sha256']],manifest['assignments'][rows[1]['sha256']])
        manifest['assignments'][rows[0]['sha256']]='calibration'
        manifest['assignments'][rows[1]['sha256']]='acceptance'
        with self.assertRaisesRegex(ValueError,'GROUP_OR_SOURCE_LEAKAGE'):
            evaluate_split(rows,manifest)

    def test_inspected_data_cannot_be_rebranded_acceptance(self):
        rows=[row('one',group='a'),row('two',group='b')]
        manifest=create_split(rows,frozen_threshold=.015)
        with self.assertRaisesRegex(ValueError,'PREVIOUSLY_INSPECTED'):
            evaluate_split(rows,manifest,'acceptance')

    def test_acceptance_uses_only_frozen_threshold_and_fingerprint(self):
        rows=[row('one',group='a'),row('two',group='b')]
        manifest=create_split(rows,frozen_threshold=.015,previously_inspected=False)
        result=evaluate_split(rows,manifest,'acceptance',thresholds=[0,1])
        self.assertEqual(len(result['results']),1)
        self.assertEqual(result['results'][0]['threshold'],.015)
        changed=copy.deepcopy(rows)
        changed[0]['label']='advertising'
        with self.assertRaisesRegex(ValueError,'DATASET_CHANGED'):
            evaluate_split(changed,manifest,'acceptance')

    def test_acceptance_requires_frozen_threshold(self):
        rows=[row('one',group='a'),row('two',group='b')]
        manifest=create_split(rows,previously_inspected=False)
        with self.assertRaisesRegex(ValueError,'FROZEN_THRESHOLD_REQUIRED'):
            evaluate_split(rows,manifest,'acceptance')

    def test_f1_and_balanced_coverage_from_independent_counts(self):
        # Actual A=3 B=1. At threshold.1: A->A1,A->B1,A->abstain1,B->A1.
        rows=[row('aa'),row('ab',a=.2,b=.8),row('ax',a=.51,b=.49),row('ba',label='advertising')]
        result=evaluate(rows,.1)
        a,b=result['per_class']['packshot'],result['per_class']['advertising']
        self.assertEqual((a['true_positive'],a['false_positive'],a['false_negative']),(1,1,2))
        self.assertEqual(a['precision'],1/2)
        self.assertEqual(a['recall'],1/3)
        self.assertEqual(a['f1'],2/5)
        self.assertEqual(b['f1'],0)
        self.assertEqual(result['macro_f1'],1/5)
        self.assertAlmostEqual(result['balanced_coverage'],(2/3+1)/2)
        self.assertEqual(result['human_review_status'],'UNVERIFIED')
        self.assertFalse(result['acceptance_qualified'])

    def test_f1_missing_class_undefined_seen_abstained_class_zero(self):
        result=evaluate([row('abstained')],1)
        self.assertIsNone(result['per_class']['advertising']['f1'])
        self.assertEqual(result['per_class']['packshot']['f1'],0)
        self.assertEqual(result['macro_f1'],0)
        self.assertEqual(result['macro_f1_classes'],['packshot'])
        self.assertEqual(result['balanced_coverage'],0)

    def test_cli_creating_protocol_only_reports_calibration_partition(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from engine.calibration import main
        rows=[row(str(i),group='product'+str(i)) for i in range(4)]
        with tempfile.TemporaryDirectory() as directory:
            labels=Path(directory)/'labels.json'
            protocol=Path(directory)/'protocol.json'
            labels.write_text(json.dumps(rows))
            output=io.StringIO()
            with patch('sys.argv',['calibration',str(labels),'--create-split',str(protocol),'--threshold','.015','--new-unseen-dataset']),contextlib.redirect_stdout(output):
                main()
            report=json.loads(output.getvalue())
            self.assertEqual(report['split'],'calibration')
            self.assertEqual(report['results'][0]['total'],3)
            self.assertFalse(report['independent_acceptance'])
            self.assertFalse(report['acceptance_qualified'])
            self.assertEqual(report['human_review_status'],'UNVERIFIED')
            self.assertEqual(len(json.loads(protocol.read_text())['assignments']),4)
