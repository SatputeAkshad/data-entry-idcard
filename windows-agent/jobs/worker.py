import hashlib, json, os, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coreldraw.adapter import CorelAdapter

def atomic_json(path,value):
    temporary=path.with_suffix('.tmp'); temporary.write_text(json.dumps(value,indent=2),encoding='utf-8'); temporary.replace(path)

def run(job,root,result_path):
    root=Path(root); result_path=Path(result_path)
    result=job.get('result') or {}; result.setdefault('items',{})
    result.pop('error',None)
    try:
        with CorelAdapter() as corel:
            if job['kind']=='inspect':
                # Inspect a separate copy so accidental changes cannot touch a template.
                import shutil
                working=root/'tmp'/f"inspect-{job['id']}.cdr"
                shutil.copy2(root/job['payload']['template']['path'],working)
                try: result['inspection']=corel.inspect(working)
                finally: working.unlink(missing_ok=True)
            else:
                for student in job['payload']['students']:
                    previous=result['items'].get(student['id'],{})
                    if previous.get('state')=='completed' and all((root/previous[k]).is_file() for k in ('cdr','pdf')): continue
                    try:
                        if hashlib.sha256((root/student['photo']).read_bytes()).hexdigest()!=student['photo_sha256']: raise ValueError('Approved photograph checksum changed')
                        item=corel.generate(job['payload']['template'],student,root,root/'generated'/job['id'])
                        result['items'][student['id']]=item
                    except Exception as e:
                        result['items'][student['id']]={'state':'failed','error':str(e)}
                    atomic_json(result_path,{'state':'running','result':result})
        failures=sum(v['state']=='failed' for v in result['items'].values())
        state='completed' if not failures else ('failed' if failures==len(result['items']) else 'partial')
    except Exception as e: result['error']=str(e); state='failed'
    atomic_json(result_path,{'state':state,'result':result})

if __name__=='__main__':
    run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')),sys.argv[2],sys.argv[3])
