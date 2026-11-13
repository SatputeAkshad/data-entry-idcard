import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from camera.adapters import discover
from coreldraw.adapter import registered_servers, CorelAdapter
from backend.app.config import ROOT, initialize

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--corel-test',action='store_true'); args=parser.parse_args(); initialize()
    result={'windows':os.name=='nt','camera':discover(),'corel_registration':registered_servers(),'data_directory':str(ROOT)}
    if args.corel_test:
        try:
            with CorelAdapter() as corel: result['corel_test']=corel.diagnostic(ROOT/'tmp/diagnostic')
        except Exception as e: result['corel_test']={'error':str(e)}
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
