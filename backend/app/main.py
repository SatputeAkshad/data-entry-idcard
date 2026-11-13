from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib, io, json, secrets, time, csv, zipfile
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from PIL import Image, ImageOps, UnidentifiedImageError
from .config import ROOT, initialize, token, asset
from .db import Session, Institution, Student, Capture, Template, Job, Audit, Setting, serialize, uid, now, audit
from .schemas import InstitutionIn, StudentIn, Crop, JobIn, SheetIn
from .domain import State, transition, validate_fields, validate_student, validate_mapping

initialize()
@asynccontextmanager
async def lifespan(app):
    # Interrupted COM work is not automatically replayed. The operator must inspect/retry.
    with Session.begin() as db:
        db.execute(update(Job).where(Job.state == 'running').values(state='interrupted', updated=now()))
    yield
app = FastAPI(title='ID Card Studio', lifespan=lifespan, docs_url=None, redoc_url=None)
ORIGIN = 'http://127.0.0.1:8765'

def db_session():
    with Session.begin() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        yield db

def get(db, model, id):
    item = db.get(model, id)
    if not item: raise HTTPException(404, 'Record not found')
    return item

def owner(request: Request):
    supplied = request.cookies.get('idcs', '')
    if not secrets.compare_digest(supplied, token()): raise HTTPException(401, 'Open the application using Start ID Card Studio')
    if request.method not in ('GET', 'HEAD') and request.headers.get('x-idcs-request') != '1':
        raise HTTPException(403, 'Missing CSRF header')

def agent(request: Request):
    if not secrets.compare_digest(request.headers.get('authorization', ''), 'Bearer '+token('agent')):
        raise HTTPException(401, 'Invalid agent authentication')

@app.middleware('http')
async def local_only(request, call_next):
    if request.headers.get('host') not in ('127.0.0.1:8765', 'testserver'):
        return JSONResponse({'detail':'Invalid host'}, status_code=403)
    origin = request.headers.get('origin')
    if origin and origin != ORIGIN:
        return JSONResponse({'detail':'Invalid origin'}, status_code=403)
    if request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'detail':'Cross-site access blocked'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api'): response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(ValueError)
async def invalid(request, error): return JSONResponse({'detail':str(error)}, status_code=422)
@app.exception_handler(IntegrityError)
async def conflict(request, error): return JSONResponse({'detail':'Conflicting operation; refresh and retry'}, status_code=409)

@app.post('/api/unlock')
async def unlock(request: Request):
    data = await request.json()
    if not secrets.compare_digest(str(data.get('token', '')), token()): raise HTTPException(401, 'Invalid launch token')
    with Session() as db:
        setting = db.get(Setting, 'password')
        if setting:
            digest = hashlib.scrypt(str(data.get('password','')).encode(), salt=bytes.fromhex(setting.value['salt']), n=16384, r=8, p=1).hex()
            if not secrets.compare_digest(digest, setting.value['digest']):
                raise HTTPException(401, 'Owner password required or incorrect')
    response = JSONResponse({'ok':True})
    response.set_cookie('idcs', token(), httponly=True, samesite='strict', max_age=12*3600)
    return response

@app.get('/api/health')
def health(): return {'status':'ok'}

@app.get('/api/dashboard', dependencies=[Depends(owner)])
def dashboard(db=Depends(db_session)):
    students = list(db.scalars(select(Student)))
    return {'institutions':len(list(db.scalars(select(Institution)))), 'students':len(students), 'pending':sum(not s.photo_id for s in students), 'ready':sum(s.status=='ready' for s in students), 'generated':sum(s.status=='generated' for s in students), 'printed':sum(s.status=='printed' for s in students)}

@app.get('/api/institutions', dependencies=[Depends(owner)])
def institutions(db=Depends(db_session)):
    return [serialize(x) for x in db.scalars(select(Institution).order_by(Institution.updated.desc()))]
@app.post('/api/institutions', dependencies=[Depends(owner)])
def create_institution(body: InstitutionIn, db=Depends(db_session)):
    fields = [f.model_dump() for f in body.fields]; validate_fields(fields)
    obj = Institution(name=body.name, year=body.year, fields=fields); db.add(obj); db.flush(); audit(db,'institution.create',obj.id)
    return serialize(obj)
@app.put('/api/institutions/{id}', dependencies=[Depends(owner)])
def edit_institution(id: str, body: InstitutionIn, db=Depends(db_session)):
    obj = get(db, Institution, id); fields = [f.model_dump() for f in body.fields]; validate_fields(fields)
    # Avoid schema edits invalidating existing data and production mappings.
    for student in db.scalars(select(Student).where(Student.institution_id==id)): validate_student(fields, student.data, draft=True)
    for template in db.scalars(select(Template).where(Template.institution_id==id)): validate_mapping(template.mapping, [f['key'] for f in fields])
    obj.name, obj.year, obj.fields, obj.updated = body.name, body.year, fields, now(); audit(db,'institution.edit',id)
    return serialize(obj)

@app.get('/api/students', dependencies=[Depends(owner)])
def students(institution_id: str, q: str='', status: str='', db=Depends(db_session)):
    rows = db.scalars(select(Student).where(Student.institution_id==institution_id).order_by(Student.updated))
    return [serialize(x) for x in rows if (not q or q.casefold() in ' '.join(x.data.values()).casefold()) and (not status or x.status==status or status=='pending' and not x.photo_id)]
@app.post('/api/students', dependencies=[Depends(owner)])
def create_student(body: StudentIn, db=Depends(db_session)):
    inst = get(db, Institution, body.institution_id); validate_student(inst.fields, body.data, body.status=='draft')
    if body.status!='draft': raise ValueError('Create a draft, then approve its photo before saving')
    obj = Student(institution_id=inst.id, data=body.data, status='draft'); db.add(obj); db.flush(); audit(db,'student.create',obj.id)
    inst.updated=now()
    return serialize(obj)
@app.put('/api/students/{id}', dependencies=[Depends(owner)])
def edit_student(id: str, body: StudentIn, db=Depends(db_session)):
    obj = get(db, Student, id)
    if obj.institution_id != body.institution_id: raise ValueError('Institution cannot change')
    if body.revision != obj.revision: raise HTTPException(409, 'Student changed; reload before saving')
    validate_student(get(db, Institution, obj.institution_id).fields, body.data, body.status=='draft')
    if body.status=='ready' and not obj.photo_id: raise ValueError('Approve a photograph first')
    obj.data, obj.status, obj.updated, obj.revision = body.data, body.status, now(), obj.revision+1
    audit(db,'student.edit',id)
    return serialize(obj)
@app.delete('/api/students/{id}', dependencies=[Depends(owner)])
def remove_student(id: str, db=Depends(db_session)):
    obj=get(db,Student,id)
    if any(j.state in ('queued','running','interrupted') and any(s['id']==id for s in j.payload.get('students',[])) for j in db.scalars(select(Job))): raise ValueError('Resolve outstanding production jobs before deletion')
    db.execute(delete(Capture).where(Capture.student_id==id)); db.delete(obj); audit(db,'student.delete',id)
    return {'ok':True, 'note':'Unreferenced image files are removed by offline cleanup after the retention period'}
@app.post('/api/students/{id}/printed', dependencies=[Depends(owner)])
def printed(id: str, db=Depends(db_session)):
    obj=get(db,Student,id)
    if obj.status!='generated': raise ValueError('Generate current student revision first')
    obj.status='printed'; audit(db,'student.printed',id); return serialize(obj)

async def upload_bytes(file: UploadFile, limit=25*1024*1024):
    data=await file.read(limit+1)
    if not data or len(data)>limit: raise ValueError('File empty or exceeds upload limit')
    return data

def image_bytes(data):
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width*im.height>40_000_000: raise ValueError('Image exceeds 40 megapixels')
            if im.format not in ('JPEG','PNG'): raise ValueError('Only JPEG and PNG images are supported')
            im.load(); return ImageOps.exif_transpose(im).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e: raise ValueError('Invalid or incomplete image') from e

@app.post('/api/institutions/{id}/logo', dependencies=[Depends(owner)])
async def logo(id: str, file: UploadFile=File(...), db=Depends(db_session)):
    obj=get(db,Institution,id); im=image_bytes(await upload_bytes(file)); path=f'projects/{uid()}.jpg'; im.save(asset(path),quality=95); obj.logo=path
    return serialize(obj)

@app.post('/api/students/{id}/capture', dependencies=[Depends(owner)])
def capture(id: str, db=Depends(db_session)):
    get(db,Student,id)
    # Close all outstanding sessions, including another browser tab. Approved assets are immutable.
    db.execute(update(Capture).where(Capture.state.in_([State.WAITING,State.REVIEWING,State.RECEIVED])).values(state=State.ERROR))
    obj=Capture(student_id=id,state=State.WAITING); db.add(obj); db.flush()
    return serialize(obj)
@app.get('/api/captures/{id}', dependencies=[Depends(owner)])
def capture_status(id: str, db=Depends(db_session)): return serialize(get(db,Capture,id))

def receive(db, id, data):
    obj=get(db,Capture,id)
    if obj.state != State.WAITING: raise HTTPException(409,'Capture is no longer waiting; start a new capture')
    if (datetime.now(timezone.utc)-datetime.fromisoformat(obj.created)).total_seconds()>300: raise ValueError('Capture expired; start again')
    digest=hashlib.sha256(data).hexdigest()
    if db.scalar(select(Capture).where(Capture.student_id==obj.student_id, Capture.digest==digest)):
        raise ValueError('This exact image was already received; choose a new photograph')
    image_bytes(data)
    with Image.open(io.BytesIO(data)) as source: extension='png' if source.format=='PNG' else 'jpg'
    path=f'originals/{obj.id}.{extension}'; asset(path).write_bytes(data)
    obj.original, obj.digest = path, digest
    obj.state=transition(obj.state,State.RECEIVED); obj.state=transition(obj.state,State.REVIEWING)
    return serialize(obj)
@app.post('/api/captures/{id}/image', dependencies=[Depends(owner)])
async def receive_image(id: str, file: UploadFile=File(...), db=Depends(db_session)): return receive(db,id,await upload_bytes(file))
@app.post('/api/captures/{id}/retake', dependencies=[Depends(owner)])
def retake(id: str, db=Depends(db_session)):
    obj=get(db,Capture,id); obj.state=transition(obj.state,State.RETAKE)
    newer=Capture(student_id=obj.student_id,state=State.WAITING); db.add(newer); db.flush(); return serialize(newer)
@app.post('/api/captures/{id}/approve', dependencies=[Depends(owner)])
def approve(id: str, crop: Crop, db=Depends(db_session)):
    obj=get(db,Capture,id)
    if obj.state!=State.REVIEWING: raise ValueError('Only the current reviewing photo can be approved')
    if crop.left>=crop.right or crop.top>=crop.bottom: raise ValueError('Crop has zero or negative size')
    with Image.open(asset(obj.original)) as source:
        im=ImageOps.exif_transpose(source).convert('RGB').rotate(-crop.rotation,expand=True)
        box=tuple(round(v*n) for v,n in zip((crop.left,crop.top,crop.right,crop.bottom),(im.width,im.height,im.width,im.height)))
        im=im.crop(box)
        if min(im.size)<100: raise ValueError('Crop must be at least 100 pixels per side')
        path=f'approved/{obj.id}.jpg'; im.save(asset(path),quality=98,dpi=(300,300))
    obj.approved=path; obj.state=transition(obj.state,State.APPROVED)
    student=get(db,Student,obj.student_id); student.photo_id=obj.id; student.revision+=1; student.status='draft'; student.updated=now()
    audit(db,'photo.approve',student.id)
    return {'capture':serialize(obj),'student':serialize(student)}

@app.get('/api/assets/{path:path}', dependencies=[Depends(owner)])
def download(path: str):
    p=asset(path)
    if p.parts[len(ROOT.parts)] not in ('projects','originals','approved','generated','templates') or not p.is_file(): raise HTTPException(404)
    return FileResponse(p,filename=p.name if p.suffix.lower() not in ('.jpg','.png') else None)

@app.get('/api/templates', dependencies=[Depends(owner)])
def templates(institution_id: str, db=Depends(db_session)):
    return [serialize(t) for t in db.scalars(select(Template).where(Template.institution_id==institution_id))]
@app.post('/api/templates', dependencies=[Depends(owner)])
async def template(institution_id: str=Form(...),name: str=Form(...),mapping: str=Form(...),settings: str=Form(...),file: UploadFile=File(...),db=Depends(db_session)):
    inst=get(db,Institution,institution_id); mapping=json.loads(mapping); settings=json.loads(settings)
    validate_mapping(mapping,[f['key'] for f in inst.fields])
    if not isinstance(settings,dict): raise ValueError('Template settings must be an object')
    if not (file.filename or '').lower().endswith('.cdr'): raise ValueError('Select a CDR template')
    for key in ('width_mm','height_mm'):
        if not 10<=float(settings.get(key,0))<=500: raise ValueError('Specify card dimensions in millimetres')
    if not isinstance(settings.get('max_chars',{}),dict): raise ValueError('max_chars must be a mapping')
    data=await upload_bytes(file,100*1024*1024)
    id=uid(); path=f'templates/{id}.cdr'; asset(path).write_bytes(data)
    obj=Template(id=id,institution_id=institution_id,name=name[:200],path=path,mapping=mapping,settings=settings); db.add(obj); db.flush(); audit(db,'template.create',id)
    return serialize(obj)
@app.post('/api/templates/{id}/inspect', dependencies=[Depends(owner)])
def inspect_template(id: str,db=Depends(db_session)):
    t=get(db,Template,id); job=Job(key=uid(),kind='inspect',payload={'template':serialize(t)}); db.add(job); db.flush(); return serialize(job)

@app.post('/api/jobs', dependencies=[Depends(owner)])
def generation(body: JobIn, db=Depends(db_session)):
    existing=db.scalar(select(Job).where(Job.key==body.key))
    if existing: return serialize(existing)
    t=get(db,Template,body.template_id); snapshots=[]
    for id in dict.fromkeys(body.student_ids):
        s=get(db,Student,id)
        if s.institution_id!=t.institution_id or s.status=='draft' or not s.photo_id: raise ValueError('Every selected student must be saved with an approved photo in this institution')
        p=get(db,Capture,s.photo_id)
        if p.student_id!=s.id or p.state!=State.APPROVED: raise ValueError('Invalid approved photo association')
        snapshots.append({**serialize(s),'photo':p.approved,'photo_sha256':hashlib.sha256(asset(p.approved).read_bytes()).hexdigest()})
    obj=Job(key=body.key,payload={'template':serialize(t),'students':snapshots}); db.add(obj); db.flush(); audit(db,'production.queue',obj.id); return serialize(obj)
@app.get('/api/jobs', dependencies=[Depends(owner)])
def jobs(db=Depends(db_session)): return [serialize(j) for j in db.scalars(select(Job).order_by(Job.created.desc()).limit(100))]
@app.post('/api/jobs/{id}/retry', dependencies=[Depends(owner)])
def retry(id: str,db=Depends(db_session)):
    job=get(db,Job,id)
    if job.state not in ('failed','partial','interrupted'): raise ValueError('Only failed or interrupted jobs can be retried')
    job.state='queued'; job.updated=now(); return serialize(job)
@app.post('/api/jobs/{id}/cancel', dependencies=[Depends(owner)])
def cancel(id: str,db=Depends(db_session)):
    job=get(db,Job,id)
    if job.state not in ('queued','interrupted'): raise ValueError('Running jobs must finish or time out before cancellation')
    job.state='cancelled'; return serialize(job)

@app.get('/api/inbox', dependencies=[Depends(owner)])
def inbox():
    result=[]
    for p in sorted((ROOT/'inbox').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
        item=json.loads(p.read_text()); result.append({'id':p.stem,**item})
    return result
@app.post('/api/captures/{id}/inbox/{item}', dependencies=[Depends(owner)])
def attach_inbox(id: str,item: str,db=Depends(db_session)):
    if not item.replace('-','').isalnum(): raise ValueError('Invalid inbox ID')
    meta=asset(f'inbox/{item}.json')
    if not meta.exists(): raise HTTPException(404)
    value=json.loads(meta.read_text()); response=receive(db,id,asset(value['path']).read_bytes())
    # A global digest check prevents the same tethered image being assigned to two students.
    duplicates=list(db.scalars(select(Capture).where(Capture.digest==response['digest'],Capture.id!=id)))
    if duplicates: raise ValueError('Image already assigned to another capture')
    return response

@app.get('/api/settings', dependencies=[Depends(owner)])
def settings(db=Depends(db_session)):
    row=db.get(Setting,'preferences'); status=db.get(Setting,'agent_status')
    return {'preferences':row.value if row else {'watch_folder':'','retention_days':30},'agent':status.value if status else {'status':'offline'}, 'data_directory':str(ROOT)}
@app.put('/api/settings', dependencies=[Depends(owner)])
async def save_settings(request: Request,db=Depends(db_session)):
    body=await request.json(); folder=str(body.get('watch_folder','')); days=int(body.get('retention_days',30))
    if folder and not Path(folder).is_absolute(): raise ValueError('Watch folder must be an absolute path')
    if days<1 or days>3650: raise ValueError('Retention must be between 1 and 3650 days')
    db.merge(Setting(key='preferences',value={'watch_folder':folder,'retention_days':days})); return {'ok':True}
@app.post('/api/settings/password', dependencies=[Depends(owner)])
async def password(request: Request,db=Depends(db_session)):
    value=str((await request.json()).get('password',''))
    if len(value)<10: raise ValueError('Use at least 10 characters')
    salt=secrets.token_bytes(16); digest=hashlib.scrypt(value.encode(),salt=salt,n=16384,r=8,p=1).hex()
    db.merge(Setting(key='password',value={'salt':salt.hex(),'digest':digest})); return {'ok':True}

@app.post('/api/agent/heartbeat', dependencies=[Depends(agent)])
async def heartbeat(request: Request,db=Depends(db_session)):
    body=await request.json(); db.merge(Setting(key='agent_status',value={**body,'seen':now()}))
    pref=db.get(Setting,'preferences'); return pref.value if pref else {}
@app.post('/api/agent/claim', dependencies=[Depends(agent)])
def claim(db=Depends(db_session)):
    if db.scalar(select(Job).where(Job.state=='running')): return None
    job=db.scalar(select(Job).where(Job.state=='queued').order_by(Job.created))
    if not job: return None
    changed=db.execute(update(Job).where(Job.id==job.id,Job.state=='queued').values(state='running',updated=now()))
    if changed.rowcount!=1: return None
    db.refresh(job); return serialize(job)
@app.post('/api/agent/jobs/{id}', dependencies=[Depends(agent)])
async def job_result(id: str, request: Request,db=Depends(db_session)):
    job=get(db,Job,id); body=await request.json()
    if job.state!='running': raise HTTPException(409,'Job no longer running')
    if body.get('state') not in ('running','completed','partial','failed','interrupted'): raise ValueError('Invalid job state')
    job.state=body['state']; job.result=body['result']; job.updated=now()
    for snap in job.payload.get('students',[]):
        s=db.get(Student,snap['id'])
        if s and s.revision==snap['revision'] and job.result.get('items',{}).get(s.id,{}).get('state')=='completed': s.status='generated'
    return {'ok':True}

@app.post('/api/institutions/{id}/import', dependencies=[Depends(owner)])
async def import_students(id: str,file: UploadFile=File(...),db=Depends(db_session)):
    inst=get(db,Institution,id); data=await upload_bytes(file)
    if (file.filename or '').lower().endswith('.csv'):
        reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)): raise ValueError('Missing or duplicate import headers')
        rows=list(reader)
    elif (file.filename or '').lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist())>100*1024*1024: raise ValueError('Expanded workbook exceeds 100 MB')
        wb=load_workbook(io.BytesIO(data),read_only=True,data_only=True); iterator=wb.active.iter_rows(values_only=True); headers=next(iterator,None)
        if not headers or len(set(headers))!=len(headers): raise ValueError('Missing or duplicate headers')
        rows=[dict(zip(headers,('' if v is None else str(v) for v in row))) for row in iterator]; wb.close()
    else: raise ValueError('Use CSV or XLSX')
    if len(rows)>10000: raise ValueError('Import at most 10,000 rows')
    for i,row in enumerate(rows,2):
        if None in row: raise ValueError(f'Row {i}: malformed columns')
        try: validate_student(inst.fields,row)
        except ValueError as e: raise ValueError(f'Row {i}: {e}')
    for row in rows: db.add(Student(institution_id=id,data=row,status='draft'))
    audit(db,'students.import',id); return {'imported':len(rows)}
@app.get('/api/institutions/{id}/export', dependencies=[Depends(owner)])
def export_students(id: str,format: str='csv',db=Depends(db_session)):
    inst=get(db,Institution,id); keys=[f['key'] for f in inst.fields]
    def safe(v): return "'"+v if v.startswith(('=','+','-','@','\t','\r')) else v
    rows=[[safe(s.data.get(k,'')) for k in keys] for s in db.scalars(select(Student).where(Student.institution_id==id))]
    if format=='xlsx':
        from openpyxl import Workbook
        wb=Workbook(); ws=wb.active; ws.append(keys)
        for row in rows: ws.append(row)
        out=io.BytesIO(); wb.save(out); content=out.getvalue(); mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        out=io.StringIO(); writer=csv.writer(out); writer.writerow(keys); writer.writerows(rows); content=out.getvalue().encode('utf-8-sig'); mime='text/csv'; format='csv'
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="students.{format}"'})

@app.post('/api/jobs/{id}/sheets', dependencies=[Depends(owner)])
def sheets(id: str,body: SheetIn,db=Depends(db_session)):
    from .printing import impose
    job=get(db,Job,id)
    if job.state not in ('completed','partial'): raise ValueError('Finish generation first')
    files=[asset(v['pdf']) for v in job.result.get('items',{}).values() if v.get('state')=='completed']
    if not files: raise ValueError('No completed PDFs')
    relative=f'generated/{id}/sheets-{uid()}.pdf'; impose(files,asset(relative),**body.model_dump()); audit(db,'production.sheets',id)
    return {'path':relative}
@app.get('/api/jobs/{id}/zip', dependencies=[Depends(owner)])
def job_zip(id: str,db=Depends(db_session)):
    job=get(db,Job,id); directory=asset(f'generated/{id}')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        paths=[asset(item[key]) for item in job.result.get('items',{}).values() if item.get('state')=='completed' for key in ('cdr','pdf','preview') if item.get(key)]
        paths.extend(directory.glob('sheets-*.pdf'))
        for p in paths:
            if p.is_file(): z.write(p,p.name)
    return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{id}.zip"'})

# Static export is served by the same origin as API; no Node process needed daily.
frontend=Path(__file__).resolve().parents[2]/'frontend/out'
if frontend.exists(): app.mount('/',StaticFiles(directory=frontend,html=True),name='frontend')
