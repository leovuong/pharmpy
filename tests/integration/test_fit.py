import shutil

import pytest

import pharmpy.modeling as modeling
from pharmpy.config import site_config_dir, user_config_dir
from pharmpy.internals.fs.cwd import chdir
from pharmpy.model import Model
from pharmpy.plugins.nonmem import conf
from pharmpy.tools import fit


def test_configuration():
    print("User config dir:", user_config_dir())
    print("Site config dir:", site_config_dir())
    print("Default NONMEM path:", conf.default_nonmem_path)
    assert (conf.default_nonmem_path / 'license' / 'nonmem.lic').is_file()


def test_fit_single(tmp_path, model_count, testdata):
    with chdir(tmp_path):
        shutil.copy2(testdata / 'nonmem' / 'pheno.mod', tmp_path)
        shutil.copy2(testdata / 'nonmem' / 'pheno.dta', tmp_path)
        model = Model.create_model('pheno.mod')
        model = model.replace(datainfo=model.datainfo.replace(path=tmp_path / 'pheno.dta'))
        res = fit(model)
        rundir = tmp_path / 'modelfit_dir1'
        assert res.ofv == pytest.approx(730.8947268137308)
        assert rundir.is_dir()
        assert model_count(rundir) == 1
        assert (rundir / 'models' / 'pheno' / '.pharmpy').exists()


def test_fit_multiple(tmp_path, model_count, testdata):
    with chdir(tmp_path):
        shutil.copy2(testdata / 'nonmem' / 'pheno.mod', tmp_path / 'pheno_1.mod')
        shutil.copy2(testdata / 'nonmem' / 'pheno.dta', tmp_path / 'pheno_1.dta')
        model_1 = Model.create_model('pheno_1.mod')
        model_1 = model_1.replace(datainfo=model_1.datainfo.replace(path=tmp_path / 'pheno_1.dta'))
        model_1 = model_1.update_source()
        shutil.copy2(testdata / 'nonmem' / 'pheno.mod', tmp_path / 'pheno_2.mod')
        shutil.copy2(testdata / 'nonmem' / 'pheno.dta', tmp_path / 'pheno_2.dta')
        model_2 = Model.create_model('pheno_2.mod')
        model_2 = model_2.replace(datainfo=model_2.datainfo.replace(path=tmp_path / 'pheno_2.dta'))
        model_2 = model_2.update_source()
        res1, res2 = fit([model_1, model_2])
        rundir = tmp_path / 'modelfit_dir1'
        assert res1.ofv == pytest.approx(730.8947268137308)
        assert res2.ofv == pytest.approx(730.8947268137308)
        assert rundir.is_dir()
        assert model_count(rundir) == 2


def test_fit_copy(tmp_path, model_count, testdata):
    with chdir(tmp_path):
        shutil.copy2(testdata / 'nonmem' / 'pheno.mod', tmp_path / 'pheno.mod')
        shutil.copy2(testdata / 'nonmem' / 'pheno.dta', tmp_path / 'pheno.dta')

        model_1 = Model.create_model('pheno.mod')
        model_1 = model_1.replace(datainfo=model_1.datainfo.replace(path=tmp_path / 'pheno.dta'))
        res1 = fit(model_1)

        rundir_1 = tmp_path / 'modelfit_dir1'
        assert rundir_1.is_dir()
        assert model_count(rundir_1) == 1

        model_2 = model_1.replace(name='pheno_copy')
        model_2 = modeling.update_inits(model_2, res1.parameter_estimates)
        res2 = fit(model_2)

        rundir_2 = tmp_path / 'modelfit_dir1'
        assert rundir_2.is_dir()
        assert model_count(rundir_2) == 1

        assert res1.ofv != res2.ofv


def test_fit_nlmixr(tmp_path, testdata):
    from pharmpy.plugins.nlmixr import conf

    if str(conf.rpath) == '.':
        pytest.skip("No R selected in conf. Skipping nlmixr tests")
    with chdir(tmp_path):
        shutil.copy2(testdata / 'nonmem' / 'pheno.mod', tmp_path)
        shutil.copy2(testdata / 'nonmem' / 'pheno.dta', tmp_path)
        model = Model.create_model('pheno.mod')
        model = model.replace(datainfo=model.datainfo.replace(path=tmp_path / 'pheno.dta'))
        model = modeling.convert_model(model, 'nlmixr')
        res = fit(model, tool='nlmixr')
        assert res.ofv == pytest.approx(732.58737)
        assert res.parameter_estimates['TVCL'] == pytest.approx(0.005863, abs=1e-6)
