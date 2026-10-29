#!/usr/bin/env python3
"""Auditable fixed-CSI-margin calibration with spatial-group metadata and resumable stages.
Statistics require independent, exchangeable calibration episodes; spatial distance is
only a diagnostic and cannot establish probabilistic independence.
"""
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from calibrate import test_one, upper, q_values
from engine_original import atomic_json, atomic_csv, sha

def read(path,M,K,strict=True):
    with np.load(path,allow_pickle=False) as d:
        mandatory=['H','groups','xyz','scenario']
        missing=[x for x in mandatory if x not in d]
        if missing:raise ValueError('Missing metadata: '+','.join(missing))
        H=d['H'];g=d['groups'].astype('U128');xyz=d['xyz'];scene=d['scenario'].astype('U128')
    n=len(H)
    if H.shape!=(n,M,K) or not np.iscomplexobj(H) or not np.isfinite(H).all():raise ValueError('H: expected finite complex (N,M,K)')
    if xyz.shape!=(n,3) or not np.isfinite(xyz).all():raise ValueError('xyz: expected finite (N,3) coordinates in METERS')
    if g.shape!=(n,) or scene.shape!=(n,):raise ValueError('groups/scenario must be length N')
    if np.any(np.char.str_len(g)==0) or np.any(np.char.str_len(scene)==0):raise ValueError('empty metadata')
    # All samples within one group must belong to the same scene.
    for name in np.unique(g):
        if len(np.unique(scene[g==name]))!=1:raise ValueError('group crosses multiple scenarios: '+name)
    if strict and len(np.unique(g))<118:raise ValueError('At least 118 groups for 50% calibration (>=59). Increase independent blocks.')
    return H,g,xyz,scene

def geometry_audit(g,xyz,scene,min_distance):
    uniq=np.unique(g);centers={k:xyz[g==k].mean(axis=0) for k in uniq}
    rows=[]
    for k in uniq:
        a=xyz[g==k];dist=np.linalg.norm(a-centers[k],axis=1).max()
        peers=[(v,np.linalg.norm(centers[v]-centers[k])) for v in uniq if v!=k and scene[np.where(g==v)[0][0]]==scene[np.where(g==k)[0][0]]]
        nearest=min((d for _,d in peers),default=float('inf'))
        rows.append({'group':k,'scenario':scene[np.where(g==k)[0][0]],'size':len(a),'radius_m':float(dist),'nearest_group_center_m':nearest,'spatial_distance_pass':int(nearest>=min_distance),'cx_m':float(centers[k][0]),'cy_m':float(centers[k][1]),'cz_m':float(centers[k][2])})
    # Spatial distances only reject suspicious groups. Never claim independence certified.
    return rows

def partitions(g,seed):
    u=np.random.default_rng(seed).permutation(np.unique(g));n=len(u)
    ndev=int(.25*n);ncal=int(.50*n);ncal=min(ncal,n-ndev-1)
    sets={'dev':set(u[:ndev]),'cal':set(u[ndev:ndev+ncal]),'test':set(u[ndev+ncal:])}
    assert all(sets[k] and sets[k].isdisjoint(sets[v]) for k in sets for v in sets if k!=v)
    return {k:np.flatnonzero(np.isin(g,list(s))).tolist() for k,s in sets.items()}, {k:sorted(s) for k,s in sets.items()}

def stable_signature(a,allfiles):
    relevant={k:v for k,v in vars(a).items() if k not in ('stage','external_dataset')}
    return {'arguments':relevant,'source_hashes':{str(p):sha(p) for p in allfiles},'dataset_sha':sha(a.dataset)}

def execute(H,ids,qs,mc,a,root,stage,source_tag,groups,one_per_group=False):
    if one_per_group:
        ids=[min([i for i in ids if groups[i]==k]) for k in np.unique(groups[ids])]
    folder=root/'tasks'/stage;folder.mkdir(parents=True,exist_ok=True)
    cfg={'sigma_rel':a.sigma_rel,'sinr':10**(a.sinr_db/10),'noise':a.noise,'pmax':a.pmax}
    rows=[]
    for idx in ids:
        p=folder/f'{source_tag}_{idx:08d}.json'
        if p.exists():
            obj=json.loads(p.read_text());expected={'index':idx,'qs':qs,'mc':mc,'source':source_tag,'group':str(groups[idx])}
            if any(obj.get(k)!=v for k,v in expected.items()):raise RuntimeError('task checkpoint mismatch '+str(p))
        else:
            results=[dict(index=int(idx),group=str(groups[idx]),q=float(q),**test_one(H,idx,q,mc,a.seed,cfg)) for q in qs]
            obj={'index':idx,'qs':qs,'mc':mc,'source':source_tag,'group':str(groups[idx]),'rows':results}
            atomic_json(p,obj)
        rows.extend(obj['rows'])
    return rows

def summarize(rows,alpha):
    result=[]
    for q in sorted(set(r['q'] for r in rows)):
        r=[t for t in rows if t['q']==q];n=len(r)
        failures=sum((not t['feasible']) or t['errors']>0 for t in r)
        powers=[t['power_w'] for t in r if t['feasible']]
        trials=sum(t['trials'] for t in r if t['feasible'])
        errs=sum(t['errors'] for t in r if t['feasible'])
        result.append({'q':q,'n_episodes':n,'n_feasible':len(powers),'failures':failures,'failure_rate':failures/n,'upper_95_one_sided':upper(failures,n,alpha),'conditional_mc_outage':errs/trials if trials else 1.,'mean_power_w':float(np.mean(powers)) if powers else ''})
    return result

def dumpcsv(path,rows):
    if not rows:raise RuntimeError('No rows for '+str(path))
    atomic_csv(path,rows,list(rows[0]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=['preflight','develop','calibrate','freeze','test','transfer','report','all'],required=True)
    p.add_argument('--dataset',required=True);p.add_argument('--external-dataset',default='');p.add_argument('--run-id',required=True);p.add_argument('--output-root',default='outputs')
    p.add_argument('--M',type=int,default=16);p.add_argument('--K',type=int,default=4);p.add_argument('--seed',type=int,default=20261028)
    p.add_argument('--sigma-rel',type=float,default=.04);p.add_argument('--sinr-db',type=float,default=6.);p.add_argument('--noise',type=float,default=1e-9);p.add_argument('--pmax',type=float,default=1.)
    p.add_argument('--epsilon',type=float,default=.05);p.add_argument('--alpha',type=float,default=.05);p.add_argument('--mc',type=int,default=100);p.add_argument('--min-center-distance-m',type=float,default=10.)
    a=p.parse_args()
    if not (0<a.epsilon<1 and 0<a.alpha<1 and a.mc>=1 and a.noise>0 and a.pmax>0 and a.sigma_rel>0):p.error('invalid parameters')
    H,g,xyz,scenario=read(a.dataset,a.M,a.K)
    audit=geometry_audit(g,xyz,scenario,a.min_center_distance_m)
    if not all(r['spatial_distance_pass'] for r in audit):raise RuntimeError('Group-center separation below threshold; rebuild group IDs or redefine blocks')
    splits,labels=partitions(g,a.seed)
    if len(labels['cal'])<59:raise RuntimeError('Calibration has fewer than 59 groups: '+str(len(labels['cal'])))
    qs=q_values(np.sqrt(-2*np.log(a.epsilon/a.K)))
    root=Path(a.output_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    signature_data=stable_signature(a,[Path(__file__),Path(__file__).parent/'calibrate.py',Path(__file__).parent/'engine_original.py'])
    signature=hashlib.sha256(json.dumps(signature_data,sort_keys=True).encode()).hexdigest()
    manifest=root/'CP00_manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['signature']!=signature:raise RuntimeError('Fingerprint mismatch: new run-id required')
    else:atomic_json(manifest,{'signature':signature,**signature_data,'splits':labels,'note':'Distance check is NOT proof of statistical independence'})
    dumpcsv(root/'CP00_spatial_group_audit.csv',audit)
    atomic_json(root/'CP00_split_groups.json',labels)
    if a.stage=='preflight':print('PREFLIGHT PASS', {k:len(v) for k,v in labels.items()});return
    if a.stage in ('develop','all'):
        rows=execute(H,splits['dev'],qs,a.mc,a,root,'dev','deepmimo',g)
        dumpcsv(root/'CP01_development.csv',rows)
        summ=summarize(rows,a.alpha);dumpcsv(root/'CP02_development_summary.csv',summ)
        candidates=[x for x in summ if x['failure_rate']<=a.epsilon and x['mean_power_w']!='']
        selection=min(candidates,key=lambda x:x['mean_power_w'])['q'] if candidates else max(qs)
        atomic_json(root/'CP03_locked_candidate.json',{'q':selection,'source':'development','selected_without_calibration':True,'selected_without_test':True,'note':'development selection not a statistical certificate'})
    if a.stage in ('calibrate','all'):
        if not (root/'CP03_locked_candidate.json').exists():raise RuntimeError('development candidate missing')
        q=json.loads((root/'CP03_locked_candidate.json').read_text())['q']
        rows=execute(H,splits['cal'],[q],1,a,root,'cal','deepmimo',g,one_per_group=True)
        dumpcsv(root/'CP04_calibration.csv',rows);v=summarize(rows,a.alpha)[0]
        v.update({'eligible':v['upper_95_one_sided']<=a.epsilon,'calibration_status':'PASS' if v['upper_95_one_sided']<=a.epsilon else 'FAIL','independence_assumption':'independent exchangeable group episodes; group metadata alone cannot prove this'})
        atomic_json(root/'CP05_calibration_decision.json',v)
    if a.stage in ('freeze','all'):
        v=json.loads((root/'CP05_calibration_decision.json').read_text())
        atomic_json(root/'CP06_frozen.json',{'q':v['q'],'eligible':v['eligible'],'epsilon':a.epsilon,'alpha':a.alpha,'state':'CALIBRATION_PASS' if v['eligible'] else 'STOP_NO_CERTIFICATE','calibration_checkpoint_sha':sha(root/'CP05_calibration_decision.json')})
    if a.stage in ('test','all'):
        fr=json.loads((root/'CP06_frozen.json').read_text())
        rows=execute(H,splits['test'],sorted(set([fr['q'],max(qs)])),a.mc,a,root,'test','deepmimo',g)
        dumpcsv(root/'CP07_independent_test.csv',rows);dumpcsv(root/'CP08_test_summary.csv',summarize(rows,a.alpha))
    if a.stage in ('transfer','all') and a.external_dataset:
        extH,extg,extxyz,extscene=read(a.external_dataset,a.M,a.K,strict=False)
        ext_audit=geometry_audit(extg,extxyz,extscene,a.min_center_distance_m)
        if not all(x['spatial_distance_pass'] for x in ext_audit):raise RuntimeError('External source group separation insufficient')
        fr=json.loads((root/'CP06_frozen.json').read_text())
        external_sha=sha(a.external_dataset);tag=external_sha[:12]
        rows=execute(extH,list(range(len(extH))),sorted(set([fr['q'],max(qs)])),a.mc,a,root,'external',tag,extg)
        dumpcsv(root/'CP09_external_test.csv',rows);dumpcsv(root/'CP10_external_summary.csv',summarize(rows,a.alpha))
        atomic_json(root/'CP10_external_provenance.json',{'sha256':external_sha,'scenario_values':sorted(set(extscene.tolist())),'n_groups':len(np.unique(extg)),'note':'Sionna/3GPP conformity and independence must be documented by simulator provenance. DeepMIMO guarantee does NOT transfer.'})
    if a.stage in ('report','all'):
        fr=json.loads((root/'CP06_frozen.json').read_text())
        if not (root/'CP08_test_summary.csv').exists():raise RuntimeError('Run test before report')
        atomic_json(root/'CP11_decision.json',{'decision':'GO_CANDIDATE_ONLY' if fr['eligible'] else 'STOP_NO_CERTIFICATE','external_run':(root/'CP10_external_summary.csv').exists(),'calibration_eligible':fr['eligible'],'caution':'No claim of improvement over baseline without paired statistical comparison; no cross-distribution guarantee'})
        records=[{'file':f.name,'sha256':sha(f)} for f in sorted(root.glob('CP*')) if f.is_file() and f.name!='CP12_sha256.csv']
        dumpcsv(root/'CP12_sha256.csv',records)
        print(json.loads((root/'CP11_decision.json').read_text())['decision'])
if __name__=='__main__':main()
