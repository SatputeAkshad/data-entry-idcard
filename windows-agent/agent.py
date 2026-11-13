"""Supervised interactive-user agent; never install as a Session 0 service."""
import json, logging, os, subprocess, sys, time
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.config import ROOT, initialize, token
from camera.adapters import FolderAdapter, discover, NikonSDKAdapter
from coreldraw.adapter import registered_servers

initialize()
logging.basicConfig(filename=ROOT/'logs/agent.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

def main():
    # OS lock releases on crashes; prevents concurrent agents/COM workers.
    lock=(ROOT/'agent.lock').open('a+b'); lock.write(b'0'); lock.flush(); lock.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stop_request=ROOT/'agent-stop.request'; stop_request.unlink(missing_ok=True)
    watcher=FolderAdapter(ROOT); camera=discover(); servers=registered_servers(); proc=None; current=None; paused=False; last_progress=0; last_content=''; last_discovery=time.monotonic()
    with httpx.Client(base_url='http://127.0.0.1:8765',headers={'Authorization':'Bearer '+token('agent')},timeout=10,trust_env=False) as client:
        while True:
            if stop_request.exists() and (not proc or proc.poll() is not None):
                stop_request.unlink(missing_ok=True); return
            if stop_request.exists() and proc and time.monotonic()-last_progress>180:
                proc.terminate(); proc.wait(timeout=10)
                stop_request.unlink(missing_ok=True); return
            try:
                if time.monotonic()-last_discovery>30:
                    camera=discover(); last_discovery=time.monotonic()
                preferences=client.post('/api/agent/heartbeat',json={'status':'paused' if paused else 'online','camera':camera,'corel_servers':servers,'direct':NikonSDKAdapter.capabilities.__dict__}).raise_for_status().json()
                watcher.poll(preferences.get('watch_folder',''))
                if proc:
                    if result_path.exists():
                        content=result_path.read_text(encoding='utf-8')
                        if content!=last_content:
                            last_progress=time.monotonic(); last_content=content
                            client.post('/api/agent/jobs/'+current['id'],json=json.loads(content)).raise_for_status()
                    if proc.poll() is not None:
                        if not result_path.exists():
                            client.post('/api/agent/jobs/'+current['id'],json={'state':'failed','result':{'error':'Worker exited without a result'}}).raise_for_status()
                        proc=None; current=None
                    elif time.monotonic()-last_progress>180:
                        proc.terminate(); proc.wait(timeout=10)
                        payload=json.loads(last_content) if last_content else {'result':{}}
                        payload.update(state='interrupted'); payload['result']['error']='COM worker timed out. Inspect CorelDRAW and close the job working document; restart agent before retry.'
                        client.post('/api/agent/jobs/'+current['id'],json=payload).raise_for_status()
                        paused=True; proc=None; current=None
                if stop_request.exists() and not proc:
                    stop_request.unlink(missing_ok=True); return
                if not proc and not paused and not stop_request.exists():
                    current=client.post('/api/agent/claim').raise_for_status().json()
                    if current:
                        input_path=ROOT/'tmp'/f"job-{current['id']}.json"; result_path=ROOT/'tmp'/f"result-{current['id']}.json"
                        input_path.write_text(json.dumps(current),encoding='utf-8'); result_path.unlink(missing_ok=True)
                        proc=subprocess.Popen([sys.executable,str(Path(__file__).parent/'jobs/worker.py'),str(input_path),str(ROOT),str(result_path)])
                        last_progress=time.monotonic(); last_content=''
            except Exception:
                logging.exception('Agent cycle failed')
            time.sleep(2)

if __name__=='__main__': main()
