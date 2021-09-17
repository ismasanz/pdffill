import io
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas

class PDFFiller:
  def __init__(self, base_file, style_sheet=None):
    self.base_file = base_file
    self.base_pdf = PdfFileReader(self.base_file, "rb")
    self.overlays = {}
    self.style_sheet = style_sheet if style_sheet is not None else getSampleStyleSheet()
    self.style_count = 0

  def get_page_size(self, page):
    # https://stackoverflow.com/questions/46232984/how-to-get-pdf-file-metadata-page-size-using-python
    p = self.base_pdf.getPage(page)
    w_in_user_space_units = p.mediaBox.getWidth()
    h_in_user_space_units = p.mediaBox.getHeight()

    w = float(p.mediaBox.getWidth()) * 25.4/72
    h = float(p.mediaBox.getHeight()) * 25.4/72
    return (w, h)

  def get_page(self, page):
    if page not in self.overlays:
      packet = io.BytesIO()
      self.overlays[page] = {
          "canvas": canvas.Canvas(packet, pagesize=self.get_page_size(page)),
          "packet": packet
      }
    return self.overlays[page]

  def get_canvas(self, page):
    return self.get_page(page)["canvas"]
  
  def get_packet(self, page):
    return self.get_page(page)["packet"]

  def apply_style(self, canvas, style):
    base_style = {
        "fontName": self.style_sheet["Normal"].fontName,
        "fontSize": self.style_sheet["Normal"].fontSize,
        "textColor": self.style_sheet["Normal"].textColor
    }
    for k in style:
      if k in style and style[k] is not None:
        base_style[k] = style[k]
    if base_style["fontName"] is not None:
      canvas.setFont(base_style["fontName"], base_style["fontSize"])
    if base_style["textColor"] is not None:
      canvas.setFillColor(base_style["textColor"])
  
  def add_text(self, x, y, text, page=0, **style):
    canvas = self.get_canvas(page)
    canvas.saveState()
    self.apply_style(canvas, style)
    canvas.drawString(x, y, text)
    canvas.restoreState()

  def add_para(self, x0, y0, x1, y1, text, page=0, **style):
    # See chap 5 of https://www.reportlab.com/docs/reportlab-userguide.pdf
    if style != None and style != {}:
      para_style = ParagraphStyle(f'parastyle{self.style_count}', parent = self.style_sheet["Normal"], **style)
      self.style_count += 1
    else:
      para_style = self.style_sheet["Normal"]
    p = Paragraph(text, para_style)
    p.wrap(x1 - x0, y0 - y1)
    canvas = self.get_canvas(page)
    p.drawOn(canvas, x0, y0)

  def save(self, output_file):
    packet = io.BytesIO()
    output = PdfFileWriter()
    for page in range(self.base_pdf.getNumPages()):
      pdfpage = self.base_pdf.getPage(page)
      if page in self.overlays:
        self.get_canvas(page).save()
        pdfpage.mergePage(PdfFileReader(self.get_packet(page)).getPage(0))
      output.addPage(pdfpage)
  
    # finally, write "output" to a real file
    outputStream = open(output_file, "wb")
    output.write(outputStream)
    outputStream.close()