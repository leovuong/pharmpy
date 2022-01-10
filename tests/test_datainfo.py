import pytest
import sympy
import sympy.physics.units

from pharmpy.datainfo import ColumnInfo, DataInfo


def test_columninfo_name():
    with pytest.raises(TypeError):
        ColumnInfo(1)


def test_columninfo_type():
    col = ColumnInfo("DUMMY")
    with pytest.raises(TypeError):
        col.type = "notaknowntype"
    col.type = 'id'
    assert col.type == 'id'

    col2 = ColumnInfo("DUMMY", type='dv')
    assert col2.type == 'dv'
    assert col2.continuous


def test_columninfo_scale():
    col = ColumnInfo("DUMMY")
    with pytest.raises(TypeError):
        col.scale = 'notavalidscale'
    col.scale = 'nominal'
    assert col.scale == 'nominal'
    assert not col.continuous


def test_columninfo_unit():
    col = ColumnInfo("DUMMY")
    col.unit = "nospecialunit"
    assert col.unit == sympy.Symbol("nospecialunit")
    col.unit = "kg"
    assert col.unit == sympy.physics.units.kg


def test_columninfo_continuous():
    col = ColumnInfo("DUMMY", scale="nominal")
    with pytest.raises(ValueError):
        col.continuous = True


def test_columninfo_is_numerical():
    col = ColumnInfo("DUMMY", scale='nominal')
    assert not col.is_numerical()
    col = ColumnInfo("DUMMY", scale='ratio')
    assert col.is_numerical()


def test_columninfo_repr():
    col = ColumnInfo("DUMMY", scale='nominal')
    correct = """              DUMMY
type        unknown
scale       nominal
continuous    False
categories     None
unit              1
drop          False"""
    assert repr(col) == correct


def test_id_label():
    di = DataInfo(['ID', 'TIME', 'DV'])
    with pytest.raises(KeyError):
        di.id_label = 'DUMMY'
    di.id_label = 'ID'
    assert di.id_label == 'ID'


def test_dv_label():
    di = DataInfo(['ID', 'TIME', 'DV'])
    with pytest.raises(KeyError):
        di.dv_label = 'DUMMY'
    di.dv_label = 'DV'
    assert di.dv_label == 'DV'


def test_idv_label():
    di = DataInfo(['ID', 'TIME', 'DV'])
    with pytest.raises(KeyError):
        di.idv_label = 'DUMMY'
    di.idv_label = 'TIME'
    assert di.idv_label == 'TIME'


def test_get_set_column_type():
    di = DataInfo(['ID', 'TIME', 'DV'])
    di.set_column_type('ID', 'id')
    with pytest.raises(KeyError):
        di.set_column_type('DUMMY', 'id')
    with pytest.raises(TypeError):
        di.set_column_type('TIME', 'kzarqj')
    assert di.get_column_type('ID') == 'id'


def test_get_column_label():
    di = DataInfo(['ID', 'TIME', 'DV', 'WGT', 'APGR'])
    di.set_column_type('ID', 'id')
    di.set_column_type(['WGT', 'APGR'], 'covariate')
    assert di.get_column_label('id') == 'ID'
    assert di.get_column_labels('covariate') == ['WGT', 'APGR']


def test_unit():
    di = DataInfo(['ID', 'TIME', 'DV', 'WGT', 'APGR'])
    assert di['ID'].unit == 1


def test_scale():
    col = ColumnInfo('WGT', scale='ratio')
    assert col
    with pytest.raises(TypeError):
        ColumnInfo('DUMMY', scale='dummy')


def test_json():
    col1 = ColumnInfo("ID", type='id', scale='nominal')
    col2 = ColumnInfo("TIME", type='idv', scale='ratio', unit="h")
    di = DataInfo([col1, col2])
    correct = '{"columns": [{"name": "ID", "type": "id", "scale": "nominal", "continuous": false, "unit": "1"}, {"name": "TIME", "type": "idv", "scale": "ratio", "continuous": true, "unit": "hour"}]}'  # noqa: E501
    assert di.to_json() == correct

    newdi = DataInfo.from_json(correct)
    assert newdi == di
