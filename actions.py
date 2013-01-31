"""
:mod:`actions` -- Methods to perform the data analysis
=======================================================

.. module: actions

In this module, we collect the functions that can be applied to the
data.
"""

from puwr import tauint
from math import log
import numpy as np
from scipy.linalg import svd, diagsvd, norm
import matplotlib.pyplot as plt
plt.rcParams['text.usetex'] = True

def pretty_print(val,err,extra_err_digits = 1):
    if isinstance(val, int):
        return "{0}({1})".format(val, int(err))
    digits = 1 + -int(log(err, 10)) + extra_err_digits
    err = int(err * 10 ** digits + 0.5)
    if err == 10 and extra_err_digits != 1:
        err = 1
        digits -= 1
    return "{0:.{1}f}({2})".format(val, digits, err)

def show(data, arg_dict):
    """Display the mean value, estimated auto-correlaton and error
    thereof."""
    for label in sorted(data.keys()):
        print "* label:", label
        for o in arg_dict["orders"]:
            print "   * order:", o
            mean, delta, tint, dtint = tauint(data[label].data, 
                                              o, plots=arg_dict['uwplot'])
            print "      mean:", pretty_print(mean, delta)
            print "      tint:", pretty_print(tint, dtint)
                                          
class ContinuumLimit(object):
    """Class to estimate continuum limits, as presented in [hep-lat/9911018].
    
    :param data_in: The input data, in the standard format (param,
      [data]), where param is expected to contain the key 'L', wich is
      interpreted as some sort of lattice size, to be taken to
      infinity

    :param fns: The functions the data is to be fitted to.

    :param delta: The error on the input data.

    :param wij: The weights of the data points.
    """

    def __init__(self, data_in, fns, delta = None, wij = None):
        if not wij:
            wij = [1]*len(data_in)
        assert len(wij) == len(data_in)
        self.W = np.mat(np.diag(wij))
        data = {}
        errsq = {}
        for param, [obj] in data_in:
            try:
                data[param['L']] = obj.loop
                errsq[param['L']] = obj.esq
            except AttributeError:
                data[param['L']] = obj
                errsq[param['L']] = 0
        # naive error estimate
        if not delta:
            self.deltasq = np.mat([errsq[L] for L in sorted(errsq)]).transpose()
        else:
            self.deltasq = np.mat([d**2 for d in delta])
        try:
            self.f = np.mat([[f(L) for f in fns] for L in sorted(data)])
        except ValueError as e:
            print "ERROR"
            print "It seems like there are multiple data points for the"
            print "same lattice size L. I don't know what to do with this"
            print "kind of input, so I will abort."
            print "INPUT DATA:"
            print data_in
            sys.exit()
        self.F = np.mat([data[L] for L in sorted(data)]).transpose()
    def estimate(self, Imin):
        """Starting from the Imin-th lattice size, determine the best
        fit parameters. This uses scipy's built-in singual value
        decomposition."""
        M, N = self.f.shape
        assert Imin < M
        M, N = self.f[Imin:, :].shape
        U, s, Vt = svd((self.W*self.f)[Imin:,])
        Sinv = np.mat(diagsvd(1/s, N, M))
        Ut = np.mat(U.transpose())
        V = np.mat(Vt.transpose())
        finv = V * Sinv * Ut
        # check estimate
        alpha = finv * self.W * self.F[Imin:,:]
        # propagate errors
        finvsq = np.mat(np.array(finv)**2)
        delta = finvsq * self.W**2 * self.deltasq[Imin:,:]
        r = norm(self.f[Imin:,:] * alpha - self.F[Imin:,:])
        self.residual = r
        return alpha, delta

class dummy:
    def __init__(self, d, e):
        self.loop = d
        self.esq = e*e

def extrapolate_cl(f, xdata, ydata, yerr):
    data = [({"L": x}, [dummy(y, d)]) 
            for x, y, d in zip(xdata, ydata, yerr)]
    # uncomment the end of the next line (and delte the ")") for a
    # weighted fit 
    cl = ContinuumLimit(data, f)#, wij = [1/x/x for x in yerr])
    return cl.estimate(0)

def mk_plot(plot):
    fig = plt.figure()
    pl = fig.add_subplot(111)
    max_xvals = [max(i[0]) for i in plot.data]
    # give the plot some space
    plt.xlim((-.00025,max(max_xvals)+.00025))
    pl.set_xlabel("$\\tau_g$")
    pl.set_ylabel(plot.ylabel)
    #pl.set_ylabel(ylabel)
    fmts = ["bo", "ro", "go", "yo"]*3
    for (x, y, dy), marker, l in zip(plot.data, fmts,
                                         plot.labels):
        plt.errorbar(x, y, yerr=dy, markersize=10,
                    fmt = marker, label=l)
    pl.legend(loc='upper center', numpoints=1, 
              bbox_to_anchor=(0.5,1.05), ncol=4)
    for (y, dy), marker in zip(plot.cl, fmts):
        plt.errorbar(0, y, yerr=dy, markersize=10,
                    fmt = marker)
    for x, y in plot.fit:
        plt.plot(x, y, "r--", c='black')
    for y in plot.known:
        plt.errorbar( [0], [y], markersize=10, fmt="m^")
    plt.savefig(plot.pdfname)

def therm(data, arg_dict):
    """Estimate thermalization effects, make a plot."""
    for label in sorted(data.keys()):
        print "* label:", label
        for o in arg_dict["orders"]:
            ydata = []
            dydata = []
            print "   * order:", o
            for nc in arg_dict['cutoffs']:
                mean, delta, tint, dtint = \
                    tauint(data[label].data[:,:,nc:], o)
                ydata.append(mean)
                dydata.append(delta)
            plt.errorbar(arg_dict['cutoffs'], ydata, yerr=dydata)
            plt.show()

def extrapolate(data, arg_dict, f = (lambda x: 1., lambda x: x)):
    """Extrapolate data. Optionally make a plot."""
    # check if target lattice sizes are given
    # if not, do the extrapolation for all lattice sizes
    if not arg_dict['L_sizes']:
        arg_dict['L_sizes'] = sorted(set([d.L for d in data.values()]))
    for o in arg_dict["orders"]:
        print "  * order = g^" + str(o)
        x, y, dy, cl, dcl, ffn = [], [], [], [], [], []
        for L in arg_dict['L_sizes']:
            print "    * L =", L
            [i.append([]) for i in x, y, dy]
            for label in data:
                if data[label].L != L:
                    continue
                print "    ** label:", label
                mean, delta, tint, dtint = \
                    tauint(data[label].data, o, plots=arg_dict['uwplot'])
                x[-1].append(data[label].tau)
                y[-1].append(mean)
                dy[-1].append(delta)
                print "      mean:", pretty_print(mean, delta)
                print "      tint:", pretty_print(tint, dtint)
            print "    ** tau -> 0 limit"
            coeffs,errors = extrapolate_cl(f, x[-1], y[-1], dy[-1])
            ffn.append(lambda x : np.sum( c[0,0] * f(x) 
                                          for c,f in zip(coeffs, f)))
            cl.append(coeffs[0,0])
            dcl.append(errors[0,0]**0.5)
            sxsq = sum(xx**2 for xx in x[-1])
            sx = sum(x[-1])
            sa = np.sqrt(sum( ((sxsq - sx*xx)/(3*sxsq - sx**2))**2*yy**2 
                              for xx, yy in zip(x[-1],dy[-1])))
            assert(abs((dcl[-1] - sa)/sa) < 1e-12)
            print "      cl:", pretty_print(cl[-1], dcl[-1])
            print "      " + "*"*50

            for plt in (p for p in arg_dict["mk_plots"]
                        if L in p.L and o in p.orders):
                plt.data.append((x[-1], y[-1], dy[-1]))
                plt.cl.append((cl[-1], dcl[-1]))
                fnx = np.linspace(0, max(x[-1]), 100)
                plt.fit.append((fnx, [ffn[-1](i) for i in fnx]))
                plt.labels.append("$L = {0}$".format(L))
    for plt in arg_dict["mk_plots"]:
        mk_plot(plt)

