from itertools import product
from typing import Iterable

from pharmpy.model import Model
from pharmpy.modeling import add_indirect_effect

from ..statement.feature.indirect_effect import IndirectEffect
from ..statement.feature.symbols import Name, Wildcard
from ..statement.statement import Statement
from .feature import Feature


def features(model: Model, statements: Iterable[Statement]) -> Iterable[Feature]:
    for statement in statements:
        if isinstance(statement, IndirectEffect):
            modes = (
                [Name('LINEAR'), Name('EMAX'), Name('SIGMOID')]
                if isinstance(statement.modes, Wildcard)
                else statement.modes
            )
            production = (
                [Name('PRODUCTION'), Name('DEGRADATION')]
                if isinstance(statement.production, Wildcard)
                else statement.production
            )

            params = list(product(modes, production))
            params = [(mode.name, production.name) for mode, production in params]

            for param in params:
                if param[1] == 'PRODUCTION':
                    yield ('INDIRECT', *param), add_indirect_effect(model, param[0].lower(), True)
                elif param[1] == 'DEGRADATION':
                    yield ('INDIRECT', *param), add_indirect_effect(model, param[0].lower(), False)
