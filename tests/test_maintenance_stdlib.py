"""Backup/restore safety tests runnable without application dependencies."""
import hashlib,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from backend.app.maintenance import backup,restore,require_stopped
class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'data';self.root.mkdir()
        for name in ('database','projects','originals','approved','templates','generated','backups'): (self.root/name).mkdir()
        with sqlite3.connect(self.root/'database/studio.db') as db:
            db.execute('create table jobs(state text)');db.execute("insert into jobs values ('running')")
        (self.root/'originals/photo.jpg').write_bytes(b'original photo fixture')
    def test_roundtrip_and_interrupted_job_recovery(self):
        with patch('backend.app.maintenance.initialize'): archive=backup(self.root)
        (self.root/'originals/photo.jpg').write_bytes(b'changed')
        old=restore(archive,self.root)
        self.assertEqual((self.root/'originals/photo.jpg').read_bytes(),b'original photo fixture')
        self.assertEqual((old/'originals/photo.jpg').read_bytes(),b'changed')
        with sqlite3.connect(self.root/'database/studio.db') as db:self.assertEqual(db.execute('select state from jobs').fetchone()[0],'interrupted')
    def test_restore_tamper_leaves_current_data_untouched(self):
        with patch('backend.app.maintenance.initialize'): archive=backup(self.root)
        bad=self.root/'backups/tampered.zip'
        with zipfile.ZipFile(archive) as source,zipfile.ZipFile(bad,'w') as dest:
            for name in source.namelist():dest.writestr(name,b'tampered' if name=='originals/photo.jpg' else source.read(name))
        with self.assertRaisesRegex(ValueError,'checksum'):restore(bad,self.root)
        self.assertEqual((self.root/'originals/photo.jpg').read_bytes(),b'original photo fixture')
    def test_zip_traversal_rejected(self):
        path=self.root/'backups/unsafe.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('../outside',b'x');z.writestr('manifest.json',json.dumps({'version':1,'files':{'../outside':hashlib.sha256(b'x').hexdigest()}}))
        with self.assertRaisesRegex(ValueError,'Unsafe'):restore(path,self.root)
    def test_live_application_blocks_maintenance(self):
        (self.root/'runtime.lock').touch()
        with self.assertRaisesRegex(RuntimeError,'Stop'):backup(self.root)
        with self.assertRaisesRegex(RuntimeError,'Stop'):restore('does-not-exist',self.root)
if __name__=='__main__':unittest.main()
