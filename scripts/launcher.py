"""Single interactive-user supervisor with browser launch and graceful shutdown."""
import json, logging, os, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from backend.app.config import ROOT, initialize, token
initialize()
logging.basicConfig(filename=ROOT/'logs/launcher.log',level=logging.INFO,format='%(asctime)s %(message)s')
URL='http://127.0.0.1:8765'

def main():
    os.chdir(PROJECT)
    lock=(ROOT/'launcher.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0)
    import msvcrt
    try: msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        webbrowser.open(URL+'/#token='+token()); return
    # Never reuse an unrelated listener on the application port.
    with socket.socket() as probe:
        try: probe.bind(('127.0.0.1',8765))
        except OSError: raise RuntimeError('Port 8765 is occupied. Stop the other process before launching.')
    shutdown=ROOT/'shutdown.request';shutdown.unlink(missing_ok=True)
    runtime=ROOT/'runtime.lock';runtime.write_text(json.dumps({'pid':os.getpid()}))
    processes=[]; agent=None
    python=Path(sys.executable).with_name('python.exe')
    flags=subprocess.CREATE_NO_WINDOW
    backend_log=(ROOT/'logs/backend.log').open('a'); agent_log=(ROOT/'logs/agent-console.log').open('a')
    try:
        backend=subprocess.Popen([str(python),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8765','--no-access-log'],stdout=backend_log,stderr=backend_log,creationflags=flags);processes.append(backend)
        for _ in range(60):
            if backend.poll() is not None: raise RuntimeError('Backend exited; inspect logs/backend.log')
            try:
                with urllib.request.urlopen(URL+'/api/health',timeout=1) as response:
                    if response.status==200: break
            except Exception: time.sleep(1)
        else: raise RuntimeError('Backend did not become ready')
        agent=subprocess.Popen([str(python),'windows-agent/agent.py'],stdout=agent_log,stderr=agent_log,creationflags=flags);processes.append(agent)
        webbrowser.open(URL+'/#token='+token())
        while not shutdown.exists():
            if any(p.poll() is not None for p in processes): raise RuntimeError('A supervised process exited; inspect application logs and restart')
            time.sleep(1)
        # Ask agent to stop claiming and finish its active worker before backend shutdown.
        (ROOT/'agent-stop.request').touch()
        try: agent.wait(timeout=190)
        except subprocess.TimeoutExpired: raise RuntimeError('Agent did not stop within timeout; inspect CorelDRAW')
    finally:
        if agent and agent.poll() is None:
            (ROOT/'agent-stop.request').touch()
            try: agent.wait(timeout=190)
            except subprocess.TimeoutExpired: logging.error('Agent failed to stop; its worker may require manual inspection')
        for p in reversed(processes):
            if p.poll() is None: p.terminate();p.wait(timeout=15)
        backend_log.close();agent_log.close();runtime.unlink(missing_ok=True);shutdown.unlink(missing_ok=True)
if __name__=='__main__':
    try: main()
    except Exception as e:
        logging.exception('Startup or supervisor failure')
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,str(e)+'\nLogs: '+str(ROOT/'logs'),'ID Card Studio',16)
