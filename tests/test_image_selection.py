import unittest
from engine.image_selection import rank_candidates

def row(name,identity='INSUFFICIENT_EVIDENCE',category='unknown',aesthetic=None):
    return {'sha256':name,'width':1000,'height':1000,'visual_evidence':{'identity_status':identity,'category':category,'aesthetic_normalized':aesthetic}}

class SelectionTests(unittest.TestCase):
    def test_identity_gate(self):
        rows=rank_candidates([row('wrong','CONFLICT','packshot',1),row('right','CORROBORATED_REVIEW_REQUIRED','packshot',.1)])
        self.assertEqual(rows[0]['sha256'],'right')
        self.assertEqual(rows[1]['selection']['status'],'REJECTED')
        self.assertFalse(rows[0]['publication_allowed'])
    def test_purpose(self):
        rows=[row('pack',category='packshot'),row('ad',category='advertising')]
        self.assertEqual(rank_candidates(rows,'catalog')[0]['sha256'],'pack')
        self.assertEqual(rank_candidates(rows,'marketing')[0]['sha256'],'ad')
    def test_missing(self):
        result=rank_candidates([row('unknown')])[0]['selection']
        self.assertIsNone(result['components']['aesthetic'])
        self.assertEqual(result['evidence_coverage'],.25)
    def test_logo(self):
        self.assertEqual(rank_candidates([row('logo',category='logo')])[0]['selection']['status'],'REJECTED')
