import hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows-agent'))
spec=importlib.util.spec_from_file_location('test_worker',Path(__file__).resolve().parents[1]/'windows-agent/jobs/worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
class SimulatedCorel:
    """Test-only adapter. Outputs clearly marked simulation fixtures, never CDR/PDF."""
    calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def generate(self,template,student,root,output):
        self.calls.append(student['id']);output.mkdir(parents=True,exist_ok=True)
        if student['data'].get('fail'):raise RuntimeError('SIMULATED per-card error')
        path=output/(student['id']+'.simulation.json')
        path.write_text(json.dumps({'SIMULATION':True,'student':student['id'],'data':student['data'],'photo':(root/student['photo']).read_text()}))
        return {'state':'completed','cdr':path.relative_to(root).as_posix(),'pdf':path.relative_to(root).as_posix()}
class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'approved').mkdir();SimulatedCorel.calls=[]
        self.job={'id':'test-job','kind':'generate','payload':{'template':{},'students':[]},'result':{}}
        for i in range(2):
            path=f'approved/{i}.jpg';data=f'SIMULATED PHOTO {i}'.encode();(self.root/path).write_bytes(data)
            self.job['payload']['students'].append({'id':str(i),'data':{'full_name':f'Student {i}'},'photo':path,'photo_sha256':hashlib.sha256(data).hexdigest()})
        self.result=self.root/'result.json'
    def run_job(self):
        with patch.object(worker,'CorelAdapter',SimulatedCorel):worker.run(self.job,self.root,self.result)
        return json.loads(self.result.read_text())
    def test_batch_keeps_identity_and_photos_together(self):
        result=self.run_job();self.assertEqual(result['state'],'completed')
        for id,item in result['result']['items'].items():
            artifact=json.loads((self.root/item['cdr']).read_text());self.assertEqual(artifact['student'],id);self.assertEqual(artifact['photo'],f'SIMULATED PHOTO {id}')
    def test_failure_continues_and_retry_preserves_success(self):
        self.job['payload']['students'][0]['data']['fail']=True
        result=self.run_job();self.assertEqual(result['state'],'partial');self.assertEqual(SimulatedCorel.calls,['0','1'])
        self.job['result']=result['result'];self.job['payload']['students'][0]['data'].pop('fail');SimulatedCorel.calls=[]
        result=self.run_job();self.assertEqual(result['state'],'completed');self.assertEqual(SimulatedCorel.calls,['0'])
    def test_changed_approved_photo_fails_closed(self):
        (self.root/'approved/0.jpg').write_bytes(b'wrong photograph')
        result=self.run_job();self.assertEqual(result['state'],'partial');self.assertNotIn('0',SimulatedCorel.calls)
if __name__=='__main__':unittest.main()
