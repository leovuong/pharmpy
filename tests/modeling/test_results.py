from io import StringIO

import numpy as np
import pandas as pd
import pytest

from pharmpy import Model
from pharmpy.modeling import (
    calculate_individual_parameter_statistics,
    calculate_pk_parameters_statistics,
)


def test_calculate_individual_parameter_statistics(testdata):
    model = Model(testdata / 'nonmem' / 'secondary_parameters' / 'pheno.mod')
    rng = np.random.default_rng(103)
    stats = calculate_individual_parameter_statistics(model, 'CL/V', seed=rng)

    assert stats['mean'][0] == pytest.approx(0.004700589484324183)
    assert stats['variance'][0] == pytest.approx(8.086653508585209e-06)
    assert stats['stderr'][0] == pytest.approx(0.0035089729730046304, abs=1e-6)

    model = Model(testdata / 'nonmem' / 'secondary_parameters' / 'run1.mod')
    rng = np.random.default_rng(5678)
    stats = calculate_individual_parameter_statistics(model, 'CL/V', seed=rng)
    assert stats['mean'][0] == pytest.approx(0.0049100899539843)
    assert stats['variance'][0] == pytest.approx(7.391076132098555e-07)
    assert stats['stderr'][0] == pytest.approx(0.0009425952783595735, abs=1e-6)

    covmodel = Model(testdata / 'nonmem' / 'secondary_parameters' / 'run2.mod')
    rng = np.random.default_rng(8976)
    stats = calculate_individual_parameter_statistics(covmodel, 'K = CL/V', seed=rng)
    assert stats['mean']['K', 'median'] == pytest.approx(0.004525842355027405)
    assert stats['variance']['K', 'median'] == pytest.approx(2.9540381716908423e-06)
    assert stats['stderr']['K', 'median'] == pytest.approx(0.001804371451706786, abs=1e-6)
    assert stats['mean']['K', 'p5'] == pytest.approx(0.0033049497924269385)
    assert stats['variance']['K', 'p5'] == pytest.approx(1.5730213328583985e-06)
    assert stats['stderr']['K', 'p5'] == pytest.approx(0.0013102577338191103, abs=1e-6)
    assert stats['mean']['K', 'p95'] == pytest.approx(0.014625434302866478)
    assert stats['variance']['K', 'p95'] == pytest.approx(3.090546438695198e-05)
    assert stats['stderr']['K', 'p95'] == pytest.approx(0.0069971678916412716, abs=1e-6)


def test_calculate_pk_parameters_statistics(testdata):
    model = Model(testdata / 'nonmem' / 'models' / 'mox1.mod')
    rng = np.random.default_rng(103)
    df = calculate_pk_parameters_statistics(model, seed=rng)
    assert df['mean'].loc['t_max', 'median'] == pytest.approx(1.5999856886869577)
    assert df['variance'].loc['t_max', 'median'] == pytest.approx(0.29728565293669557)
    assert df['stderr'].loc['t_max', 'median'] == pytest.approx(0.589128711884761)
    assert df['mean'].loc['C_max_dose', 'median'] == pytest.approx(0.6306393134647171)
    assert df['variance'].loc['C_max_dose', 'median'] == pytest.approx(0.012194951111832641)
    assert df['stderr'].loc['C_max_dose', 'median'] == pytest.approx(0.11328030491204867)


def test_calc_pk_two_comp_bolus(testdata):
    # Warning: These results are based on a manually modified cov-matrix
    # Results are not verified
    model = Model(testdata / 'nonmem' / 'models' / 'mox_2comp.mod')
    rng = np.random.default_rng(103)
    df = calculate_pk_parameters_statistics(model, seed=rng)
    # FIXME: Why doesn't random state handle this difference in stderr?
    df.drop('stderr', inplace=True, axis=1)

    correct = """parameter,covariates,mean,variance,stderr
A,median,0.003785,0.0,0.052979
B,median,0.996215,0.0,0.051654
alpha,median,0.109317,0.000037,0.940936
beta,median,24.27695,2.660843,24.759415
k_e,median,13.319584,2.67527,2.633615
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['parameter', 'covariates'], inplace=True)
    correct.drop('stderr', inplace=True, axis=1)
    #pd.testing.assert_frame_equal(df, correct, atol=1e-4)
