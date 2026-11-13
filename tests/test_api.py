import io, json, uuid
import pytest

def create(client,inst,name='Student One'):
    r=client.post('/api/students',json={'institution_id':inst['id'],'data':{'full_name':name,'student_id':str(uuid.uuid4()),'class':'1'},'status':'draft'})
    assert r.status_code==200,r.text
    return r.json()
def photo(color):
    Image=pytest.importorskip('PIL.Image'); out=io.BytesIO(); Image.new('RGB',(500,600),color).save(out,format='JPEG'); return out.getvalue()
def start(client,s): return client.post('/api/students/'+s['id']+'/capture').json()
def receive(client,c,color): return client.post('/api/captures/'+c['id']+'/image',files={'file':('photo.jpg',photo(color),'image/jpeg')})
def ready(client,inst,s,color='blue'):
    c=start(client,s);assert receive(client,c,color).status_code==200
    approved=client.post('/api/captures/'+c['id']+'/approve',json={}); assert approved.status_code==200,approved.text
    s=approved.json()['student'];r=client.put('/api/students/'+s['id'],json={'institution_id':inst['id'],'data':s['data'],'revision':s['revision'],'status':'ready'}); assert r.status_code==200,r.text
    return r.json()
def template(client,inst):
    r=client.post('/api/templates',data={'institution_id':inst['id'],'name':'Test template','mapping':json.dumps({'NAME':'full_name','PHOTO':'photo'}),'settings':json.dumps({'width_mm':85.6,'height_mm':54})},files={'file':('test.cdr',b'SIMULATED CDR fixture; never sent to real CorelDRAW','application/octet-stream')});assert r.status_code==200,r.text
    return r.json()

def test_student_crud_and_revision(client,institution):
    s=create(client,institution)
    bad=client.put('/api/students/'+s['id'],json={'institution_id':institution['id'],'data':s['data'],'revision':0,'status':'draft'});assert bad.status_code==409
    updated=client.put('/api/students/'+s['id'],json={'institution_id':institution['id'],'data':{**s['data'],'full_name':'Updated'},'revision':1,'status':'draft'});assert updated.status_code==200
    assert client.get('/api/students',params={'institution_id':institution['id'],'q':'Updated'}).json()[0]['id']==s['id']
    assert client.delete('/api/students/'+s['id']).status_code==200
    assert client.get('/api/students',params={'institution_id':institution['id']}).json()==[]

def test_import_atomic_validation_and_export(client,institution):
    r=client.post('/api/institutions/'+institution['id']+'/import',files={'file':('test.csv',b'full_name,student_id,class\nAlice,1,1\nBob,2,invalid\n')});assert r.status_code==422
    assert client.get('/api/students',params={'institution_id':institution['id']}).json()==[]
    r=client.post('/api/institutions/'+institution['id']+'/import',files={'file':('test.csv',b'full_name,student_id,class\nAlice,1,1\nBob,2,2\n')});assert r.json()['imported']==2
    assert 'Alice' in client.get('/api/institutions/'+institution['id']+'/export').text
    assert client.get('/api/institutions/'+institution['id']+'/export?format=xlsx').content.startswith(b'PK')

def test_capture_retake_matching_and_next(client,institution):
    s=create(client,institution);c=start(client,s)
    assert receive(client,c,'red').status_code==200
    c2=client.post('/api/captures/'+c['id']+'/retake').json()
    assert client.post('/api/captures/'+c['id']+'/approve',json={}).status_code==422
    assert receive(client,c,'green').status_code==409
    assert receive(client,c2,'blue').status_code==200
    approved=client.post('/api/captures/'+c2['id']+'/approve',json={'left':.1,'right':.9}).json()
    assert approved['student']['photo_id']==c2['id']
    second=create(client,institution,'Student Two');assert second['photo_id'] is None
    c3=start(client,second)
    assert client.get('/api/captures/'+c3['id']).json()['original'] is None
    assert client.post('/api/captures/'+c2['id']+'/approve',json={}).status_code==422

def test_late_capture_invalidated(client,institution):
    first=create(client,institution);old=start(client,first)
    second=create(client,institution,'Next');start(client,second)
    assert receive(client,old,'green').status_code==409

def test_approval_requires_valid_crop(client,institution):
    s=create(client,institution);c=start(client,s);receive(client,c,'white')
    assert client.post('/api/captures/'+c['id']+'/approve',json={'left':.8,'right':.2}).status_code==422
    assert client.post('/api/captures/'+c['id']+'/approve',json={'left':.99}).status_code==422

def test_queue_snapshot_idempotency_retry(client,institution):
    from backend.app.config import token
    s=ready(client,institution,create(client,institution));t=template(client,institution)
    payload={'key':str(uuid.uuid4()),'template_id':t['id'],'student_ids':[s['id']]}
    j=client.post('/api/jobs',json=payload).json();assert client.post('/api/jobs',json=payload).json()['id']==j['id']
    headers={'authorization':'Bearer '+token('agent')}
    claimed=client.post('/api/agent/claim',headers=headers).json();assert claimed['id']==j['id']
    assert claimed['payload']['students'][0]['photo']==f"approved/{s['photo_id']}.jpg"
    assert client.post('/api/agent/claim',headers=headers).json() is None
    r=client.post('/api/agent/jobs/'+j['id'],headers=headers,json={'state':'failed','result':{'items':{s['id']:{'state':'failed','error':'SIMULATION: disconnected'}}}});assert r.status_code==200
    assert client.post('/api/jobs/'+j['id']+'/retry').json()['state']=='queued'
    assert client.post('/api/agent/claim',headers=headers).json()['id']==j['id']

def test_cross_institution_production_rejected(client,institution):
    s=ready(client,institution,create(client,institution));t=template(client,institution)
    other=client.post('/api/institutions',json={'name':'Other','year':'2026','fields':institution['fields']}).json()
    t=template(client,other)
    assert client.post('/api/jobs',json={'key':str(uuid.uuid4()),'template_id':t['id'],'student_ids':[s['id']]}).status_code==422

def test_security_boundaries(client):
    assert client.post('/api/agent/claim').status_code==401
    assert client.get('/api/dashboard',headers={'origin':'https://evil.example'}).status_code==403
    assert client.get('/api/dashboard',headers={'host':'evil.example'}).status_code==403
    assert client.post('/api/settings',headers={'x-idcs-request':''},json={}).status_code in (403,405)
    assert client.get('/api/assets/database/studio.db').status_code==404
    assert client.get('/api/assets/../owner-token').status_code in (404,422)

def test_schema_edit_rejects_orphan_fields(client,institution):
    create(client,institution)
    r=client.put('/api/institutions/'+institution['id'],json={'name':'Updated','year':'2027','fields':[institution['fields'][0]]});assert r.status_code==422
