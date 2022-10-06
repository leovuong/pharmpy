from typing import Iterable

from pharmpy.deps import numpy as np
from pharmpy.deps.scipy import stats
from pharmpy.model import Model


def _ofv(model: Model) -> float:
    return np.nan if model.modelfit_results is None else model.modelfit_results.ofv


def _dofv(parent: Model, model: Model) -> float:
    return _ofv(parent) - _ofv(model)


def degrees_of_freedom(parent: Model, child: Model) -> int:
    return len(child.parameters) - len(parent.parameters)


def cutoff(parent: Model, child: Model, alpha: float) -> float:
    df = degrees_of_freedom(parent, child)
    return (
        0
        if df == 0
        else float(stats.chi2.isf(q=alpha, df=df))
        if df > 0
        else -float(stats.chi2.isf(q=alpha, df=-df))
    )


def p_value(parent: Model, child: Model, parent_ofv, child_ofv) -> float:
    dofv = parent_ofv - child_ofv
    df = degrees_of_freedom(parent, child)
    return float(stats.chi2.sf(x=dofv, df=df))


def test(parent: Model, child: Model, parent_ofv, child_ofv, alpha: float) -> bool:
    dofv = parent_ofv - child_ofv
    return dofv >= cutoff(parent, child, alpha)


def best_of_two(parent: Model, child: Model, alpha: float) -> Model:
    return child if test(parent, child, alpha) else parent


def best_of_many(
    parent: Model, models: Iterable[Model], parent_ofv, model_ofvs, alpha: float
) -> Model:
    best_index = np.argmax(model_ofvs)
    return best_of_two(parent, models[best_index], alpha)
