import re 
from abc import ABC, abstractmethod
from dataclasses import dataclass
import yaml
from pdf_filler import PDFFiller

@dataclass
class AbstractField(ABC):
  page: int
  style: dict
  value: str

  @abstractmethod
  def render(self, pdf, style={}):
    pass

@dataclass
class LineField(AbstractField):
  x: float
  y: float

  def render(self, pdf, style={}):
    style = {**style, **self.style}
    pdf.add_text(self.x, self.y, self.value, page=self.page, **style)

@dataclass
class ParaField(AbstractField):
  x0: float
  y0: float
  x1: float
  y1: float

  def render(self, pdf, style={}):
    style = {**style, **self.style}
    pdf.add_para(self.x0, self.y0, self.x1, self.y1, self.value, page=self.page, **style)

class PDFForm:
  def __init__(self, base_file=None, style_sheet=None):
    self.base_file = base_file
    self.style_sheet = style_sheet
    self.style = {}
    self.fields = {}

  def from_yaml(self, yaml_config):
    conf = yaml.load(yaml_config)
    if "BasePDF" in conf:
      self.base_file = conf["BasePDF"]
    if "Style" in conf:
      self.style = {**conf["Style"], **self.style} 
    if "Fields" in conf:
      for f in conf["Fields"]:
        name = f["Name"]
        page = f.get("Page", 0)
        style = f.get("Style", {})
        value = f.get("Value", "")
        if "Rect" in f:
          f = ParaField(page, style, value, f["Rect"][0], f["Rect"][1], f["Rect"][2], f["Rect"][3])
        elif "Point" in f:
          f = LineField(page, style, value, f["Point"][0], f["Point"][1])
        else:
          raise ValueError("Rect or Point must be specified in field")
        self.fields[name] = f 
    return self

  def add_line_field(self, name, x, y, page=0, **style):
    field = LineField(page, style, "", x, y)
    self.fields[name] = field

  def add_para_field(self, name, x0, y0, x1, y1, page=0, **style):
    field = ParaField(page, style, "", x0, y0, x1, y1)
    self.fields[name] = field

  def clear_fields(self):
    for name in self.fields:
      self.fields[name].value = ""      

  def set_field(self, name, value):
    self.fields[name].value = value

  def get_field(self, name): 
    return self.fields[name].value

  def set_values(self, value_dict):
    for name, value in value_dict.items():
      self.set_field(name, value)

  def set_style(self, **style):
    self.style = {**style, **self.style}

  def __getitem__(self, name):
    self.get_field(name)

  def __setitem__(self, name, value):
    self.set_field(name, value)
  
  def generate(self, file_name):
    template = PDFFiller(self.base_file, self.style_sheet)
    for f in self.fields.values():
      f.render(template, style=self.style)
    template.save(file_name)

  def generate_batch(self, values, file_name_pattern):
    for i, val in enumerate(values):
      self.clear_fields()
      template = PDFFiller(self.base_file, self.style_sheet)
      for k, v in val.items():
        self.set_field(k, v)
      for f in self.fields.values():
        f.render(template, style=self.style)
      replacement = {'_i': str(i), **val}
      file_name = re.sub(r'\{(\w+)\}', lambda m: replacement[m[1]], file_name_pattern) 
      template.save(file_name)