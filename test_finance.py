import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import amount,extract,calculate,MAP
class FinanceTests(unittest.TestCase):
 def test_amount(self):
  self.assertEqual(amount('(1,200)'),-1200); self.assertIsNone(amount('-'))
 def test_calculations(self):
  v={k:None for k in MAP}; b=v.copy()
  v.update(revenue=200,operating_profit=20,net_income=10,owners_income=8,assets=120,owners_equity=50,liabilities=60,equity=60,current_assets=40,current_liabilities=20,cfo=30,capex_ppe=5,capex_intangible=2)
  b.update(revenue=100,assets=80,owners_equity=30)
  r=calculate(v,b)
  self.assertEqual(r['revenue_growth'],100);self.assertEqual(r['roa'],10);self.assertEqual(r['roe'],20);self.assertEqual(r['fcf'],23)
  v['net_income']=-10;self.assertIsNone(calculate(v,b)['cash_conversion'])
  v['capex_intangible']=None;self.assertIsNone(calculate(v,b)['fcf'])
 def test_conflicts_and_currency(self):
  row={'sj_div':'BS','account_id':'ifrs-full_Assets','thstrm_amount':'100','frmtrm_amount':'80','currency':'KRW'}
  self.assertEqual(extract([row])[0]['assets'],100)
  self.assertIsNone(extract([row,{**row,'thstrm_amount':'200'}])[0]['assets'])
  self.assertIsNone(extract([{**row,'currency':'USD'}])[0]['assets'])
if __name__=='__main__':unittest.main()
