"""Vector-preserving PDF imposition in physical millimetres."""
import io
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject
from reportlab.pdfgen import canvas
from .domain import sheet_positions
MM = 72/25.4

def impose(files, output, width=210, height=297, card_width=85.6, card_height=54, margin=10, gap=5, bleed=0, duplex='none', cutting_marks=True):
    positions=sheet_positions(width,height,card_width,card_height,margin,gap,bleed)
    readers=[PdfReader(str(f)) for f in files]
    sides=1 if duplex=='none' else 2
    for reader in readers:
        if len(reader.pages)!=sides: raise ValueError(f'Expected {sides} PDF page(s) per card; front/back must be pages 1/2')
        for page in reader.pages:
            expected=(card_width+2*bleed,card_height+2*bleed)
            if abs(float(page.mediabox.width)/MM-expected[0])>.2 or abs(float(page.mediabox.height)/MM-expected[1])>.2:
                raise ValueError('PDF dimensions do not match card plus bleed. No automatic scaling is allowed.')
    writer=PdfWriter()
    for start in range(0,len(readers),len(positions)):
        batch=readers[start:start+len(positions)]
        for side in range(sides):
            sheet=PageObject.create_blank_page(width=width*MM,height=height*MM)
            marks=io.BytesIO(); c=canvas.Canvas(marks,pagesize=(width*MM,height*MM)); c.setLineWidth(.25)
            for reader,(x,y) in zip(batch,positions):
                if side==1:
                    if duplex=='long-edge': x=width-x-card_width
                    else: y=height-y-card_height
                px=(x-bleed)*MM; py=(height-y-card_height-bleed)*MM
                page=reader.pages[side]
                transform=Transformation().translate(-float(page.mediabox.left),-float(page.mediabox.bottom)).translate(px,py)
                sheet.merge_transformed_page(page,transform,expand=False)
                if cutting_marks:
                    for xx in (x,x+card_width):
                        for yy in (y,y+card_height):
                            signx=-1 if xx==x else 1; signy=1 if yy==y else -1
                            X,Y=xx*MM,(height-yy)*MM
                            c.line(X+signx*(bleed+.5)*MM,Y,X+signx*(bleed+2)*MM,Y)
                            c.line(X,Y+signy*(bleed+.5)*MM,X,Y+signy*(bleed+2)*MM)
            c.showPage(); c.save(); sheet.merge_page(PdfReader(marks).pages[0]); writer.add_page(sheet)
    with open(output,'wb') as f: writer.write(f)
