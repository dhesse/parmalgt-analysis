import xml.sax.handler
import os
import fnmatch
import copy
import sys

def create_element(name, parent, attrs):
    """!Cerate an element of the process.

    This is done by instanciating the object w/ corresponding
    name. This means, to make PY-PASTOR understand the tag <my-tag>,
    it is enough to define the class My-tag (note capitalization) in
    this namespace and have it inherit from Node to add some
    convenience functions."""
    name = name.lower().capitalize() # get the capitalization right
    try:
        tmp = eval(name)(attrs)
    except NameError as e:
        print "Encountered undefined tag '{}'.".format(name.upper())
        sys.exit()
    tmp.parent = parent
    return tmp

class Root(xml.sax.handler.ContentHandler):
    """!Root code element."""
    def __init__(self, xml_filename):
        self.current = self
        self.project = None
        self.xml_filename = xml_filename
        self.children = []
        self.parent = None
    def startElement(self, name, attrs):
        """!Create an elemt with name corresponding to the tag
        name. Ignores attributes"""
        old = self.current
        self.current = create_element(name, self.current, attrs)
        old.children.append(self.current)
    def endElement(self, name):
        """!Call finalize on current element and reset the current to
        the previous parent."""
        self.current.finalize()
        self.current = self.current.parent
    def characters(self, data):
        """!Pass on the characters."""
        self.current.characters(data)

def tagname(cls):
    return cls.__class__.__name__.lower()

class Node(object):
    """!Base class for all tags.

    This is used to make handling parent nodes etc. somewhat
    easier. MAKE ANY CLASS YOU DEFINE FOR YOUR OWN TAGS INHERIT FROM
    THIS!!!
    """
    parent_tags = []
    allowed_values = []
    def __new__(cls, *args, **kwargs):
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
        """!Default characters method, just buffer them."""
        self.buffer += data
    def xml(self):
        if self.children:
            inner = "".join(c.xml() for c in self.children)
        else:
            inner = self.buffer.strip()
        return "<{0}>{1}</{0}>".format(tagname(self),
                                       inner)
    def split(self, name):
        for ch in range(len(self.children)):
            for new_ch in self.children[ch].split(name):
                new = copy.copy(self)
                new.children[ch] = new_ch
                yield new
    def has_parent(self, test):
        cand = self
        while cand.parent:
            try:
                if test(cand.parent):
                    return True
            except AttributeError:
                pass
            cand = cand.parent
    
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
    def __init__(self, attrs):
        self.path = ""
        self.se = False
        self.tauval = 0.0
        self.label = False
        self.complex = False
        self.normalization = 1.0
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
    # Create the handler
    handler = Root(f)
    parser = xml.sax.make_parser()
    # Parse the input
    parser.setContentHandler(handler)
    parser.parse(f)
    return handler.run
