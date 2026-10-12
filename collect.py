"""Annual CFS only; no credentials in output or exception URLs."""
import os, json, io, zipfile, re, csv
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
ROOT=Path(__file__).resolve().parents[1]
def norm(s): return re.sub(r'\s+','',s or '')
def amount(s):
    s=(s or '').replace(',','').strip()
    if s in ('','-'): return None
    if s.startswith('(') and s.endswith(')'): s='-'+s[1:-1]
    try: return int(s)
    except ValueError: return None
# Exact matching only. Unmatched or conflicting rows stay null; no fuzzy guessing.
MAP={
'revenue':(['IS','CIS'],['ifrs-full_Revenue'],['매출액','영업수익','수익(매출액)']),
'operating_profit':(['IS','CIS'],['dart_OperatingIncomeLoss'],['영업이익','영업이익(손실)']),
'net_income':(['IS','CIS'],['ifrs-full_ProfitLoss'],['당기순이익','당기순이익(손실)']),
'owners_income':(['IS','CIS'],['ifrs-full_ProfitLossAttributableToOwnersOfParent'],['지배기업소유주지분','지배기업의소유주에게귀속되는당기순이익(손실)']),
'assets':(['BS'],['ifrs-full_Assets'],['자산총계']),
'liabilities':(['BS'],['ifrs-full_Liabilities'],['부채총계']),
'equity':(['BS'],['ifrs-full_Equity'],['자본총계']),
'owners_equity':(['BS'],['ifrs-full_EquityAttributableToOwnersOfParent'],['지배기업소유주지분','지배기업의소유주에게귀속되는자본']),
'current_assets':(['BS'],['ifrs-full_CurrentAssets'],['유동자산']),
'current_liabilities':(['BS'],['ifrs-full_CurrentLiabilities'],['유동부채']),
'cash':(['BS'],['ifrs-full_CashAndCashEquivalents'],['현금및현금성자산']),
'cfo':(['CF'],['ifrs-full_CashFlowsFromUsedInOperatingActivities'],['영업활동현금흐름','영업활동으로인한현금흐름']),
'capex_ppe':(['CF'],['ifrs-full_PurchaseOfPropertyPlantAndEquipment'],['유형자산의취득']),
'capex_intangible':(['CF'],['ifrs-full_PurchaseOfIntangibleAssets'],['무형자산의취득'])}
def extract(rows):
    vals={}; prior={}; audit={}
    for k,(sj,ids,names) in MAP.items():
        candidates=[r for r in rows if r.get('sj_div') in sj and r.get('account_id') in ids]
        if not candidates: candidates=[r for r in rows if r.get('sj_div') in sj and norm(r.get('account_nm')) in names]
        usable=[r for r in candidates if r.get('currency')=='KRW']
        pairs={(amount(r.get('thstrm_amount')),amount(r.get('frmtrm_amount'))) for r in usable}
        if len(pairs)==1:
            vals[k],prior[k]=next(iter(pairs))
        else: vals[k]=prior[k]=None
        audit[k]={'status':'matched' if len(pairs)==1 and vals[k] is not None else 'review_required',
                  'rows':[{x:r.get(x) for x in ('sj_div','account_id','account_nm','currency','thstrm_amount','frmtrm_amount')} for r in candidates]}
    return vals,prior,audit

def ratio(n,d,scale=100):
    return n/d*scale if n is not None and d is not None and d>0 else None

def average(a,b): return (a+b)/2 if a is not None and b is not None else None

def calculate(v,b):
    out={'revenue_growth':ratio(v['revenue'],b['revenue'])}
    if out['revenue_growth'] is not None: out['revenue_growth']-=100
    out.update(operating_margin=ratio(v['operating_profit'],v['revenue']),
      net_margin=ratio(v['net_income'],v['revenue']),
      roa=ratio(v['net_income'],average(v['assets'],b['assets'])),
      roe=ratio(v['owners_income'],average(v['owners_equity'],b['owners_equity'])),
      current_ratio=ratio(v['current_assets'],v['current_liabilities']),
      debt_ratio=ratio(v['liabilities'],v['equity']),
      equity_ratio=ratio(v['equity'],v['assets']),
      asset_turnover=ratio(v['revenue'],average(v['assets'],b['assets']),1),
      cash_conversion=ratio(v['cfo'],v['net_income'],1))
    capex=None if any(v[k] is None for k in ('capex_ppe','capex_intangible')) else abs(v['capex_ppe'])+abs(v['capex_intangible'])
    out['capex']=capex
    out['fcf']=v['cfo']-capex if capex is not None and v['cfo'] is not None else None
    return out

def api(endpoint,key,**params):
    try:
        r=requests.get('https://opendart.fss.or.kr/api/'+endpoint,params={'crtfc_key':key,**params},timeout=90)
        r.raise_for_status()
        return r
    except requests.RequestException:
        raise RuntimeError('DART 통신 실패: 요청 주소와 인증키는 로그에 기록하지 않습니다.') from None

def getzip(endpoint,key,**params):
    r=api(endpoint,key,**params)
    if not zipfile.is_zipfile(io.BytesIO(r.content)):
        try: code=ET.fromstring(r.content).findtext('status')
        except ET.ParseError: code='unknown'
        raise RuntimeError('DART ZIP 수신 실패: '+str(code))
    return r.content

def main():
    key=os.environ.get('DART_API_KEY')
    if not key: raise RuntimeError('GitHub Secrets에 DART_API_KEY를 등록하세요.')
    end=int(os.environ.get('END_YEAR') or datetime.now(timezone.utc).year-1)
    start=int(os.environ.get('START_YEAR') or end-4)
    if start<2015 or start>end: raise RuntimeError('연도 범위를 확인하세요.')
    corpzip=getzip('corpCode.xml',key)
    with zipfile.ZipFile(io.BytesIO(corpzip)) as z:
        xml=ET.fromstring(z.read('CORPCODE.xml'))
    matches=[r for r in xml.findall('list') if r.findtext('stock_code')=='035720']
    if len(matches)!=1: raise RuntimeError('카카오 종목코드 035720 고유번호를 유일하게 확인하지 못했습니다.')
    corp=matches[0].findtext('corp_code'); company=matches[0].findtext('corp_name')
    records=[]; issues=[]; now=datetime.now(timezone.utc).isoformat()
    for year in range(start,end+1):
        data=api('fnlttSinglAcntAll.json',key,corp_code=corp,bsns_year=year,reprt_code='11011',fs_div='CFS').json()
        if data.get('status')=='013':
            issues.append({'year':year,'message':'연결 사업보고서 재무자료 없음'}); continue
        if data.get('status')!='000': raise RuntimeError('DART 오류 코드: '+str(data.get('status')))
        raw=ROOT/'data/raw'/str(year); raw.mkdir(parents=True,exist_ok=True)
        (raw/'financials.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        rows=data['list']; receipts=sorted({r['rcept_no'] for r in rows})
        for no in receipts:
            target=ROOT/'reports'/f'{year}_{no}.zip'; target.parent.mkdir(exist_ok=True)
            if not target.exists(): target.write_bytes(getzip('document.xml',key,rcept_no=no))
        v,b,audit=extract(rows); ratios=calculate(v,b)
        (raw/'mapping_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        rec={'year':year,'values':v,'prior_values':b,'ratios':ratios,'receipts':receipts,'collected_at':now,
             'warnings':[k+' 계정 확인 필요' for k,a in audit.items() if a['status']!='matched']}
        if v['net_income'] is not None and v['net_income']<=0: rec['warnings'].append('순손실 또는 순이익 0: CFO/순이익은 표시하지 않음')
        if all(v[k] is not None for k in ('assets','liabilities','equity')) and v['assets']!=v['liabilities']+v['equity']: rec['warnings'].append('자산 = 부채 + 자본 검증 실패')
        records.append(rec)
    if not records: raise RuntimeError('수집된 재무제표가 없어 배포하지 않습니다.')
    output={'company':company,'stock_code':'035720','corp_code':corp,'basis':'CFS / annual / KRW','updated_at':now,'records':records,'issues':issues}
    dst=ROOT/'data'; dst.mkdir(exist_ok=True)
    (dst/'financials.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    with (dst/'financials.csv').open('w',encoding='utf-8-sig',newline='') as f:
        flat=[{'year':r['year'],**r['values'],**r['ratios']} for r in records]
        w=csv.DictWriter(f,fieldnames=flat[0].keys()); w.writeheader(); w.writerows(flat)
    template=(ROOT/'web/template.html').read_text(encoding='utf-8')
    embedded=json.dumps(output,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    (ROOT/'index.html').write_text(template.replace('__PAYLOAD__',embedded),encoding='utf-8')
    print('수집 완료:',len(records),'개 연도; 누락 지표는 mapping_audit.json 확인')
if __name__=='__main__': main()
