#!/usr/bin/env python3
"""Read-only final manuscript gate. Cannot turn a synthetic rehearsal into independent evidence."""
import argparse,json,csv,hashlib
from pathlib import Path
from reference_model import digest,jwrite,cwrite

def verify_sha(root,name):
    path=root/name
    if not path.exists():raise FileNotFoundError(path)
    with path.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    for r in rows:
        p=root/r['file']
        if not p.exists() or digest(p)!=r['sha256']:raise RuntimeError(f'Hash failure: {p}')
    return len(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--deepmimo-dir',required=True);ap.add_argument('--threegpp-dir',required=True)
    ap.add_argument('--boundary-dir',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    d=Path(a.deepmimo_dir);g=Path(a.threegpp_dir);b=Path(a.boundary_dir)
    reasons=[];sources=[];hashes=[]
    for root,expect in ((d,'DeepMIMO'),(g,'Sionna_3GPP')):
        verify_sha(root,'CP07_SHA256.csv')
        p=json.loads((root/'CP01_dataset_audit.json').read_text(encoding='utf8'))
        x=json.loads((root/'CP06_decision.json').read_text(encoding='utf8'))
        source=p['provenance']['source'];scenario=p['provenance']['scenario']
        if source!=expect:reasons.append(f'{expect}: source mismatch')
        if p['smoke']:reasons.append(f'{expect}: smoke data')
        if x['false_prune']!=0:reasons.append(f'{expect}: false pruning')
        if x['status']!='GO_FAST_RUNTIME':reasons.append(f'{expect}: no verified FAST runtime advantage')
        if p['n_groups']<20:reasons.append(f'{expect}: fewer than 20 groups')
        if 'synthetic' in (scenario+' '+p['provenance']['generation_method']).lower():reasons.append(f'{expect}: synthetic source declared')
        hashes.append(p['dataset_sha256']);sources.append(dict(source=source,scenario=scenario,decision=x['status'],groups=p['n_groups']))
    verify_sha(b,'CP03_sha256.csv')
    bd=json.loads((b/'CP02_boundary_decision.json').read_text(encoding='utf8'))
    if bd.get('outcome')!='PASS' or bd.get('false_prunes')!=0:reasons.append('Boundary audit failed')
    with (b/'CP01_boundary_cases.csv').open(newline='',encoding='utf-8') as f:
        boundary_rows=list(csv.DictReader(f))
    if not any(r.get('source') not in ('algebraic','',None) for r in boundary_rows):
        reasons.append('Boundary audit lacks channel-derived cases')
    if hashes[0]==hashes[1]:reasons.append('Identical channel files for two claimed sources')
    # NOTE: metadata is not a mathematical proof of source independence.
    status='ELIGIBLE_FOR_MANUSCRIPT_REVIEW' if not reasons else 'STOP_MANUSCRIPT_NOT_LOCKED'
    result=dict(status=status,blocking_reasons=reasons,sources=sources,boundary=bd,
                caution='Passing technical gates does not verify 3GPP generator or publications, statistical independence, or full floating-point interval certification; scientific review required.')
    jwrite(a.out,result);print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
