"""Offline maintenance. Stop application before backup, restore or cleanup."""
import argparse, hashlib, json, shutil, sqlite3, tempfile, zipfile, os, time
from pathlib import Path
from .config import ROOT, initialize

def require_stopped(root):
    lock=root/'runtime.lock'
    if lock.exists():
        raise RuntimeError('Stop ID Card Studio first; runtime.lock is present')

def backup(root=ROOT):
    root=Path(root); require_stopped(root); initialize()
    destination=root/'backups'/('backup-'+time.strftime('%Y%m%d-%H%M%S')+'.zip')
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/'studio.db'
        with sqlite3.connect(root/'database/studio.db') as source, sqlite3.connect(snapshot) as target: source.backup(target)
        manifest={}
        with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
            paths=[snapshot]+[p for folder in ('projects','originals','approved','templates','generated') for p in (root/folder).rglob('*') if p.is_file()]
            for path in paths:
                name='database/studio.db' if path==snapshot else path.relative_to(root).as_posix()
                z.write(path,name); manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            z.writestr('manifest.json',json.dumps({'version':1,'files':manifest}))
    return destination

def restore(archive,root=ROOT):
    root=Path(root); require_stopped(root)
    allowed={'database','projects','originals','approved','templates','generated'}
    with tempfile.TemporaryDirectory(dir=root.parent) as tmp:
        stage=Path(tmp)
        with zipfile.ZipFile(archive) as z:
            if sum(x.file_size for x in z.infolist())>100*1024**3: raise ValueError('Archive exceeds 100 GB')
            if len(z.namelist())!=len(set(z.namelist())): raise ValueError('Duplicate archive names')
            manifest=json.loads(z.read('manifest.json'))
            if manifest['version']!=1: raise ValueError('Unsupported backup format')
            if set(z.namelist())!=set(manifest['files'])|{'manifest.json'}: raise ValueError('Unexpected archive members')
            for name,digest in manifest['files'].items():
                target=(stage/name).resolve()
                if not target.is_relative_to(stage) or Path(name).parts[0] not in allowed or '\\' in name: raise ValueError('Unsafe archive path')
                content=z.read(name)
                if hashlib.sha256(content).hexdigest()!=digest: raise ValueError('Backup checksum mismatch')
                target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
        with sqlite3.connect(stage/'database/studio.db') as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Invalid backup database')
            db.execute("UPDATE jobs SET state='interrupted' WHERE state='running'")
        # Retain a complete rollback directory. Installation tokens stay local.
        rollback=root.parent/(root.name+'-before-restore-'+str(time.time_ns()))
        rollback.mkdir()
        moved=[]
        try:
            for folder in allowed:
                dest=root/folder
                if dest.exists(): shutil.move(str(dest),str(rollback/folder))
                moved.append(folder)
                if (stage/folder).exists(): shutil.move(str(stage/folder),str(dest))
                else: dest.mkdir()
        except Exception:
            for folder in reversed(moved):
                shutil.rmtree(root/folder,ignore_errors=True)
                if (rollback/folder).exists(): shutil.move(str(rollback/folder),str(root/folder))
            raise
    return rollback

def cleanup(root=ROOT):
    require_stopped(root)
    with sqlite3.connect(root/'database/studio.db') as db:
        row=db.execute("SELECT value FROM settings WHERE key='preferences'").fetchone()
        days=json.loads(row[0]).get('retention_days',30) if row else 30
        referenced={p for row in db.execute('SELECT original, approved FROM captures') for p in row if p}
        for (payload,) in db.execute('SELECT payload FROM jobs'):
            referenced.update(s['photo'] for s in json.loads(payload).get('students',[]))
    cutoff=time.time()-days*86400; count=0
    for folder in ('tmp','inbox','originals','approved'):
        for p in (root/folder).glob('*'):
            if p.is_file() and p.stat().st_mtime<cutoff and p.relative_to(root).as_posix() not in referenced:
                p.unlink(); count+=1
    return count

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['init','backup','restore','cleanup']); parser.add_argument('--archive'); args=parser.parse_args()
    initialize()
    if args.command=='backup': print(backup())
    elif args.command=='restore':
        if not args.archive: parser.error('--archive required')
        print('Rollback retained at',restore(args.archive))
    elif args.command=='cleanup': print('Removed',cleanup(),'unreferenced files')
