"""Nikon capabilities are deliberately not inferred from USB device presence."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, os, shutil, subprocess, time, uuid
from PIL import Image

@dataclass
class Capabilities:
    mode: str
    remote_shutter: bool = False
    live_view: bool = False
    receive_images: bool = True
    detail: str = ''

class ManualAdapter:
    capabilities=Capabilities('manual',detail='Select a JPEG/PNG through the photo approval screen')

class NikonSDKAdapter:
    capabilities=Capabilities('nikon-sdk',receive_images=False,detail='Unavailable: camera model and licensed Nikon SDK integration must be verified first')
    def capture(self): raise RuntimeError(self.capabilities.detail)

def discover():
    if os.name!='nt': return {'devices':[],'detail':'Windows discovery unavailable on this operating system'}
    command="Get-PnpDevice -PresentOnly | Where-Object { $_.FriendlyName -match 'Nikon' -or $_.InstanceId -match 'VID_04B0' } | Select-Object FriendlyName,Status,InstanceId | ConvertTo-Json -Compress"
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=20,check=True)
        devices=json.loads(result.stdout or '[]'); devices=devices if isinstance(devices,list) else [devices]
        return {'devices':devices,'detail':'USB presence does not establish remote shutter/live-view support. Use one camera-control application at a time.'}
    except Exception as e: return {'devices':[],'detail':str(e)}

class FolderAdapter:
    """Polling handles missed notifications. Inbox is unassigned until operator confirms.

    Existing files are baselined on folder change, and files must remain unchanged
    for three polls and pass a full image decode. RAW files are not accepted.
    """
    capabilities=Capabilities('watched-folder',detail='Trigger shutter in Nikon software or on camera; explicitly select received image')
    def __init__(self, root):
        self.root=Path(root); self.folder=None; self.baseline={}; self.pending={}
        self.seen=set()
        for p in (self.root/'inbox').glob('*.json'):
            try: self.seen.add(json.loads(p.read_text())['sha256'])
            except (ValueError,KeyError): pass
    def poll(self, folder):
        folder=Path(folder) if folder else None
        if folder!=self.folder:
            self.folder=folder; self.pending={}
            self.baseline={str(p):(p.stat().st_size,p.stat().st_mtime_ns) for p in folder.iterdir() if p.is_file()} if folder and folder.is_dir() else {}
            return
        if not folder: return
        if not folder.is_dir(): raise ValueError('Tether folder is unavailable')
        for p in folder.iterdir():
            if not p.is_file() or p.suffix.lower() not in ('.jpg','.jpeg','.png'): continue
            stat=p.stat(); sig=(stat.st_size,stat.st_mtime_ns); key=str(p)
            if self.baseline.get(key)==sig: continue
            last,count=self.pending.get(key,(None,0)); count=count+1 if last==sig else 0; self.pending[key]=(sig,count)
            if count<3 or stat.st_size==0 or stat.st_size>25*1024*1024: continue
            try:
                data=p.read_bytes(); digest=hashlib.sha256(data).hexdigest()
                if digest in self.seen: self.baseline[key]=sig; continue
                import io
                with Image.open(io.BytesIO(data)) as im:
                    if im.width*im.height>40_000_000: continue
                    im.load(); normalized=im.convert('RGB')
                if (p.stat().st_size,p.stat().st_mtime_ns)!=sig: continue
                id=str(uuid.uuid4()); relative=f'originals/inbox-{id}{p.suffix.lower()}'; (self.root/relative).write_bytes(data)
                meta={'path':relative,'source_name':p.name,'received':time.time(),'sha256':digest}
                temporary=self.root/'inbox'/f'{id}.tmp'; temporary.write_text(json.dumps(meta)); temporary.replace(temporary.with_suffix('.json'))
                self.seen.add(digest); self.baseline[key]=sig
            except (OSError,ValueError): continue
