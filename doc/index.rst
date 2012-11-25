.. parmalgt-analysis documentation master file, created by
   sphinx-quickstart on Sun Nov 25 19:12:15 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to parmalgt-analysis's documentation!
=============================================


Prerequisites
=============

You will need to have

* Python
* Scipy and Numpy
* Matplotlib (a Python package)
* The `py-uwerr <https://github.com/dhesse/py-uwerr>`_ package (just
  copy the puwr.py file in this project's main directory.

installed. On my Linux box (Ubuntu 12.12) I ran into some trouble
because I did not have dvipng installed. 

The code can be grabbed directly from `github
<https://github.com/dhesse/parmalgt-analysis>`_, either via ``ssh`` or http:

.. code-block:: bash

  git clone git@github.com:dhesse/parmalgt-analysist  # OR
  git clone https://github.com/dhesse/parmalgt-analysis 

or downloaded as a `.zip archive
<https://github.com/dhesse/parmalgt-analysis/archive/master.zip>`_

Basic usage
===========

With the example files provided, you may do the following to get a
quick idea how to use this script. A detailed description will be
added soon. For now, try this::

  $ ./analyze.py --help

Will give you an overview over the command line arguments. These will
probably change in the future. Now, lets work with the example ``xml``
input provided in the sub-directory ``examples``::

  $ ./analyze.py examples/input_show.py

Will show you some properties of the data stored in
``example/data.005``. The last example provided will take the tau -->
0 limit for the data stored in ``example./data*``::

  $ ./analyze.py examples/input_cl.py

The continuum limit will be taken using the general method described
in [2]_ (to be completely independent of the form of the fit
function), using for now an un-weighted fit. This is because also the
naive error propagation is used to cross-check the resulting error.

Feel free to ask me if anything is unclear/does not work.

.. [1] Ulli Wolff [**ALPHA** Collaboration],
   *Monte Carlo errors with less errors*,
   Comput. Phys. Commun. **156** (2004) 143-153, 
   Erratum-ibid. 176 (2007) 383 ``[hep-lat/0306017]``

.. [2] A. Bode *et al.* [**ALPHA** Collaboration],
  *First results on the running coupling in QCD with two massless
  flavors*,
  Phys. Lett. B **515**, 49 (2001) ``[hep-lat/0105003]``.

.. automodule:: analyze
   :members:

.. automodule:: actions
  :members:

.. automodule:: xml_parser
  :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

