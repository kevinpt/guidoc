.. image:: http://kevinpt.github.io/guidoc/_static/guidoc_icon.png

======
Guidoc
======


Guidoc is a Python package that allows you to create `Tkinter <https://wiki.python.org/moin/TkInter>`_ widget layouts using a simple `docstring specification <https://kevinpt.github.io/guidoc/index.html#guidoc-specification-syntax>`_. It can be used dynamically with docstrings passed to a class decorator or to statically generate a layout method from a specification file. The specification lets you describe a widget hierarchy in a compact form with a simple indented list. This is also used to compactly describe menus. When the docutils package is installed, grid layouts can be described using ASCII tables to visually indicate where widgets are located and how they span rows or columns.

Guidoc saves you from the challenge of writing and managing complex Tkinter layouts as you can easily see the parent-child relationships between widgets and menu items. Grid layouts are easy to modify at a later date without having to decipher the row and column indices.


.. code-block:: python

  import Tkinter as tk
  from guidoc import tk_layout

  @tk_layout(r'''
  btnA(Button | text='Button A')
  btnB(Button | text='Button B')
  btnC(Button | text='Button C\n(spanning two columns)')
  frmX(Frame)
    lbl1(Label | text='Widgets default', bg='red')
    lbl2(Label | text='to using the pack', bg='white')
    lbl3(Label | text='geometry manager', bg='blue', fg='white')

  [grid]    # Grid layout for the top level widgets

  +-----+------+------+
  |btnA | btnB |      |
  +-----+------+ frmX |
  |    btnC    |      |
  +------------+------+
  ''')
  class MyApp(tk.Frame):
    def __init__(self, parent):
      tk.Frame.__init__(self, parent)
      self.pack(fill='both', expand=1)
      self._build_widgets()  # This method is generated by tk_layout()

  root = tk.Tk()
  app = MyApp(root)
  root.mainloop()

This gives rise to the following mockup:

.. image:: http://kevinpt.github.io/guidoc/_images/splash.png
  
What happens here is the ``tk_layout`` decorator parses the Guidoc specification string and inserts the ``_build_widgets()`` method into the ``MyApp`` class. Calling the method in the initialization code adds all of the widget and menu items declared in the specification.

  
The ``guidoc.py`` file functions as a standalone module and can be directly copied into your projects. It also functions as a `command line tool for static code generation <https://kevinpt.github.io/guidoc/index.html#static-generation>`_.

With no command line arguments the ``guidoc.py`` module will launch a demo app:

.. code-block:: sh

  > guidoc

.. image:: http://kevinpt.github.io/guidoc/_images/demo.png


You should be somewhat familiar with Tkinter. Guidoc simplifies some of the labor involved in creating a Tkinter application but you need to know how to write the code that connects the widgets together and makes them useful. This documentation will not teach you how to use Tkinter.



Requirements
------------

Guidoc requires either Python 2.7 or Python 3.x and no additional libraries.
It is recommended that you install the docutils package needed to parse
tabular grid layouts.

The installation script depends on setuptools which will be installed if it
isn't currently present in your Python distribution. The source is written in
Python 2.7 syntax but will convert cleanly to Python 3 when the installer
passes it through 2to3.


Download
--------

You can access the Guidoc Git repository from `Github
<https://github.com/kevinpt/guidoc>`_. You can install direct from PyPI with the "pip"
command if you have it available.


Documentation
-------------

The full documentation is available online at the `main Guidoc site
<http://kevinpt.github.io/guidoc/>`_.

