import io, json, sqlite3, zipfile
from pathlib import Path
import pytest

def test_backup_restore_and_checksum(client,institution):
    from backend.app.config import ROOT
    from backend.app.maintenance import backup,restore
    from backend.app.db import engine
    # Test fixture client has no supervisor; dispose SQLite connections before swapping files.
    (ROOT/'originals/probe.jpg').write_bytes(b'asset marker')
    archive=backup();engine.dispose()
    (ROOT/'originals/probe.jpg').unlink()
    rollback=restore(archive)
    assert (ROOT/'originals/probe.jpg').read_bytes()==b'asset marker'
    assert rollback.is_dir()
    with sqlite3.connect(ROOT/'database/studio.db') as db: assert db.execute('select name from institutions').fetchone()[0]=='Test School'
    bad=ROOT/'backups/bad.zip'
    with zipfile.ZipFile(archive) as src,zipfile.ZipFile(bad,'w') as dst:
        for name in src.namelist(): dst.writestr(name,b'corrupt' if name=='originals/probe.jpg' else src.read(name))
    with pytest.raises(ValueError,match='checksum'): restore(bad)

def test_restore_rejects_traversal(tmp_path):
    from backend.app.maintenance import restore
    import hashlib
    root=tmp_path/'data';root.mkdir();bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr('../outside',b'x');z.writestr('manifest.json',json.dumps({'version':1,'files':{'../outside':hashlib.sha256(b'x').hexdigest()}}))
    with pytest.raises(ValueError,match='Unsafe'):restore(bad,root)
    assert not (tmp_path/'outside').exists()

def test_print_sheet_physical_dimensions_and_duplex(tmp_path):
    pytest.importorskip('pypdf');pytest.importorskip('reportlab')
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader
    from backend.app.printing import impose,MM
    inputs=[]
    for i in range(3):
        path=tmp_path/f'{i}.pdf';c=canvas.Canvas(str(path),pagesize=(85.6*MM,54*MM))
        for side in ('front','back'): c.drawString(10,10,f'{i} {side}');c.showPage()
        c.save();inputs.append(path)
    out=tmp_path/'sheets.pdf';impose(inputs,out,duplex='long-edge')
    pages=PdfReader(out).pages;assert len(pages)==2
    assert abs(float(pages[0].mediabox.width)/MM-210)<.001
    assert all(f'{i} front' in pages[0].extract_text() for i in range(3))
    assert all(f'{i} back' in pages[1].extract_text() for i in range(3))
    with pytest.raises(ValueError,match='dimensions'): impose(inputs,out,card_width=80,duplex='long-edge')

def test_folder_transfer_stability_and_dedup(tmp_path):
    pytest.importorskip('PIL')
    import sys
    sys.path.insert(0,str(Path('windows-agent').resolve()))
    from camera.adapters import FolderAdapter
    from PIL import Image
    root=tmp_path/'data';(root/'inbox').mkdir(parents=True);(root/'originals').mkdir();folder=tmp_path/'tether';folder.mkdir()
    watcher=FolderAdapter(root);watcher.poll(str(folder))
    image=folder/'DSC_1.jpg';image.write_bytes(b'incomplete')
    for _ in range(5):watcher.poll(str(folder))
    assert not list((root/'inbox').glob('*.json'))
    Image.new('RGB',(400,500),'blue').save(image)
    for _ in range(5):watcher.poll(str(folder))
    assert len(list((root/'inbox').glob('*.json')))==1
    (folder/'copy.jpg').write_bytes(image.read_bytes())
    for _ in range(5):watcher.poll(str(folder))
    assert len(list((root/'inbox').glob('*.json')))==1
