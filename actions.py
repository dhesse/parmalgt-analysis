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
    """
    def __init__(self, data_in, fns, delta = None, wij = None):
        """Constructor.

        Parameters:
        data_in (iterable): The input data, in the standard format
        (param, [data]), where param is expected to contain the key
        'L', wich is interpreted as some sort of lattice size, to be
        taken to infinity

        fns (iterable): The functions the data is to be fitted to.

        delta (iterable, optional): The error on the input data.

        wij (iterable, optional): The weights of the data points."""
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

def plot(pdfname, x, y, dy, cl, dcl, ylabel, fit_fn):
    fig = plt.figure()
    pl = fig.add_subplot(111)
    plt.xlim((-.00025,max(x)+.00025))
    pl.set_xlabel("$\\tau_g$")
    pl.set_ylabel(ylabel)
    pl.errorbar(x, y, yerr=dy, fmt = "bs",
                markersize=10)
    pl.errorbar([0.0],[cl],yerr=[dcl], 
                fmt="ro", markersize=10)
    fit_x = np.linspace(0, max(x), 100)
    fit_pts = [fit_fn(x) for x in fit_x]
    plt.plot(fit_x, fit_pts, "r--",c='black', label="fit")
    plt.legend(("data","cl"),'upper left', numpoints=1)
    plt.savefig(pdfname)

def extrapolate(data, arg_dict, f = (lambda x: 1., lambda x: x)):
    for o in arg_dict["orders"]:
        print "  * order g^", o
        x, y, dy = [], [], []
        for label in data:
            print "    **label:", label
            mean, delta, tint, dtint = \
                tauint(data[label].data, o, plots=arg_dict['uwplot'])
            x.append(data[label].tau)
            y.append(mean)
            dy.append(delta)
            print "      mean:", pretty_print(mean, delta)
            print "      tint:", pretty_print(tint, dtint)
        coeffs,errors = extrapolate_cl(f, x,y,dy)
        fit_fn = lambda x : np.sum( c[0,0] * f(x) 
                                    for c,f in zip(coeffs, f))
        mean, sigma = coeffs[0,0], errors[0,0]**0.5
        sxsq = sum(xx**2 for xx in x)
        sx = sum(x)
        sa = np.sqrt(sum( ((sxsq - sx*xx)/(3*sxsq - sx**2))**2*yy**2 
                          for xx, yy in zip(x,dy)))
        assert(abs((sigma - sa)/sa) < 1e-12)
        print
        print "      cl:", pretty_print(mean, sigma)
        if arg_dict["clplot"]:
            ylabel = "$m_1^a$" if o == 2 else "$m_2^a$"
            plot("cl_o{}.pdf".format(o), x, y, dy, 
                 mean, sigma, ylabel, fit_fn) 
