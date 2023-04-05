import pytest

from pharmpy.deps import numpy as np
from pharmpy.model.model import update_datainfo
from pharmpy.modeling.blq import transform_blq
from pharmpy.modeling.error import set_additive_error_model, set_combined_error_model, set_proportional_error_model


@pytest.mark.parametrize(
    'method, error_func, sd_ref, y_ref',
    [
        (
            'm4',
            set_additive_error_model,
            ('ADD = SQRT(SIGMA(1,1))', 'SD = SQRT(ADD**2)'),
            ('Y = F + EPS(1)', 'Y = (CUMD - CUMDZ)/(1 - CUMDZ)'),
        ),
        (
            'm4',
            set_proportional_error_model,
            ('PROP = F*SQRT(SIGMA(1,1))', 'SD = SQRT(PROP**2)'),
            ('Y = F + EPS(1)*F', 'Y = (CUMD - CUMDZ)/(1 - CUMDZ)'),
        ),
    ],
)
def test_transform_blq(load_model_for_test, testdata, method, error_func, sd_ref, y_ref):
    model = load_model_for_test(testdata / 'nonmem' / 'pheno.mod')
    model = error_func(model)

    model = transform_blq(model, 0.1)

    assert all(statement in model.model_code for statement in sd_ref)
    assert all(statement in model.model_code for statement in y_ref)


def test_transform_blq_different_lloq(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'pheno.mod')
    model_float = transform_blq(model, 0.1)

    assert 'DV.GE.LLOQ' in model_float.model_code

    df_blq = model.dataset
    df_blq['BLQ'] = np.random.randint(0, 2, df_blq.shape[0])
    di_blq = update_datainfo(model.datainfo, df_blq)
    blq_col = di_blq['BLQ'].replace(type='blq')
    di_blq = di_blq.set_column(blq_col)
    model_blq_col = model.replace(dataset=df_blq, datainfo=di_blq)

    model_blq_col = transform_blq(model_blq_col)

    assert 'BLQ.EQ.1' in model_blq_col.model_code

    df_lloq = model.dataset
    df_lloq['LLOQ'] = np.random.random(df_lloq.shape[0])
    di_lloq = update_datainfo(model.datainfo, df_lloq)
    lloq_col = di_lloq['LLOQ'].replace(type='lloq')
    di_lloq = di_lloq.set_column(lloq_col)
    model_lloq = model.replace(dataset=df_lloq, datainfo=di_lloq)

    model_lloq_col = transform_blq(model_lloq)

    assert 'DV.GE.LLOQ' in model_lloq_col.model_code
    assert 'LLOQ = ' not in model_lloq_col.model_code
