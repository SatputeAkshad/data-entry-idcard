"""CorelDRAW 2019 (21) adapter. Call only inside a dedicated STA process.

No user application is quit. Each opened working document is closed independently.
See docs/HARDWARE.md for the mandatory installed-type-library validation.
"""
import os, shutil, json
from pathlib import Path

def registered_servers():
    if os.name!='nt': return []
    import winreg
    found=[]
    for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,'',0,winreg.KEY_READ|view) as root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    name=winreg.EnumKey(root,i)
                    if not name.lower().startswith('coreldraw.application'): continue
                    try:
                        with winreg.OpenKey(root,name+'\\CLSID') as key: clsid=winreg.QueryValue(key,None)
                        with winreg.OpenKey(root,'CLSID\\'+clsid+'\\LocalServer32') as key: server=winreg.QueryValue(key,None)
                        item={'progid':name,'clsid':clsid,'server':server}
                        if item not in found: found.append(item)
                    except OSError: continue
        except OSError: continue
    return found

class CorelAdapter:
    def __enter__(self):
        import pythoncom, win32com.client
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        self.pythoncom=pythoncom; self.app=None
        try:
            candidates=[s for s in registered_servers() if s['progid'].lower().endswith('.21')]
            if not candidates: raise RuntimeError('CorelDRAW 21 version-specific COM registration not found. Repair installation/automation components.')
            self.app=win32com.client.gencache.EnsureDispatch(candidates[0]['progid'])
            if int(self.app.VersionMajor)!=21: raise RuntimeError('Connected application is not CorelDRAW 21')
            self.app.Visible=True
            self.constants=win32com.client.constants
            # Fail closed if the installed type library cannot supply required enum values.
            for constant in ('cdrMillimeter','cdrTextShape','cdrGroupShape','cdrTrue'): getattr(self.constants,constant)
            return self
        except Exception:
            self.app=None; pythoncom.CoUninitialize(); raise
    def __exit__(self,*args):
        self.app=None; self.pythoncom.CoUninitialize()
    def shapes(self, collection):
        for i in range(1,collection.Count+1):
            shape=collection.Item(i); yield shape
            if shape.Type==self.constants.cdrGroupShape: yield from self.shapes(shape.Shapes)
    def named(self, doc):
        result={}
        for i in range(1,doc.Pages.Count+1):
            page=doc.Pages.Item(i)
            for shape in self.shapes(page.Shapes):
                if shape.Name: result.setdefault(str(shape.Name),[]).append(shape)
        return result
    def inspect(self,path):
        doc=self.app.OpenDocument(str(path))
        try:
            doc.Unit=self.constants.cdrMillimeter
            return {'version':str(self.app.VersionMajor),'pages':doc.Pages.Count,'width_mm':doc.Pages.Item(1).SizeWidth,'height_mm':doc.Pages.Item(1).SizeHeight,'objects':[{'name':name,'count':len(shapes),'type':int(shapes[0].Type),'text':shapes[0].Text.Story.Text if shapes[0].Type==self.constants.cdrTextShape else ''} for name,shapes in self.named(doc).items()]}
        finally:
            # Only disposable copies or diagnostic documents are opened by this adapter.
            # Save changes to those copies to avoid an unattended close/save prompt.
            doc.Save()
            doc.Close()
    def generate(self,template,student,root,output):
        root=Path(root); output=Path(output); output.mkdir(parents=True,exist_ok=True)
        # Unique per student/job copy, never the original registered CDR.
        final_cdr=output/(student['id']+'.cdr'); final_pdf=output/(student['id']+'.pdf')
        cdr=root/'tmp'/(output.name+'-'+student['id']+'.cdr'); pdf=cdr.with_suffix('.pdf')
        shutil.copy2(root/template['path'],cdr)
        doc=self.app.OpenDocument(str(cdr))
        try:
            doc.Unit=self.constants.cdrMillimeter
            cfg=template['settings']; names=self.named(doc)
            for object_name,field in template['mapping'].items():
                matches=names.get(object_name,[])
                if len(matches)!=1: raise ValueError(f'{object_name}: expected exactly one named object; found {len(matches)}')
                shape=matches[0]
                if field=='photo':
                    if min(shape.SizeWidth,shape.SizeHeight)<=0: raise ValueError('Photo frame has no size')
                    width,height=shape.SizeWidth,shape.SizeHeight
                    shape.Layer.Import(str(root/student['photo']))
                    photo=doc.Selection().Shapes.Item(1)
                    factor=max(width/photo.SizeWidth,height/photo.SizeHeight)
                    photo.SetSize(photo.SizeWidth*factor,photo.SizeHeight*factor)
                    photo.AddToPowerClip(shape,self.constants.cdrTrue)
                else:
                    if shape.Type!=self.constants.cdrTextShape: raise ValueError(f'{object_name} is not a text object')
                    value=student['data'].get(field,'')
                    limit=int(cfg.get('max_chars',{}).get(field,80))
                    if len(value)>limit: raise ValueError(f'{field} exceeds configured length {limit}; adjust template or record')
                    old_width,old_height=shape.SizeWidth,shape.SizeHeight
                    shape.Text.Story.Text=value
                    # Never silently shrink/change fonts; require a review for expanded bounds.
                    if shape.SizeWidth>old_width+.2 or shape.SizeHeight>old_height+.2:
                        raise ValueError(f'{object_name} exceeds placeholder bounds; enlarge placeholder in the template')
            bleed=float(cfg.get('bleed_mm',0))
            for index in range(1,doc.Pages.Count+1):
                page=doc.Pages.Item(index)
                if abs(page.SizeWidth-(float(cfg['width_mm'])+2*bleed))>.2 or abs(page.SizeHeight-(float(cfg['height_mm'])+2*bleed))>.2:
                    raise ValueError('Template page size must equal card dimensions plus configured bleed')
            doc.Save()
            # Print PDF settings must be configured and verified in CorelDRAW before production.
            doc.PublishToPDF(str(pdf))
            if not pdf.exists() or pdf.stat().st_size==0: raise RuntimeError('CorelDRAW produced no PDF')
            shutil.copy2(cdr,final_cdr); shutil.copy2(pdf,final_pdf)
            return {'cdr':final_cdr.relative_to(root).as_posix(),'pdf':final_pdf.relative_to(root).as_posix(),'state':'completed'}
        finally:
            # Only disposable copies or diagnostic documents are opened by this adapter.
            # Save changes to those copies to avoid an unattended close/save prompt.
            doc.Save()
            doc.Close()
    def diagnostic(self,folder):
        folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
        doc=self.app.CreateDocument()
        try:
            doc.ActiveLayer.CreateArtisticText(1,1,'ID Card Studio CorelDRAW 21 diagnostic')
            doc.SaveAs(str(folder/'diagnostic.cdr')); doc.PublishToPDF(str(folder/'diagnostic.pdf'))
            typelib=self.app._oleobj_.GetTypeInfo().GetContainingTypeLib()[0].GetLibAttr()
            return {'version':int(self.app.VersionMajor),'type_library':str(typelib),'cdr':(folder/'diagnostic.cdr').exists(),'pdf':(folder/'diagnostic.pdf').exists(),'note':'No VBA helper required. Inspect font substitution warnings and exported PDF manually.'}
        finally:
            # Only disposable copies or diagnostic documents are opened by this adapter.
            # Save changes to those copies to avoid an unattended close/save prompt.
            doc.Save()
            doc.Close()
