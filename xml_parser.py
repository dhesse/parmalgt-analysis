r"""
:mod:`xml_parser` -- the ``xml`` parser back-end
==================================================
.. module: xml_parser
.. moduleauthor: Dirk Hesse <herr.dirk.hesse@gmail.com>

This module contains the parser back-end, which relies on a ``sax``
parser. The general idea is that we construct a python object
corresponding to each tag encountered during the parse. In the end, we
effectively convert the ``xml`` to a tree of python objects.

Quick ``xml`` overview.
=========================

- Each input file *must* contain one <analysis> tag.

  * Each analysis contains one or more <directory> tags. They specify
    directories where measured data resides. If there are more than
    one data files in a directory, they are considered to be
    replica. Each <directory> tag contains

    - A <path> tag where the path to the data files is given.
  
    - A <tauval> tag that contains the value for the integrator step size
      :math:`\tau_g`.

    - A <Lval> tag that contains the lattice size :math:`L/a`.

    - A <ntherm> tag that contains the number of measurements per
      replicum that should be omitted to account for thermalization.

    - A <max_order> tag that specifies the perturbative order.

    - A <normalization> tag that specifies a normalization factor (can
      be omitted).

    - A <swap_endian> tag that tells the code to swap the endianness
      of the input data.

    - A <complex_tag> that tells the code that the input data is
      complex (only the real part will be used, tough).

    - A <label> tag that will label the data in the analysis (can be
      omitted).

  * Each analysis may contain one or more <action> tags. At the
    moment, there are three actions defined:

      - <show> Just prints out the mean values, estimated
        autocorrelation time and the estimated errors thereof.

      - <extrapolate> extrapolates the data linearly to zero
        integration step size.

      - <therm> plots the mean value an estimated error vs. the
        thermalization cut-off to allow the user to estimate the time
        the simulation needs to thermalize.


Minimalist example
=======================

The following example shows the parser at work::

  >>> f = open("dummy", "w")
  >>> xml = '''
  ... <analysis>
  ...   <directory>
  ...     <label>t.005</label>
  ...     <path>example/data.005</path>
  ...     <tauval>.005</tauval>
  ...     <Lval>8</Lval>
  ...     <ntherm>10</ntherm>
  ...     <max_order>5</max_order>
  ...     <normalization>0.053058750062</normalization>
  ...     <swap_endian/>
  ...     <complex/>
  ...   </directory>
  ...   <actions>
  ...     <show orders="2 4"/>
  ...   </actions>
  ... </analysis>
  ... '''
  >>> f.write(xml)
  >>> f.close()
  >>> from parser import parse_file
  >>> analysis = parse_file("dummy")
  >>> analysis.directories[0].path
  u'example/data.005'
  >>> analysis.directories[0].normalization
  0.053058750062
  >>> analysis.directories[0].L
  8
  >>> analysis.actions[0].function
  'show'

Don't forget to check out the examples in the sub-directory
``example`` of the source tree.
"""
import xml.sax.handler
import os
import fnmatch
import copy
import sys

def create_element(name, parent, attrs):
    """Create an element of the process.  This is done by
    instantiating the object with corresponding name. This means, to
    make ``jekyll`` understand the tag <my-tag>, it is enough to
    define the class My-tag (note capitalization) in this namespace
    and have it inherit from Node to add some convenience functions.

    :param name: Name of the tag encountered. Should match the name of
                 the object to be created.
    :type name: str.

    :param parent: The parent object (usually derived from
                   :class:`Node`).
    :type parent:  Class
    """
    name = name.lower().capitalize() # get the capitalization right
    try:
        tmp = eval(name)(attrs)
    except NameError as e:
        print "Encountered undefined tag '{}'.".format(name.upper())
        sys.exit()
    tmp.parent = parent
    return tmp

class Root(xml.sax.handler.ContentHandler):
    """Root code element."""
    def __init__(self, xml_filename):
        self.current = self
        self.project = None
        self.xml_filename = xml_filename
        self.children = []
        self.parent = None
    def startElement(self, name, attrs):
        """Create an elemt with name corresponding to the tag
        name. Ignores attributes"""
        old = self.current
        self.current = create_element(name, self.current, attrs)
        old.children.append(self.current)
    def endElement(self, name):
        """Call finalize on current element and reset the current to
        the previous parent."""
        self.current.finalize()
        self.current = self.current.parent
    def characters(self, data):
        """Pass on the characters."""
        self.current.characters(data)

def tagname(cls):
    return cls.__class__.__name__.lower()

class Node(object):
    """Base class for all tags.  This is used to make handling parent
    nodes etc. somewhat easier. **Make any class you define for your
    own tags inherit from this one**! This will guarantee that your
    class will know its parent tag and the parent process. For
    example, you can implement you own ``xml`` tag that communicates
    with the process that it is associated with like that::

      class foo(Node):
        # make parent aware of its foo
        def __init__(self):
          self.get_process().foo = self
        # do nothing when the tag is closed
        def finalize(self):
          pass

    Furthermore, any object derived from Node will know the text found
    between the opening and the closing tag in its ``buffer``
    member. To access it, you would proceed like this::

      class bar(Node):
        # tell parent to which bar to go
        def finalize(self):
          self.parent.bar = self.buffer

    Given an ``xml`` document structure like 
    
    .. code-block:: xml

      <foo>
        <!-- ... grab Liz, go to the Winchester, have a nice cold
        pint, and wait for all of this to blow over ... -->
        <bar>The Winchester</bar>
      </foo>
      
    The parser will create a ``foo`` instance with ``foo.bar``
    containing the string "The Winchester".
    """
    parent_tags = []
    allowed_values = []
    def __new__(cls, *args, **kwargs):
        """Use a custom __new__ here to avoid trouble when a class
        that inherits from Node defines its own __init__. In that case,
        some of Node's methods like characters could run into trouble
        because some of the members like characters might not be
        defined."""
        try:
            obj = object.__new__(cls, *args, **kwargs)
        except TypeError:
            obj = object.__new__(cls)
        obj.buffer = ""
        obj.parent = None
        obj.children = []
        obj.opts = {}
        return obj
    def characters(self, data):
        """Default characters method, just buffer them. This is what
        lets you access the text between the enclosing tags in
        `self.buffer` of any derived object's instance.

        :param data: Characters to append.
        :type data: str.
        """
        self.buffer += data
    
class Analysis(Node):
    def __init__(self, attrs):
        self.directories = []
        self.actions = []
    def finalize(self):
        self.parent.run = self

    def add_to_abs_file(self, ext):
        return self.work_directory + "/" + self.filename + "." + ext

    def info(self):
        h =  " Analysis info "
        s = "="*((60 - len(h))/2)
        print s + h + s
        print "* Directories:"
        print "   " + "*"*50
        for d in self.directories:
            print "      Label:", d.label
            print "       Path:", d.path
            print "        Tau:", d.tauval
            print "          L:", d.L
            print "     endian: " + ("swap" if d.se else "keep")
            print "  data type: " + "complex" if d.complex else "double"
            print "      therm:", d.ntherm
            print "      order:", d.order
            print "   " + "*"*50
        print "* Actions:"
        for a in self.actions:
            print a
        print "="*60

    def add_directory(self, dir):
        self.directories.append(dir)

class Max_order(Node):
    def finalize(self):
        self.parent.order = int(self.buffer.strip())

class Directory(Node):
    """Directory to read data from."""
    def __init__(self, attrs):
        #: Path.
        self.path = ""
        #: Switch endianness?
        self.se = False
        #: Integration step size.
        self.tauval = 0.0
        self.label = False
        #: Complex data?
        self.complex = False
        #: Normalization.
        self.normalization = 1.0
        #: Filter for file names.
        self.fn_contains = ""
    def finalize(self):
        if not self.label:
            self.label = self.path
        self.parent.add_directory(self)

class Label(Node):
    def finalize(self):
        self.parent.label = self.buffer.strip()

class Path(Node):
    def finalize(self):
        self.parent.path = self.buffer.strip()
        
class Tauval(Node):
    def finalize(self):
        self.parent.tauval = float(self.buffer.strip())

class Lval(Node):
    def finalize(self):
        self.parent.L = int(self.buffer.strip())

class Swap_endian(Node):
    def finalize(self):
        self.parent.se = True

class Complex(Node):
    def finalize(self):
        self.parent.complex = True

class Ntherm(Node):
    def finalize(self):
        self.parent.ntherm = int(self.buffer.strip())

class Normalization(Node):
    def finalize(self):
        self.parent.normalization = float(self.buffer.strip())

class Filenamecontains(Node):
    def finalize(self):
        self.parent.fn_contains = self.buffer.strip()

class Actions(Node):
    def __init__(self, attrs):
        self.actions = []
    def finalize(self):
        self.parent.actions = self.actions

class Show(Node):
    def __init__(self, attrs):
        # orders (for info string and attributes for function call)
        self.orders = [int(i) for i in attrs.get('orders').split()]
        # function rom actions.py to call
        self.function = "show"
        # arguments for call
        self.kwargs = {'orders' : self.orders}
    def __str__(self):
        return "  --> show\n      orders = " \
            + ", ".join(str(i) for i in self.orders)
    def finalize(self):
        self.parent.actions.append(self)

class Extrapolate(Node):
    def __init__(self, attrs):
        # orders (for info string and attributes for function call)
        self.orders = [int(i) for i in attrs.get('orders').split()]
        if attrs.get('L'):
            self.L = [int(i) for i in attrs.get('L').split()]
        else:
            self.L = None
        self.plots = []
        # function from actions.py to call
        self.function = "extrapolate"
    def __str__(self):
        return "  --> extrapolate (tau -> 0)\n      orders = " \
            + ", ".join(str(i) for i in self.orders)
    def finalize(self):
        # arguments for call
        self.kwargs = {'orders' : self.orders,
                       'L_sizes' : self.L,
                       'mk_plots' : self.plots}
        self.parent.actions.append(self)

class Plot(Node):
    def __init__(self, attrs):
        self.data = []
        self.cl = []
        self.fit = []
        self.labels = []
        self.L = [int(i) for i in attrs.get('L').split()]
        self.orders = [int(i) for i in attrs.get('orders').split()]
        self.pdfname = attrs.get('pdfname')
        if attrs.get('known'):
            self.known = [float(i) for i in attrs.get('known').split()]
        else:
            self.known = []
        self.ylabel = attrs.get("ylabel") if attrs.get("ylabel") else ""
    def finalize(self):
        self.parent.plots.append(self)

class Therm(Node):
    def __init__(self, attrs):
        self.orders = [int(i) for i in attrs.get('orders').split()]
        self.start, self.end, self.step = \
            [int(i) for i in attrs.get('range').split()]
        self.function = "therm"
    def __str__(self):
        return ("  --> check thermalization effects\n"
                "      cut-off from {0} to {1} in steps of {2}\n")\
                .format(self.start, self.end, self.step)
    def finalize(self):
        self.kwargs = {'orders' : self.orders,
                       'cutoffs' : range(self.start, self.end,
                                         self.step)}
        self.parent.actions.append(self)

def parse_file(f):
    """Parse an entire ``xml`` file.

    :param name: Name of the ``xml`` file to parse.
    :name type: str.
    :returns: The :class:`Project` object resulting from the parse.
    """
    # Create the handler
    handler = Root(f)
    parser = xml.sax.make_parser()
    # Parse the input
    parser.setContentHandler(handler)
    parser.parse(f)
    return handler.run

