import unittest
from engine.adaptive_identity import identify_adaptive

class FastIdentityTests(unittest.TestCase):
    def test_unique_and_fallback(self):
        lines=[{'text':x,'score':.99} for x in ('QV','Gentle Cleanser','250 g')]
        item={'source':'catalog','fields':{'brand':'QV','name':'Gentle Cleanser','size':'250g'}}
        result=identify_adaptive(lines,lambda:self.fail('unexpected visual'),structured_evidence=[item])
        self.assertFalse(result['adaptive']['visual_executed'])
        self.assertFalse(result['identity_verified'])
        for evidence in ([],[dict(item,fields=dict(item['fields'],size='500g'))],[item,dict(item,fields=dict(item['fields'],gtin='12345678'))]):
            result=identify_adaptive(lines,lambda:{'fields':{'brand':'QV'}},structured_evidence=evidence)
            self.assertTrue(result['adaptive']['visual_executed'])
