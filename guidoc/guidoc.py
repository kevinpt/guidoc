#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright © 2016 Kevin Thibedeau
# (kevin 'period' thibedeau 'at' gmail 'punto' com)
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

'''
This guidoc package provides a way to implement Tkinter widget layouts and
menus. It uses a simple specification language to ease the task of creating
and maintaining Tkinter code.
'''

from __future__ import print_function

import Tkinter as tk

import re
import sys
import string
import types
from datetime import datetime

try:
  import docutils.core
  have_docutils = True
except ImportError:
  have_docutils = False


__version__ = '0.9.2'

class LayoutError(Exception):
  '''Base exception for guisdoc'''
  pass
  
class WidgetError(LayoutError):
  pass

class MenuError(LayoutError):
  pass

class GridError(LayoutError):
  pass

class ParameterError(LayoutError):
  pass


def indent(lines, spaces=0):
  '''Indent a line with leading spaces
  Args:
    lines (Sequence):       Sequence of text lines to indent
    spaces (int, optional): Number of leading spaces to insert
  Yields:
    Each line with indentation prepended
  '''
  for l in lines:
    yield ' '*spaces + l

def parse_indented_list(lines, parse_func, class_name=None):
  '''Parse an indented list of text lines into a tree
  
  The objects returned by the parse_func function must have a list attribute named 'children'
  
  Args:
    lines (Sequence):           Sequence of text lines to parse
    parse_func (callable):      A function object that parses each line and returns a representative object
    class_name (str, optional): Name of class this layout is modifying. Used for better exception messages.
  Returns:
    List of parsed nodes for top level of the tree
  '''
  cur_indent = None
  cur_level = None
  nodes = []
  cur_level = nodes
  stack = [(cur_indent, cur_level)]
  
  for l in lines:
    ls = l.lstrip()
    next_indent = len(l) - len(ls)
    
    n = parse_func(ls.rstrip(), class_name)
    if cur_indent is None or next_indent == cur_indent:
      cur_level.append(n)
      cur_indent = next_indent
    elif next_indent > cur_indent:
      cur_indent = next_indent
      stack.append((cur_indent, cur_level[-1].children))
      cur_level = stack[-1][1]
      cur_level.append(n)
    else:
      while next_indent < cur_indent and len(stack) > 1:
        del stack[-1]
        cur_indent, cur_level = stack[-1]
        if cur_indent is None:
          cur_indent = next_indent
      cur_level.append(n)
      
  return nodes

def find_tkinter_name():
  '''Discover the name the Tkinter module has been imported under
  Returns:
    str: The name of the Tkinter library or None
  '''
  import types

  # Get all global modules pointing to the Tkinter or tkinter package
  m = [k for k,v in globals().iteritems() if type(v) == types.ModuleType and v.__name__ in ('Tkinter', 'tkinter')]

  if len(m) > 0:
    return m[0]
  else:
    return None

def lib_imports(glbls):
  '''Extract all packages from a global namespace

  args:
    glbls (dict): Globals to take packages from
  returns:
    Dictionary of all packages except '__builtins__'
  '''
  lib_names = [n for n, v in glbls.iteritems() if n != '__builtins__' and isinstance(v, types.ModuleType)]
  return {k:glbls[k] for k in lib_names}


def compile_method(code, method_name, libraries={}):
  '''Compile a code string into a code object
  The code must contain a function definition which will be used as a method.
  
  Args:
    code (str):        Python source code to compile
    method_name (str): Name of method defined by the code
    libraries (dict, optional): Dictionary of packages used by the code
  Returns:
    code object: The compiled code object for the method or None
  '''
  glbls = globals().copy()
  glbls.update(libraries) # Make libraries from user code visible to exec
  exec(code, glbls)
  
  if method_name in glbls:
    return glbls[method_name]
  else:
    return None


def parse_params(params, class_name=None):
  '''Parse a string of parameters in Python syntax into a dict
  Args:
    params (str): Python parameter string. Must use named parameters.
    class_name (str, optional): Name of the class the layout is implemented in for debug messages
  Returns:
    dict : The key value pairs extracted from the parameter string
  '''
  
  try:
    terms = [t.strip() for t in params.split(',')]
    d = {}
    for t in terms:
      k,v = [kv.strip() for kv in t.split('=')]
      # Strip quotes from strings
      #if v[0] == v[-1] and v.startswith(('"', "'")):
      #  v = v[1:-1]
      d[k] = v
  except:
    raise ParameterError('Invalid parameters in {}:\n\t{}'.format(class_name, params))

  return d
  
def index_widgets(widgets, index):
  '''Build an index associating WidgetSpec objects by their name
  Args:
    widgets (list): List of widgets to recursively index
    index (dict): Dictionary to put each widget into keyed by its name
  '''
  for w in widgets:
    index[w.name] = w
    index_widgets(w.children, index)
    
def index_containers(widgets, index, parent=None):
  '''Build an index of all widgets that contain children
  Args:
    widgets (list): List of widgets to recursively scan
    index (dict): Dictionary to put widget list into keyed by the parent
    parent (WidgetSpec, optional): Parent widget of the currrent list of widgets
  '''
  index[parent] = widgets
  for w in widgets:
    if len(w.children) > 0:
      index_containers(w.children, index, w)


class Section(object):
  '''Generic sections of the layout specification. Subclasses provide section specific methods
  Args:
    name (str): Name of the section
    param (str): Parameters for this section
  Attributes:
    name (str):        Section name argument
    param (str):       Parameter argument
    lines (list(str)): Raw text lines for this section
  '''
  def __init__(self, name, param=None):
    self.name = name
    self.param = param
    self.lines = []
    
  def parse(self, class_name=None, **kwargs):
    '''Section parser
    
    Implemented in sub-classes
    
    Args:
      class_name (str, optional): Name of class for error messages
    '''
    pass



###########################
######## WIDGETS ##########

class WidgetSpec(object):
  '''Specification of an individual widget
  
  Args:
    name          (str):  Widget instance name
    kind          (str):  Widget object type
    params        (str):  Python parameters for the widget invocation 
    layout_mgr    (str, optional): Layout manager for this widget (defaults to pack)
    layout_params (dict, optional): Paramaters for the layout manager
  Attributes:
    children (list(WidgetSpec)): Child widgets owned by this instance
  '''
  def __init__(self, name, kind, params, layout_mgr=None, layout_params={}):
    self.name = name
    self.kind = kind
    self.params = params
    self.layout_mgr = layout_mgr
    self.layout_params = layout_params
    self.children = []
    
  def code(self, parent, lib_prefix=None):
    '''Generate Python code for widget creation
    Args:
      parent (str): Parent widget for this widget
      lib_prefix (str, optional): Library prefix to prepend to all widget classes
    Yields:
      Sequence of Python code lines for creating this widget
    '''

    full_widget = self.kind    

    # Only prepend lib_prefix if the widget exists in that module

    # Strip any trailing '.' from prefix
    lib_prefix = lib_prefix.rstrip('.')

    # Get module
    if lib_prefix in globals():
      if hasattr(globals()[lib_prefix], full_widget):
        # Attach prefix
        full_widget = '{}.{}'.format(lib_prefix, full_widget)

    # Create the widget
    params = [parent]
    if len(self.params.strip()) > 0:
      params.append(self.params)

    yield 'self.{} = {}({})'.format(self.name, full_widget, ', '.join(params))

    # Configure its layout manager
    layout_mgr = self.layout_mgr if self.layout_mgr else 'pack'
    params = ['{}={}'.format(k, v) for k, v in self.layout_params.iteritems()]
    yield 'self.{}.{}({})'.format(self.name, layout_mgr, ', '.join(params))


# Match a widget spec line
widget_re = re.compile(r'^(\w+)\s*\(\s*([\w.]+)\s*(?:\|\s*(.*))?\)$')
# Match the widget and layout manager params
layout_re = re.compile(r'<\s*(\w+)\s*(?:\|\s*([^>]*))?>$')

class WidgetSection(Section):
  '''Section defining a widget tree. There should only be one per layout
  
  Args:
    name (str):            Section type (Must be 'widgets')
    param (str, optional): Section parameters
  Attributes:
    widgets (list(WidgetSpec)): Parsed widgets for this section
  '''
  def __init__(self, name, param=None):
    self.widgets = []
    Section.__init__(self, name, param)

  @staticmethod  
  def parse_widget_spec(line, class_name):
    '''Callback for recursively parsing indented widget list
    Args:
      line (str):       Widget spec line to parse
      class_name (str): Name of class for error messages
    Returns:
      WidgetSpec: The parsed widget
    '''
    widget_layout_mgr = None
    widget_layout_params = None
    
    # Strip off any layout mgr. params
    m = layout_re.search(line)
    if m:
      widget_layout_mgr = m.group(1)
      widget_layout_params = m.group(2)
      line = line[:m.start()].rstrip() # Remove layout spec from widget line

    m = widget_re.match(line)
    if m:
      widget_name = m.group(1)
      widget_kind = m.group(2)
      widget_params = m.group(3)
      if widget_params is None:
        widget_params = ''
  
      # Parse layout manager params into a dict so that they can be altered later
      if widget_layout_params:
        widget_layout_params = parse_params(widget_layout_params, class_name)
      else:
        widget_layout_params = {}
        
      return WidgetSpec(widget_name, widget_kind, widget_params, widget_layout_mgr, widget_layout_params)
    else:
      raise WidgetError('Invalid syntax in layout for {}:\n\t{}'.format(class_name, line))

  
  def parse(self, class_name=None, **kwargs):
    '''Widget section parser
    
    Parses all widgets into a tree stored at self.widgets
    
    Args:
      class_name (str, optional): Name of class for error messages
    '''
    self.widgets = parse_indented_list(self.lines, WidgetSection.parse_widget_spec, class_name)

  @staticmethod
  def generate_widget_code(widgets, parent=None, lib_prefix=None):
    '''Recursively generate code for widgets
    Args:
      widgets (list(WidgetSpec)): List of sibling widgets at the current level of the tree
      parent (str, optional): Parent widget this level in the tree
      lib_prefix (str, optional): Library prefix to prepend to all widget classes
    Yields:
      Sequence of Python code lines for creating this section
    '''
    for w in widgets:
      # Generate the widget code
      for l in w.code(parent, lib_prefix):
        yield l
        
      # Recurse into any children
      ccode = WidgetSection.generate_widget_code(w.children, 'self.' + w.name, lib_prefix)
      for c in ccode:
        yield c

  def code(self, parent, lib_prefix=None):
    '''Generate Python code for widget section
    Args:
      parent (str): Parent widget for top level widgets
      lib_prefix (str, optional): Library prefix to prepend to all widget classes
    Yields:
      str: Sequence of Python code lines for creating this section
    '''
    
    yield '# Widgets'
    
    for l in WidgetSection.generate_widget_code(self.widgets, parent, lib_prefix):
      yield l



#########################
######## GRIDS ##########

class GridSection(Section):
  '''Section defining a grid layout
  Args:
    name (str):            Section type (Must be 'grid')
    param (str, optional): Section parameter. Identifies container widget this grid is associated with.
  Attributes:
    grid_data (list(GridSpec)): Parsed grid for this section
  '''
  
  def __init__(self, name, param=None):

    self.grid_data = {'_container': param}
    Section.__init__(self, name, param)
    

  def parse(self, class_name=None, **kwargs):
    '''Parse a grid table
    
    This uses the docutils library to convert a table in either the grid or simple
    table formats (http://docutils.sourceforge.net/docs/user/rst/quickref.html#tables)
    
    It extracts the cell coordinates and spanning data for each widget included in the table
    and alters their layout properties to match.
    Args:
      class_name (str, optional): Class name for error messages
      kwargs (dict, optional): Additional keyword arguments. 'require_docutils' can be passed to control grid parsing.
    '''
    
    if 'require_docutils' in kwargs:
      require_docutils = kwargs['require_docutils']
    else:
      require_docutils = False

    # Skip parsing grid section if docutils lib is not available
    if not have_docutils:
      if require_docutils:
        raise GridError('Missing docutils library needed to parse grid sections in {}'.format(class_name))
      else: # Just skip parsing this section
        return
    
    # Use docutils to parse a table in one of two supported formats
    dom = docutils.core.publish_doctree('\n'.join(self.lines)).asdom()
    
    # Get the number of columns
    num_cols = 1
    tgroup = dom.getElementsByTagName('tgroup')
    if len(tgroup) >= 1:
      num_cols = int(tgroup[0].attributes['cols'].value)

    # Iterate over the rows of the table extracting grid parameters
    # from their position in the layout
    table = dom.getElementsByTagName('tbody')
    if len(table) >= 1:
      rows = table[0].getElementsByTagName('row')
      
      num_rows = len(rows)
      
      # Create map of occupied cells
      cell_map = [[False]*num_cols for _ in xrange(num_rows)]
      
      # Each row has a series of <entry> elements that should contain a single <paragraph> element
      for j, r in enumerate(rows):
        col_offset = 0
        entries = r.getElementsByTagName('entry')
        for i,e in enumerate(entries):
          p = e.getElementsByTagName('paragraph')
          if len(p) == 1:
            widget = p[0].firstChild.nodeValue # Get the widget name
            
            # Set initial coordinates for the cell
            cell_row = j
            cell_col = i + col_offset
            cell_width = 1
            cell_height = 1
            
            # Check if the cell origin is already occupied by a row-spanning cell
            if cell_map[cell_row][cell_col]:
              # Move to first unoccupied column
              while cell_map[cell_row][cell_col] and cell_col < num_cols:
                cell_col += 1
                col_offset += 1
              if cell_map[cell_row][cell_col]:
                raise GridError('Cannot find unoccupied cell in row {}'.format(cell_row))

            
            # Save location of this widget
            self.grid_data[widget] = {'row':cell_row, 'column':cell_col}
            
            # Check if this widget spans multiple cells
            if 'morecols' in e.attributes.keys():
              cell_width = int(e.attributes['morecols'].value) + 1
              self.grid_data[widget]['columnspan'] = cell_width
              col_offset += cell_width - 1
              
            if 'morerows' in e.attributes.keys():
              cell_height = int(e.attributes['morerows'].value) + 1
              self.grid_data[widget]['rowspan'] = cell_height
              
            # Mark occupied cells
            for n in xrange(cell_row, cell_row + cell_height):
              for m in xrange(cell_col, cell_col + cell_width):
                cell_map[n][m] = True


#########################
######## MENUS ##########

class MenuSpec(object):
  '''Specification of a menu item
  Args:
    label         (str):  Menu label text. Use '&' to identify underlined characters.
    kind          (str):  Menu object type: One of 'normal', 'separator', 'check', or 'radio'
    params        (str):  Python parameters for the menu  invocation 
  Attributes:
    children (list(MenuSpec)): Child menus owned by this instance
  '''
  def __init__(self, label, kind, params):
    self.kind = kind
    self.params = params
    self.children = []
    
    # Strip quotes from label
    if len(label) > 2 and label[0] == label[-1] and label.startswith(('"', "'")):
      label = label[1:-1]
    
    self.underline = label.find('&')
    
    if self.underline >= 0 and len(label) > 1:
      if self.underline == 0:
        self.label = label[1:]
      else:
        self.label = '{}{}'.format(label[:self.underline], label[self.underline+1:])
    else:
      self.label = label
      
  @property
  def prop_label(self):
    '''Convert label to valid Python identifier '''
    return re.sub(r'[\W]|^(?=\d)', '_', self.label)

    
  def __repr__(self):
    return 'MenuSpec({}, {}, {})'.format(self.label, self.kind, self.params)
    
  def code(self, parent=None, lib_prefix=None):
    '''Generate Python code for menu creation'''
    
    if len(self.children) == 0:
      delim = ', ' if len(self.params.strip()) > 0 else ''
      
      add_method = 'add_command'
      if self.kind == 'check':
        add_method = 'add_checkbutton'
      elif self.kind == 'radio':
        add_method = 'add_radiobutton'

      if self.kind == 'separator':
        yield 'self.{}.add_separator()'.format(parent)
      else:
        new_params = {
          'label': self.label,
        }
        
        if self.underline >= 0:
          new_params['underline'] = self.underline
          
        new_params = ', '.join('{}={}'.format(k, repr(v)) for k, v in new_params.iteritems()) 
        yield 'self.{}.{}({}{}{})'.format(parent, add_method, new_params, delim, self.params)


# Match a menu spec line
menu_re = re.compile('^(\\*|\\[\\])?\\s*([^\\s\'"]+|"[^"]+"|\'[^\']+\')\\s*(.*)')
menu_sep_re = re.compile(r'^----')

class MenuSection(Section):
  '''Section defining a menu tree.'''
  def __init__(self, name, param=None):
    self.items = []
    Section.__init__(self, name, param)
  
  @staticmethod  
  def parse_menu_item(line, class_name):
    params = ''
    kind = 'normal'
    
    if menu_sep_re.match(line):
      return MenuSpec('', 'separator', '')
    
    m = menu_re.match(line)
    if m:
      if m.group(1) == '*':
        kind = 'radio'
      elif m.group(1) == '[]':
        kind = 'check'

      label = m.group(2)
      params = m.group(3)
    else:
      label = line
    
    return MenuSpec(label, kind, params)


  @staticmethod
  def generate_menu_code(items, menu_name, parent=None, lib_prefix=None):
    '''Generate code for a menu'''
    
    # Prepare prefix
    if lib_prefix is None or len(lib_prefix) == 0:
      lib_prefix = ''
    elif lib_prefix[-1] != '.':
      lib_prefix += '.'
    
    next_parent = parent
    for i in items:
      if len(i.children) > 0:
        next_parent = '{}{}'.format(menu_name, i.prop_label)
        yield 'self.{} = {}Menu(self.{}, tearoff=0)'.format(next_parent, lib_prefix, parent)
      else:
        for l in i.code(parent):
          yield l

      ccode = MenuSection.generate_menu_code(i.children, menu_name, next_parent, lib_prefix)
      for c in ccode:
        yield c
        
      if len(i.children) > 0:
        new_params = {
          'label': i.label,
        }
        
        if i.underline >= 0:
          new_params['underline'] = i.underline
          
        new_params = ', '.join('{}={}'.format(k, repr(v)) for k, v in new_params.iteritems()) 

        yield 'self.{}.add_cascade({}, menu=self.{})'.format(parent, new_params, next_parent)
        

    
  def parse(self, class_name=None, **kwargs):
    self.items = parse_indented_list(self.lines, MenuSection.parse_menu_item, class_name)

  def code(self, parent, lib_prefix=None):
    '''Generate code for a menu
    Args:
      parent (str): Parent widget for top level menu objects
      lib_prefix (str, optional): Library prefix for widgets
    Yields:
      str: Sequence of Python code lines for creating this menu
    '''
    # Check if Menu object exists under library prefix
    if (lib_prefix not in globals()) or (not hasattr(globals()[lib_prefix], 'Menu')):
      lib_prefix = ''

    # Prepare prefix
    if lib_prefix is None or len(lib_prefix) == 0:
      lib_prefix = ''
    elif lib_prefix[-1] != '.':
      lib_prefix += '.'

    default_menu = 'menubar'
    menu_name = self.param if self.param else default_menu
    
    yield '# Menu: {}'.format(menu_name)
    
    yield 'self.{} = {}Menu({}, tearoff=0)'.format(menu_name, lib_prefix, parent)
    for l in MenuSection.generate_menu_code(self.items, menu_name, menu_name, lib_prefix):
      yield l

    # Automatically configure menu if it has the default name
    # Any other menu must be manually installed
    if menu_name == default_menu:      
      menu_attach = '''if isinstance(self, {}Toplevel):
  self.config(menu=self.{})
elif isinstance(self.master, {}Tk) or isinstance(self.master, {}Toplevel):
  self.master.config(menu=self.{})'''.format(lib_prefix, menu_name, lib_prefix, lib_prefix, menu_name)
      for l in menu_attach.splitlines():
        yield l



#########################
######### MISC ##########


# Match end of line comments
comment_re = re.compile(r'^(.*)\s*#.*$')

# Match a section heading
section_re = re.compile(r'^\s*\[\s*([^]]+)\s*\]')

def parse_layout_spec(spec, class_name=None, require_docutils=False):
  '''Parse a complete layout spec into sections
  Args:
    spec (str): Layout specification
    class_name (str, optional): Class name for error messages
    require_docutils (bool, optional): Require docutils library when True. Ignore grid sections when False.
  Returns:
    list(Section): List of parsed sections
  '''
  sections = []
  # Start with a widget section by default so that its section heading is optional
  cur_section = WidgetSection('widgets')

  # Break spec into sections
  for l in spec.split('\n'):
    # Strip comments
    m = comment_re.match(l)
    if m:
      l = m.group(1)
      
    l = l.rstrip()
    
    m = section_re.match(l)
    if m:
      # Get section names
      names = [n.strip() for n in m.group(1).split()]
      if len(names) > 0:
        sect_name = names[0].lower()
        sect_param = None
        if len(names) > 1:
          sect_param = names[1]

      # Save previous section
      sections.append(cur_section)
      if sect_name == 'widgets':
        cur_section = WidgetSection(sect_name, sect_param)
      elif sect_name == 'grid':
        cur_section = GridSection(sect_name, sect_param)
      elif sect_name == 'menu':
        cur_section = MenuSection(sect_name, sect_param)
      else:
        cur_section = Section(sect_name, sect_param)
    else:
      # Add line to current section if non-empty
      if l:
        cur_section.lines.append(l)

  # Save last section
  if cur_section:
    sections.append(cur_section)
    
  # Remove empty sections
  for i in xrange(len(sections)-1, -1, -1):
    if len(sections[i].lines) == 0:
      del sections[i]

  # Parse each section
  for s in sections:
    s.parse(class_name, require_docutils=require_docutils)

  return sections


def print_widget_tree(widgets, indent=0):
  '''Dump a parsed widget tree
  Args:
    widgets (list(WidgetSpec)): Tree of WidgetSpec objects
    indent (int, optional): Characters to indent for each level of the tree
  '''
  for w in widgets:
    print('{}{} {}'.format(' '*indent*2, w.name, w.kind))
    if len(w.children) > 0:
      print_widget_tree(w.children, indent+1)

def print_menu_tree(nodes, indent=0):
  '''Dump a parsed menu tree
  Args:
    nodes (list(MenuSpec)): Tree of MenuSpec objects
    indent (int, optional): Characters to indent for each level of the tree
  '''
  for n in nodes:
    print('{}{}'.format(' '*indent*2, n.label))
    if len(n.children) > 0:
      print_menu_tree(n.children, indent+1)


def apply_grid_attributes(grids, widget_sec, class_name=None):
  '''Set cell coordinates extracted from grid sections
  Args:
    grids (list(GridSection)): List of parsed grid sections
    widget_sec (WidgetSection): The widget section to apply grid attributes to
    class_name (str, optional): Class name for error messages
  '''

  # Build an index of the widgets
  index = {}
  index_widgets(widget_sec.widgets, index)

  # Associate grids with their container widget
  gindex = {}
  for g in grids:
    if g.grid_data['_container'] in index:
      gindex[g.grid_data['_container']] = (index[g.grid_data['_container']].children, g.grid_data)
    elif g.grid_data['_container'] is None: # Top level grid
      gindex['<top>'] = (widget_sec.widgets, g.grid_data)
      
  # Set children of gridded containers to use grid layout
  for w, g in gindex.itervalues():
    for c in w:
      if c.layout_mgr is None:
        c.layout_mgr = 'grid'

  # Apply grid parameters from tables
  for w, g in gindex.itervalues():
    for c in w:
      if c.name in g:
        grid_params = g[c.name]
        if c.layout_mgr == 'grid':
          c.layout_params.update(grid_params)
  
  # Set default grid coordinates for remaining widgets
  for w, g in gindex.itervalues():
    max_row = -1
    try:
      max_row = max(int(c.layout_params['row']) for c in w if 'row' in c.layout_params)
    except ValueError: # Raised if list passed to max() is empty
      raise LayoutError('Could not determine number of rows in grid for {}'.format(class_name))

    next_row = max_row + 1
    for c in w:
      if c.layout_mgr == 'grid':
        if 'row' not in c.layout_params:
          c.layout_params['row'] = next_row
          next_row += 1
        if 'column' not in c.layout_params:
          c.layout_params['column'] = 0


def create_layout_method(layout, method_name, parent='self', lib_prefix=None, class_name=None, require_docutils=False):
  '''Create a code string for a method that can be inserted into a widget container class
  Args:
    layout (str):                Layout specification
    method_name (str):           Name for the method to generate
    parent (str, optional):      Parent object for the widgets. Defaults to "self"
    lib_prefix (str, optional):  Library prefix for widgets
    class_name (str, optional):  Class name for error messages
    require_docutils (bool, optional): Require docutils library when True. Ignore grid sections when False.
  Returns:
    str: The generated function declaration that implements the layout specification
  '''

  # Attempt to auto-discover the library prefix
  if lib_prefix is None:
    lib_prefix = find_tkinter_name()

  sections = parse_layout_spec(layout, class_name, require_docutils)
  
  # Get all widgets  and menu sections
  widgets = [s for s in sections if s.name == 'widgets']
  menus = [s for s in sections if s.name == 'menu']
  
  # We can only have 0 or 1 widget section
  # We must have at least 1 menu section if there is no widget section
  # Grid sections are completely optional
  
  if len(widgets) == 0 and len(menus) == 0:
    raise LayoutError('Missing widget or menu section in layout for {}'.format(class_name))
  elif len(widgets) > 1:
    # There can be only one
    raise LayoutError('Multiple widget sections found in layout for {}'.format(class_name))

  method_body = []

  if len(widgets) == 1:  
    widget_sec = widgets[0]
      
    # Find all the grid sections
    grids = [s for s in sections if s.name == 'grid']
    
    # Set grid parameters on widgets
    apply_grid_attributes(grids, widget_sec, class_name)

    # Build an index of widget containers
    containers = {}
    index_containers(widget_sec.widgets, containers)
    
    # Verify container widgets all use the same layout manager
    for container, group in containers.iteritems():
      if len(group) > 0:
        managers = ['pack' if c.layout_mgr is None else c.layout_mgr for c in group]
        unique_managers = set(managers)
        if len(unique_managers) != 1:
          container_name = container.name if container else 'self'
          raise LayoutError('Mismatched layout managers in layout for {}\n\tcontainer "{}" has: {}'.format(class_name,
            container_name, ', '.join(unique_managers)))
        
    # Generate method code
    method_body = list(widget_sec.code(parent, lib_prefix))
  
  # Add menu(s)
  if len(menus) > 0:
    for m in menus:
      method_body.append('')
      method_body.extend(list(m.code(parent, lib_prefix)))

  # Build the complete method source code
  method = '''def {}(self):
  """Tk layout generated by guidoc on {}"""
{}'''.format(method_name, datetime.now(),'\n'.join(indent(method_body, 2)))

  #print(method)
  return method


def tk_layout(layout='', lib_prefix=None, libraries={}, method_name='_build_widgets', layout_file=None, require_docutils=False):
  '''Class decorator to parse a layout spec and add a builder method for the layout
  Args:
    layout (str, optional): Layout specification
    lib_prefix (str, optional): Python library prefix for all Tk widgets
    libraries (dict, optional): Dictionary of user packages keyed by name
    method_name (str, optional): The name of the method to add to the class
    file_name (str, optional): File containing layout specification. Only used when layout is empty.
    require_docutils (bool, optional): Require docutils library when True. Ignore grid sections when False.
  '''
  
  if not layout and layout_file:
    try:
      with open(layout_file, 'r') as fh:
        layout = fh.read()
    except IOError:
      pass
  
  # We require either a layout or a valid file_name
  assert layout, 'Missing layout specification'
  
  def layout_tk_class(cls):
    code = create_layout_method(layout, method_name, 'self', lib_prefix, cls.__name__, require_docutils)
    co = compile_method(code, method_name, libraries)
    if co:
      setattr(cls, method_name, co)   # Add method to the class
      setattr(cls, '_guidoc', layout) # Save the original layout

    return cls
    
  return layout_tk_class


def dump_layouts(glbls):
  '''Dump all guidoc layouts found within a namespace
  This writes a file with the contents of the '_guidoc' attribute
  from every object in the glbls dict. This allows you to generate
  static _build_widgets() methods with the guidoc command line mode.

  Args:
    glbls (dict): Dictionary of namespace objects produced by the globals() function.

  Returns:
    list: List of the files written
  '''
  for k in glbls.iterkeys():
    files = []
    if hasattr(glbls[k], '_guidoc'):
      fname = k + '.guidoc'
      with open(fname, 'w') as fh:
        fh.write(glbls[k]._guidoc)
        files.append(fname)
  return files


@tk_layout('''
btnA(Button | text='Button A')
btnB(Button | text='Button B')
chkA(Checkbutton | text='Option A', variable=self.chkAVal) <grid | row=4>
chkB(Checkbutton | text='Option B', variable=self.chkBVal) 
frmChoices(Frame)
  optA(Radiobutton | text='Foo', value='foo', variable=self.radioVal)
  optB(Radiobutton | text='Bar', value='bar', variable=self.radioVal)
  optC(Radiobutton | text='Baz', value='baz', variable=self.radioVal)
lblStatus(Label | padx=5, pady=5, relief='sunken') <grid | padx=3, pady=3, sticky='nsew'>

[grid]

+-----+------+------------+
|btnA | chkA |            |
+-----+------+ frmChoices |
|btnB | chkB |            |
+-----+------+------------+
| lblStatus               |
+-------------------------+

[menu ]

&File
  &Open command=lambda: self.lblStatus.config(text='Open menu')
  &Save command=lambda: self.lblStatus.config(text='Save menu')
  ----
  '&Property settings'
    [] x  variable=self.propXVal, command=lambda: self.lblStatus.config(text='Properties | x menu')
    [] y  variable=self.propYVal, command=lambda: self.lblStatus.config(text='Properties | y menu')
    [] z  variable=self.propZVal, command=lambda: self.lblStatus.config(text='Properties | z menu')
    ----
    *  a  variable=self.propRadioVal, value='a'
    *  b  variable=self.propRadioVal, value='b'
    *  c  variable=self.propRadioVal, value='c'

&Help
  '&About guidoc' command=self.show_about
  
[menu menuCtx]

&Test
  foo
  bar
''')
class GuidocDemoApp(tk.Frame):
  def __init__(self, parent):
    tk.Frame.__init__(self, parent)
    
    parent.title('Guidoc demo')
    self.pack(fill='both', expand=1)
    
    # Any Tk variables referenced in _build_widgets() should be created first
    self.chkAVal = tk.IntVar()
    self.chkBVal = tk.IntVar()
    self.radioVal = tk.StringVar()
    self.radioVal.set('foo')
    
    self.propXVal = tk.BooleanVar()
    self.propXVal.set(True)
    self.propYVal = tk.BooleanVar()
    self.propYVal.set(True)
    self.propZVal = tk.BooleanVar()
    self.propZVal.set(True)
    self.propRadioVal = tk.StringVar()
    self.propRadioVal.set('b')

    # Call our generated layout method
    self._build_widgets()
    
    # Configure callbacks
    self.btnA['command'] = lambda: self.lblStatus.config(text = 'Button A')
    self.btnB['command'] = lambda: self.lblStatus.config(text = 'Button B')
    
    self.chkA['command'] = lambda: self.lblStatus.config(text = 'Option A is {}'.format(self.chkAVal.get()))
    self.chkB['command'] = lambda: self.lblStatus.config(text = 'Option B is {}'.format(self.chkBVal.get()))
    
    # Monitor changes to radio group
    self.radioVal.trace('w', lambda *args: self.lblStatus.config(text = 'Radio choice is {}'.format(self.radioVal.get())))


    #self.menubar.e.entryconfig('Save', state='disabled')
    #self.menubar.component('File').entryconfig('Save', state='disabled')
#    self.menubar.entryconfig(1, state='disabled')
#    self.menubarFile.entryconfig('Save', state='disabled')
#    self.menubarProperty_settings.entryconfig(1, state='disabled')
    for m in dir(self):
      if m.startswith('menu'):
        print('## MENU:', m)

    
  def show_about(self):
    msgbox.showinfo('About', 'This is a guidoc demonstration app')


def guidoc_demo():
  import tkMessageBox as msgbox
  global msgbox

  print('Starting guidoc demonstration...')

  root = tk.Tk()
  app = GuidocDemoApp(root)
  root.mainloop()


def main():
  if len(sys.argv) <= 1:
    # Show demo
    guidoc_demo()

  else: # Act as command line code generator
    # Parse command line args
    import argparse
    
    def usage():
      return """
Dynamic layout in code using a decorator that adds a "_build_widgets" method:
  from guidoc import tk_layout
  
  @tk_layout('''
  <your layout specification>
  ''')
  class MyGui(Frame):
    def __init__(self):
      ...
      self._build_widgets()

Static layout:
  guidoc.py [-h] -i INPUT [-L LIB_PREFIX] [-n METHOD_NAME] [-d]
"""
    
    parser = argparse.ArgumentParser(description='Generate a Tkinter layout method', usage=usage())
    parser.add_argument('-i', '--input', dest='input', action='store', help='Input file. Use - for stdin')
    parser.add_argument('-L', '--lib_prefix', dest='lib_prefix', action='store', help='Library prefix')
    parser.add_argument('-n', '--name', dest='method_name', default='_build_widgets', action='store', help='Name for generated method')
    parser.add_argument('-d', '--docutils', dest='require_docutils', default=False, action='store_true', help='Require the docutils library')
    parser.add_argument('-v', '--version', dest='show_version', default=False, action='store_true', help='Guidoc version')
    args = parser.parse_args()
    
    if args.show_version:
      print('Guidoc v{}'.format(__version__))
      sys.exit(0)
      
    if args.input is None:
      print('Error: argument -i/--input is required')
      sys.exit(1)
    
    # Get layout specification
    if args.input == '-':
      layout = sys.stdin.read()
    else:
      with open(args.input, 'r') as fh:
        layout = fh.read()
        
    class_name = '<stdin>' if args.input == '-' else args.input
      
    # Create method
    code = create_layout_method(layout, args.method_name, 'self', args.lib_prefix, class_name, args.require_docutils)
    print(code)

if __name__ == '__main__':
  main()

