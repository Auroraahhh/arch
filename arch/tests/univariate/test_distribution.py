from __future__ import division

from unittest import TestCase

import numpy as np
import pytest
import scipy.stats as stats
from numpy.random import RandomState
from numpy.testing import assert_almost_equal, assert_equal, assert_array_equal
from scipy.special import gammaln, gamma

from arch.univariate.distribution import Normal, StudentsT, SkewStudent, GeneralizedError


class TestDistributions(TestCase):
    @classmethod
    def setup_class(cls):
        cls.rng = RandomState(12345)
        cls.T = 1000
        cls.resids = cls.rng.randn(cls.T)
        cls.sigma2 = 1 + cls.rng.random_sample(cls.resids.shape)

    def test_normal(self):
        dist = Normal()
        ll1 = dist.loglikelihood([], self.resids, self.sigma2)
        scipy_dist = stats.norm
        ll2 = scipy_dist.logpdf(self.resids, scale=np.sqrt(self.sigma2)).sum()
        assert_almost_equal(ll1, ll2)

        assert_equal(dist.num_params, 0)

        bounds = dist.bounds(self.resids)
        assert_equal(len(bounds), 0)

        a, b = dist.constraints()
        assert_equal(len(a), 0)

        assert_array_equal(dist.starting_values(self.resids), np.empty((0,)))

    def test_studentst(self):
        dist = StudentsT()
        v = 4.0
        ll1 = dist.loglikelihood(np.array([v]), self.resids, self.sigma2)
        # Direct calculation of PDF, then log
        constant = np.exp(gammaln(0.5 * (v + 1)) - gammaln(0.5 * v))
        pdf = constant / np.sqrt(np.pi * (v - 2) * self.sigma2)
        pdf *= (1 + self.resids ** 2.0 / (self.sigma2 * (v - 2))) ** (
                -(v + 1) / 2)
        ll2 = np.log(pdf).sum()
        assert_almost_equal(ll1, ll2)

        assert_equal(dist.num_params, 1)

        bounds = dist.bounds(self.resids)
        assert_equal(len(bounds), 1)

        a, b = dist.constraints()
        assert_equal(a.shape, (2, 1))

        k = stats.kurtosis(self.resids, fisher=False)
        sv = max((4.0 * k - 6.0) / (k - 3.0) if k > 3.75 else 12.0, 4.0)
        assert_array_equal(dist.starting_values(self.resids), np.array([sv]))

        with pytest.raises(ValueError):
            dist.simulate(np.array([1.5]))

    def test_skewstudent(self):
        dist = SkewStudent()
        eta, lam = 4.0, .5
        ll1 = dist.loglikelihood(np.array([eta, lam]),
                                 self.resids, self.sigma2)
        # Direct calculation of PDF, then log
        const_c = gamma((eta + 1) / 2) / ((np.pi * (eta - 2)) ** .5 * gamma(eta / 2))
        const_a = 4 * lam * const_c * (eta - 2) / (eta - 1)
        const_b = (1 + 3 * lam ** 2 - const_a ** 2) ** .5

        resids = self.resids / self.sigma2 ** .5
        pow = (-(eta + 1) / 2)
        pdf = const_b * const_c / self.sigma2 ** .5 * \
            (1 + 1 / (eta - 2) *
             ((const_b * resids + const_a) /
              (1 + np.sign(resids + const_a / const_b) * lam)) ** 2) ** pow

        ll2 = np.log(pdf).sum()
        assert_almost_equal(ll1, ll2)

        assert_equal(dist.num_params, 2)

        bounds = dist.bounds(self.resids)
        assert_equal(len(bounds), 2)

        a, b = dist.constraints()
        assert_equal(a.shape, (4, 2))

        k = stats.kurtosis(self.resids, fisher=False)
        sv = max((4.0 * k - 6.0) / (k - 3.0) if k > 3.75 else 12.0, 4.0)
        assert_array_equal(dist.starting_values(self.resids),
                           np.array([sv, 0.]))

        with pytest.raises(ValueError):
            dist.simulate(np.array([1.5, 0.]))
        with pytest.raises(ValueError):
            dist.simulate(np.array([4., 1.5]))
        with pytest.raises(ValueError):
            dist.simulate(np.array([4., -1.5]))
        with pytest.raises(ValueError):
            dist.simulate(np.array([1.5, 1.5]))

    def test_ged(self):
        dist = GeneralizedError()
        nu = 1.7
        ll1 = dist.loglikelihood(np.array([nu]), self.resids, self.sigma2)

        sigma = np.sqrt(self.sigma2)
        x = self.resids

        c = (2 ** (-2 / nu) * gamma(1 / nu) / gamma(3 / nu)) ** 0.5
        pdf = nu / (c * gamma(1 / nu) * 2 ** (1 + 1 / nu) * sigma)
        pdf *= np.exp(-(1 / 2) * np.abs(x / (c * sigma)) ** nu)
        ll2 = np.log(pdf).sum()
        assert_almost_equal(ll1, ll2)
        lls1 = dist.loglikelihood(np.array([nu]), self.resids, self.sigma2, individual=True)
        assert_almost_equal(lls1, np.log(pdf))

        assert_equal(dist.num_params, 1)

        bounds = dist.bounds(self.resids)
        assert_equal(len(bounds), 1)

        a, b = dist.constraints()
        assert_equal(a.shape, (2, 1))

        assert_array_equal(dist.starting_values(self.resids), np.array([1.5]))

        with pytest.raises(ValueError):
            dist.simulate(np.array([0.9]))
        simulator = dist.simulate(1.5)
        rvs = simulator(1000)
        assert rvs.shape[0] == 1000
        assert str(hex(id(dist))) in dist.__repr__()
        assert dist.parameter_names() == ['nu']
