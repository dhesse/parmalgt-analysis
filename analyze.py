#!/usr/bin/env python
import argparse
import sys
# nasty workaround to enabple pdf plots
if "--clplot" in sys.argv:
    import matplotlib
    matplotlib.use('agg')
from parser import parse_file
import actions
import numpy as np
import os

class Data:
    def __init__(self, d):
        # remember maximum order ...
        self.ord = d.order
        # ... tau value ...
        self.tau = d.tauval
        # ... thermalization cutoff
        self.ncut = d.ntherm
        # determine data type
        dt = np.complex if d.complex else np.float
        files = os.listdir(d.path)
        if d.se:
            raw = [np.fromfile(open(d.path + "/" + f, "rb"), dt)\
                       .byteswap().real[self.ncut*self.ord:]\
                       *d.normalization
                   for f in files]
        else:
            raw = [np.fromfile(open(d.path + "/" + f, "rb"), dt)\
                       .real[self.ncut*self.ord:]\
                       *d.normalization
                   for f in files]
        # number of replica
        self.nrep = len(raw)
        # number of data points / replicum / order
        self.N = raw[0].size / self.ord
        self.data = np.concatenate(raw)\
            .reshape( self.nrep * self.N, self.ord )\
            .transpose().reshape(self.ord, self.nrep, self.N)
            

############################################################
#
#  main 

if __name__ == "__main__":
    # prepare parser for command line arguments
    parser = argparse.ArgumentParser(
        description = "Analysis for parmalgt NSPT data.")
    # input file name
    parser.add_argument('file', type=file, help='input file name')
    # should the script produce plots?
    parser.add_argument('--uwplot', 
                        help=('Make uw_err-style plot. '
                              'This makes sense only if the actions '
                              '"show" or "extrapolate" are used in '
                              'the xml input.'), 
                        action='store_true')
    parser.add_argument('--clplot',
                        help=('Make pdf plot for tau -> 0. '
                              'This makes sense only if the action '
                              '"extrapolate" is used in the xml'
                              'input.'),
                        action='store_true')
    # parse command line arguments
    args = parser.parse_args()
    # parse input file -> analysis object
    an =  parse_file(args.file)
    # print info on analysis object
    an.info()
    # read the data
    data = {}
    for directory in an.directories:
        data[directory.label] = Data(directory)
    for action in an.actions:
        action.kwargs.update(vars(args))
        getattr(actions, action.function)\
            (data, action.kwargs)
