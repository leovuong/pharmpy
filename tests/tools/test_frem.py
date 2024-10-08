import re
import shutil
from io import StringIO

import numpy as np
import pytest
from pytest import approx

import pharmpy.tools as tools
from pharmpy.deps import pandas as pd
from pharmpy.tools import read_modelfit_results
from pharmpy.tools.frem.models import calculate_parcov_inits, create_model3b
from pharmpy.tools.frem.results import (
    calculate_results,
    calculate_results_using_bipp,
    get_params,
    psn_frem_results,
)
from pharmpy.tools.frem.tool import check_covariates
from pharmpy.tools.psn_helpers import create_results


def test_check_covariates(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'pheno_real.mod')
    newcov = check_covariates(model, ['WGT', 'APGR'])
    assert newcov == ['WGT', 'APGR']
    newcov = check_covariates(model, ['APGR', 'WGT'])
    assert newcov == ['APGR', 'WGT']
    data = model.dataset
    data['NEW'] = data['WGT']
    model = model.replace(dataset=data)
    with pytest.warns(UserWarning):
        newcov = check_covariates(model, ['APGR', 'WGT', 'NEW'])
    assert newcov == ['APGR', 'WGT']
    with pytest.warns(UserWarning):
        newcov = check_covariates(model, ['NEW', 'APGR', 'WGT'])
    assert newcov == ['NEW', 'APGR']


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_check_covariates_mult_warns(load_model_for_test, testdata):
    # These are separated because capturing the warnings did not work.
    # Possibly because more than one warning is issued
    model = load_model_for_test(testdata / 'nonmem' / 'pheno_real.mod')
    newcov = check_covariates(model, ['FA1', 'FA2'])
    assert newcov == []


def test_parcov_inits(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    res = read_modelfit_results(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    params = calculate_parcov_inits(model, res.individual_estimates, 2)
    assert params == approx(
        {
            'OMEGA_3_1': 0.02560327,
            'OMEGA_3_2': -0.001618381,
            'OMEGA_4_1': -0.06764814,
            'OMEGA_4_2': 0.02350935,
        }
    )


def test_create_model3b(load_model_for_test, testdata):
    model3 = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    model3_res = read_modelfit_results(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    model1b = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_1b.mod')
    model3b = create_model3b(model1b, model3, model3_res, 2)
    pset = model3b.parameters
    assert pset['OMEGA_3_1'].init == approx(0.02560327)
    assert pset['pCL'].init == 0.00469555
    assert model3b.name == 'model_3b'


def test_bipp_covariance(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    res = read_modelfit_results(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    res = calculate_results_using_bipp(
        model, res, continuous=['APGR', 'WGT'], categorical=[], seed=9532
    )
    assert res


def test_frem_results_pheno(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    res = read_modelfit_results(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    rng = np.random.default_rng(39)
    res = calculate_results(
        model, res, continuous=['APGR', 'WGT'], categorical=[], samples=10, seed=rng
    )

    correct = """parameter,covariate,condition,p5,mean,p95
CL,APGR,5th,0.7796529929324229,0.8867711881110598,1.0237174754763725
CL,APGR,95th,0.9895148609293414,1.062539375981661,1.1255598889265175
CL,WGT,5th,1.0138679164965747,1.069260327455717,1.1227676327855627
CL,WGT,95th,0.7906354024697144,0.8760068835762611,0.9728455252816097
V,APGR,5th,0.9936701106325982,1.0889696510593,1.2119831273167379
V,APGR,95th,0.9127339869907857,0.9622459841559994,1.0030333294681528
V,WGT,5th,0.8946083231694212,0.9298545412018248,0.96839224665385
V,WGT,95th,1.0675663716554031,1.1615592500763623,1.2535787989945573
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1, 2])
    correct.index.set_names(['parameter', 'covariate', 'condition'], inplace=True)
    pd.testing.assert_frame_equal(res.covariate_effects, correct)

    correct = """ID,parameter,observed,p5,p95
1,CL,0.5547432549476109,0.4201938943885976,0.6486041435973237
1,V,1.8160960655979352,1.5159727720524636,2.4087602613533137
2,CL,0.470266113724661,0.336067068070933,0.5827414837908154
2,V,2.2213515152250167,1.6905078909975229,3.175141345673264
3,CL,0.6048549734153286,0.47327609098130746,0.6872756912807287
3,V,1.6399940159772919,1.4314260504151428,2.090579810001594
4,CL,0.5955397044481454,0.4597909738235796,0.6769706266292679
4,V,1.6484353917187287,1.4485017921440297,2.120567010593509
5,CL,0.5547432549476109,0.4201938943885976,0.6486041435973237
5,V,1.8160960655979352,1.5159727720524636,2.4087602613533137
6,CL,0.6527046558639648,0.5229013536890104,0.721249418816454
6,V,1.4860459959674077,1.3583499807791721,1.8317147347643095
7,CL,0.6493365773005624,0.517888019243357,0.7176388267982333
7,V,1.4885912900169234,1.3637971548555514,1.8404416874475509
8,CL,0.5518806756042662,0.4161637323010297,0.6453349952693215
8,V,1.8192066681779755,1.5228573503213898,2.4202088892134292
9,CL,0.5101011580745779,0.37487516057187953,0.6138914952328142
9,V,2.0093873418573915,1.6023634774278785,2.7688014098197904
10,CL,0.5547432549476109,0.4201938943885976,0.6486041435973237
10,V,1.8160960655979352,1.5159727720524636,2.4087602613533137
11,CL,0.5518806756042662,0.4161637323010297,0.6453349952693215
11,V,1.8192066681779755,1.5228573503213898,2.4202088892134292
12,CL,0.6017338005198548,0.46873759361132505,0.6838228568287452
12,V,1.6428029985551513,1.4371244730565678,2.100510294124698
13,CL,0.5986287411393255,0.4642426980858814,0.6803878695977212
13,V,1.645616785415111,1.4427941712663757,2.110505865627533
14,CL,0.5504549350145245,0.41416319983462446,0.643706784382881
14,V,1.8207639613452735,1.5263174977736287,2.4259613043647303
15,CL,0.5533101191078784,0.4181739576274599,0.6469674522485841
15,V,1.817650696000068,1.5194091070094373,2.414475203340811
16,CL,0.46663081967852893,0.33124196481449014,0.5783123081116264
16,V,2.2270610448892993,1.7017260732935522,3.197780869912951
17,CL,0.6510184325366081,0.5203886308484903,0.7194417859880207
17,V,1.4873181029953997,1.3610690197570656,1.8360710928395796
18,CL,0.6493365773005624,0.517888019243357,0.7176388267982333
18,V,1.4885912900169234,1.3637971548555514,1.8404416874475509
19,CL,0.9082662125035582,0.7861474820759035,1.0946056759077873
19,V,0.9932889496846123,0.9730162256733937,1.189888085296149
20,CL,0.6001792682784761,0.4664847312447339,0.6821031453414619
20,V,1.6442092851138022,1.439954589403155,2.1054998945192014
21,CL,0.5605130348474453,0.42837187217101363,0.655193617562414
21,V,1.8098908074994613,1.5023453430494869,2.3860861327756804
22,CL,0.5114223852709964,0.37668630683254006,0.6154497591483878
22,V,2.0076687100771538,1.5987913349463176,2.762255637680207
23,CL,0.8108370290863273,0.7200262531278955,0.8490886116178837
23,V,1.194322088025955,1.1504982328241513,1.331186208680593
24,CL,0.8840823174194126,0.810386432575673,0.947772702344147
24,V,1.0785120776210764,1.0612514583679045,1.177265443145508
25,CL,0.9012449959011728,0.7739072182946907,1.09568057548982
25,V,0.9958420155519944,0.9746675356376356,1.2030039432471393
26,CL,0.4952359358734823,0.35454312768366725,0.6240497561166303
26,V,2.183660209878726,1.5752966849308307,3.029739652904095
27,CL,0.6646311094940178,0.5408339378289935,0.7340343581785044
27,V,1.4771716864501518,1.3395691746399758,1.8016156006728994
28,CL,0.4914075703608971,0.3522056995703855,0.6168451149638602
28,V,2.189272931704994,1.592616156237213,3.050951475768113
29,CL,0.5490328677077555,0.412172285362853,0.642082785395998
29,V,1.8223225985865346,1.5297896426675361,2.431732596280769
30,CL,0.5154066239499925,0.3821724858550786,0.6201489724425161
30,V,2.0025216438845668,1.5881483535909287,2.742746112122217
31,CL,0.5101011580745779,0.37487516057187953,0.6138914952328142
31,V,2.0093873418573915,1.6023634774278785,2.7688014098197904
32,CL,0.4965186439556987,0.35447961444965437,0.6264718071721832
32,V,2.1817925459489342,1.56956567319248,3.0227150147425306
33,CL,0.5140751112218422,0.38033492951246134,0.6185784891089421
33,V,2.0042358599370567,1.591683813610663,2.7492280548747488
34,CL,0.7190679813649745,0.6004405374601173,0.77254660241196
34,V,1.3373616351521445,1.258195602488078,1.5798662905368952
35,CL,0.6750270663834927,0.556694188243534,0.745178366348608
35,V,1.469607339995171,1.3238169127213095,1.7763579665856464
36,CL,0.6577895607808315,0.5305126480009646,0.72670039000237
36,V,1.4822362109972405,1.3502472437513753,1.8187308019831043
37,CL,0.46663081967852893,0.33124196481449014,0.5783123081116264
37,V,2.2270610448892993,1.7017260732935522,3.197780869912951
38,CL,0.5087833516028349,0.37307274645401733,0.6123372944695755
38,V,2.0111074351445737,1.6059479118685898,2.775368559861589
39,CL,0.436919726732037,0.2996572633332399,0.5598296826927744
39,V,2.4493773011969093,1.749902203060225,3.6154457285184174
40,CL,0.7699546293898543,0.6534636410275181,0.8400921045943329
40,V,1.214936790586783,1.1659823007484773,1.407042333617961
41,CL,0.5590649932323148,0.4263125594349446,0.6535398293144995
41,V,1.811440126022407,1.5057345821948098,2.3917269179725764
42,CL,0.4863491978777795,0.34892651702262206,0.6073813086029592
42,V,2.1967788319031087,1.616005190801764,3.0795568972739096
43,CL,0.9059197612239268,0.7820460252089322,1.0949633839795967
43,V,0.9941392395525903,0.9735663427031525,1.194244030896607
44,CL,0.5547432549476109,0.4201938943885976,0.6486041435973237
44,V,1.8160960655979352,1.5159727720524636,2.4087602613533137
45,CL,0.8308651728267631,0.716389304752958,0.9526353599728384
45,V,1.1008893826559083,1.0783462844822813,1.285772417712476
46,CL,0.5061579247643022,0.36949389078045053,0.6092409910953004
46,V,2.014552064617543,1.6131539518528704,2.7885675008383415
47,CL,0.48383948298170665,0.3470192013893334,0.6027093242200596
47,V,2.20054155937321,1.6278287908948514,3.094000302371552
48,CL,0.5009476352770347,0.3624389940059495,0.6030965534006122
48,V,2.0214590457637964,1.6277158380000811,2.8152257630883315
49,CL,0.5087833516028349,0.37307274645401733,0.6123372944695755
49,V,2.0111074351445737,1.6059479118685898,2.775368559861589
50,CL,0.5986287411393255,0.4642426980858814,0.6803878695977212
50,V,1.645616785415111,1.4427941712663757,2.110505865627533
51,CL,0.46302362498267097,0.32648624395467507,0.5739177056914652
51,V,2.2327852537698796,1.7130603574441423,3.2206434370605774
52,CL,0.5476144742265739,0.4101909565648559,0.6404629985762667
52,V,1.8238825700754526,1.5332738053776367,2.437522791163792
53,CL,0.5140751112218422,0.38033492951246134,0.6185784891089421
53,V,2.0042358599370567,1.591683813610663,2.7492280548747488
54,CL,0.5154066239499925,0.3821724858550786,0.6201489724425161
54,V,2.0025216438845668,1.5881483535909287,2.742746112122217
55,CL,0.7079937333419911,0.5833380494168027,0.7629094131325159
55,V,1.3442453042031974,1.2632628782544288,1.6064842812826683
56,CL,0.6988955801007979,0.5694592519524815,0.7577272242611905
56,V,1.3500087586036706,1.2675026633491273,1.6290495232809696
57,CL,0.6143159447902024,0.48715735302638175,0.6977421569066333
57,V,1.631595871114456,1.4119626221409085,2.0611745243868853
58,CL,0.5101011580745779,0.37487516057187953,0.6138914952328142
58,V,2.0093873418573915,1.6023634774278785,2.7688014098197904
59,CL,0.5986287411393255,0.4642426980858814,0.6803878695977212
59,V,1.645616785415111,1.4427941712663757,2.110505865627533
"""
    correct = pd.read_csv(StringIO(correct), dtype={0: 'int32'}, index_col=[0, 1])
    correct.index.set_names(['ID', 'parameter'], inplace=True)
    pd.testing.assert_frame_equal(res.individual_effects, correct)

    correct = """parameter,covariate,sd_observed,sd_5th,sd_95th
CL,none,0.1983559931033091,0.12946065353375166,0.2571110819074169
CL,APGR,0.19362660786608385,0.12480254721683472,0.2435502440034818
CL,WGT,0.19328348109779792,0.09866852139499792,0.2543649419117436
CL,all,0.185099734421644,0.0971482727878702,0.23790495842928758
V,none,0.1610490608479292,0.14504107223375226,0.19394379745548562
V,APGR,0.16104004787758217,0.12462053963880998,0.18510960059209022
V,WGT,0.1468992585960289,0.13810044039392597,0.17122865026045814
V,all,0.14574143997630676,0.11964944422449278,0.16136355952455325
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['parameter', 'covariate'], inplace=True)
    pd.testing.assert_frame_equal(res.unexplained_variability, correct)

    correct = pd.DataFrame(
        {
            'p5': [1.0, 0.7],
            'mean': [6.423729, 1.525424],
            'p95': [9.0, 3.2],
            'stdev': [2.237636, 0.704565],
            'ref': [6.423729, 1.525424],
            'categorical': [False, False],
            'other': [np.nan, np.nan],
        },
        index=['APGR', 'WGT'],
    )
    correct.index.name = 'covariate'
    pd.testing.assert_frame_equal(res.covariate_statistics, correct)


def test_frem_results_pheno_categorical(load_model_for_test, testdata):
    model = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno_cat' / 'model_4.mod')
    res = read_modelfit_results(testdata / 'nonmem' / 'frem' / 'pheno_cat' / 'model_4.mod')
    rng = np.random.default_rng(8978)
    res = calculate_results(
        model, res, continuous=['WGT'], categorical=['APGRX'], samples=10, seed=rng
    )

    correct = """parameter,covariate,condition,p5,mean,p95
CL,WGT,5th,0.8641310291070126,0.9249018170362138,0.9904807012744238
CL,WGT,95th,1.0223489728826207,1.1800849865689271,1.3449587374579082
CL,APGRX,other,1.0162806666597155,1.1224051712526673,1.2970395860372472
V,WGT,5th,0.9634325485986632,1.0093449073624652,1.0602888686355647
V,WGT,95th,0.8884917962843722,0.9846864656610128,1.0785058624188064
V,APGRX,other,0.8688332175262571,0.9250999359338907,0.9855484973972216
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1, 2])
    correct.index.set_names(['parameter', 'covariate', 'condition'], inplace=True)
    pd.testing.assert_frame_equal(res.covariate_effects, correct)

    correct = """ID,parameter,observed,p5,p95
1,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
1,V,1.0011657907076288,0.9956532401541823,1.00779290063149
2,CL,0.9982280031437448,0.9956289893370296,0.9995169404027027
2,V,1.0002361858019588,0.999117351665513,1.0015745372340525
3,CL,0.9982280031437448,0.9956289893370296,0.9995169404027027
3,V,1.0002361858019588,0.999117351665513,1.0015745372340525
4,CL,0.9573077718907862,0.8979325061786043,0.9883610955931397
4,V,1.0058267874330078,0.9785120552034893,1.0394940750546369
5,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
5,V,1.0011657907076288,0.9956532401541823,1.00779290063149
6,CL,1.1198435491217265,1.0050530027804239,1.2399681634311417
6,V,0.9085976422437901,0.864708941115037,0.9900256170661949
7,CL,1.1043277095093798,0.9876067086619895,1.2223617070225354
7,V,0.9102872994311817,0.8587234024197213,0.9956157360488638
8,CL,0.9775538039511688,0.9454965059144583,0.9938806397874291
8,V,1.0030275905796406,0.9887610234986426,1.0203506696993732
9,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
9,V,1.0011657907076288,0.9956532401541823,1.00779290063149
10,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
10,V,1.0011657907076288,0.9956532401541823,1.00779290063149
11,CL,0.9775538039511688,0.9454965059144583,0.9938806397874291
11,V,1.0030275905796406,0.9887610234986426,1.0203506696993732
12,CL,0.984397205662633,0.9619151788582223,0.9957463505068541
12,V,1.0020962549833665,0.9922011584234814,1.0140514963854317
13,CL,0.9707579766809108,0.9293631640229286,0.9920279022735898
13,V,1.0039597917474488,0.9853328182234272,1.0266906485971503
14,CL,0.9707580846524858,0.9293633205582649,0.9920279620535241
14,V,1.0039597398327802,0.9853327819954453,1.0266905646187507
15,CL,0.984397205662633,0.9619151788582223,0.9957463505068541
15,V,1.0020962549833665,0.9922011584234814,1.0140514963854317
16,CL,0.9775538039511688,0.9454965059144583,0.9938806397874291
16,V,1.0030275905796406,0.9887610234986426,1.0203506696993732
17,CL,1.112058541995997,0.9969387463374805,1.2274405589196362
17,V,0.9094420814108903,0.861710963295333,0.9928166100134688
18,CL,1.1043277095093798,0.9876067086619895,1.2223617070225354
18,V,0.9102872994311817,0.8587234024197213,0.9956157360488638
19,CL,1.1043277095093798,0.9876067086619895,1.2223617070225354
19,V,0.9102872994311817,0.8587234024197213,0.9956157360488638
20,CL,0.9775538039511688,0.9454965059144583,0.9938806397874291
20,V,1.0030275905796406,0.9887610234986426,1.0203506696993732
21,CL,1.0193394191110992,1.0052718001357361,1.048471125710801
21,V,0.9974525520566727,0.9831583878012387,1.0095821619717518
22,CL,0.9982280031437448,0.9956289893370296,0.9995169404027027
22,V,1.0002361858019588,0.999117351665513,1.0015745372340525
23,CL,1.278561145560325,1.1275699971795996,1.523192779611293
23,V,0.8927014996056475,0.834650795241219,0.9715994084026611
24,CL,1.2875116337804728,1.1312814275703031,1.5483556963143925
24,V,0.8918726161520479,0.8295240866532907,0.971362691027928
25,CL,1.0814559146197718,0.9511304679550197,1.208556756968732
25,V,0.9128276994620533,0.8498226306012399,1.0040623760324794
26,CL,1.1476875524497763,1.0402125088943983,1.4067791348734346
26,V,0.9818242876491968,0.8852625407867885,1.0709877401664711
27,CL,1.175885957445256,1.052365300951731,1.331722511230272
27,V,0.9027084993825373,0.8859888620382477,0.9758668150806762
28,CL,1.1239176188679145,1.033750177359764,1.3355073831315731
28,V,0.9845643436557832,0.9017698567148642,1.059886168124429
29,CL,0.9640094405028626,0.913510222295993,0.9901880847702433
29,V,1.0048928527141423,0.9819165252494239,1.0330716618290827
30,CL,1.0193394191110992,1.0052718001357361,1.048471125710801
30,V,0.9974525520566727,0.9831583878012387,1.0095821619717518
31,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
31,V,1.0011657907076288,0.9956532401541823,1.00779290063149
32,CL,1.1557218681759203,1.0423956605267668,1.4313866984485024
32,V,0.9809126526774464,0.8798305415063195,1.074713961491109
33,CL,1.0122531534168406,1.003340233042313,1.030547021926794
33,V,0.9983795653196571,0.9892575335089764,1.0060817779658537
34,CL,1.1595936298853569,1.0396217633765041,1.3047638643163955
34,V,0.9043872049318215,0.8798559968837507,0.9775876140846201
35,CL,1.2261492360260002,1.0915540340958125,1.4163600499467606
35,V,0.8976910613647905,0.8661135072712194,0.973167678207756
36,CL,1.1435270215868598,1.0270346055258113,1.2784069421517623
36,V,0.9060690340346341,0.8737655848091472,0.981701336152011
37,CL,0.9775538039511688,0.9454965059144583,0.9938806397874291
37,V,1.0030275905796406,0.9887610234986426,1.0203506696993732
38,CL,0.984397205662633,0.9619151788582223,0.9957463505068541
38,V,1.0020962549833665,0.9922011584234814,1.0140514963854317
39,CL,1.026475342573432,1.0072167581988607,1.0667129298238824
39,V,0.9965263930197235,0.9770984003968382,1.0130947515488598
40,CL,1.112058541995997,0.9969387463374805,1.2274405589196362
40,V,0.9094420814108903,0.861710963295333,0.9928166100134688
41,CL,1.0122531534168406,1.003340233042313,1.030547021926794
41,V,0.9983795653196571,0.9892575335089764,1.0060817779658537
42,CL,1.0929891262425546,1.0253348122823047,1.246159832365342
42,V,0.9882295642803754,0.9242800977385958,1.0452632447666985
43,CL,1.0966505664884518,0.9753301995465317,1.2177225367682787
43,V,0.9111333089443203,0.8557461803338741,0.9984230591697282
44,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
44,V,1.0011657907076288,0.9956532401541823,1.00779290063149
45,CL,1.0890265798617313,0.9632438668673179,1.21312086919932
45,V,0.911980128603927,0.8527791987235807,1.0012386637772648
46,CL,0.9707579766809108,0.9293631640229286,0.9920279022735898
46,V,1.0039597917474488,0.9853328182234272,1.0266906485971503
47,CL,1.0778449935823065,1.021211757953344,1.2037909667247977
47,V,0.990067352893127,0.9357546725680159,1.0380273727070317
48,CL,0.9440437853762491,0.8675835161541562,0.9847453546653573
48,V,1.0076972748297237,0.9717384444551324,1.0524641715242777
49,CL,0.984397205662633,0.9619151788582223,0.9957463505068541
49,V,1.0020962549833665,0.9922011584234814,1.0140514963854317
50,CL,0.9707579766809108,0.9293631640229286,0.9920279022735898
50,V,1.0039597917474488,0.9853328182234272,1.0266906485971503
51,CL,0.9573077718907862,0.8979325061786043,0.9883610955931397
51,V,1.0058267874330078,0.9785120552034893,1.0394940750546369
52,CL,0.9573077718907862,0.8979325061786043,0.9883610955931397
52,V,1.0058267874330078,0.9785120552034893,1.0394940750546369
53,CL,1.0122531534168406,1.003340233042313,1.030547021926794
53,V,0.9983795653196571,0.9892575335089764,1.0060817779658537
54,CL,1.0193394191110992,1.0052718001357361,1.048471125710801
54,V,0.9974525520566727,0.9831583878012387,1.0095821619717518
55,CL,1.112058541995997,0.9969387463374805,1.2274405589196362
55,V,0.9094420814108903,0.861710963295333,0.9928166100134688
56,CL,1.0739378789217238,0.9382357484232393,1.2040297359866272
56,V,0.9136760580307196,0.8468763146466098,1.0068943395657701
57,CL,1.0408973539422075,1.0111470675343617,1.104172126431605
57,V,0.9946766605413693,0.9650950296683103,1.0201566183230069
58,CL,0.9912884661387944,0.9786241977843422,0.9976250876166421
58,V,1.0011657907076288,0.9956532401541823,1.00779290063149
59,CL,0.9707579766809108,0.9293631640229286,0.9920279022735898
59,V,1.0039597917474488,0.9853328182234272,1.0266906485971503
"""

    correct = pd.read_csv(StringIO(correct), dtype={0: 'int32'}, index_col=[0, 1])
    correct.index.set_names(['ID', 'parameter'], inplace=True)
    pd.testing.assert_frame_equal(res.individual_effects, correct)

    correct = """parameter,covariate,sd_observed,sd_5th,sd_95th
CL,none,0.18764141333937986,0.14085450961881152,0.22647803852959827
CL,WGT,0.18248555852725476,0.1264054412422197,0.19585778196189485
CL,APGRX,0.17859851761700796,0.11449651065830042,0.22431033311551907
CL,all,0.17186720148456744,0.10764691725271058,0.19087269979943314
V,none,0.15093077883586237,0.13461538698412528,0.17931305974288728
V,WGT,0.15090452947915597,0.12875168500774023,0.17670652936331083
V,APGRX,0.14429826722004974,0.13031362833636273,0.17139135149890256
V,all,0.14415324601826981,0.12550789602518891,0.1698873910362707
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['parameter', 'covariate'], inplace=True)
    pd.testing.assert_frame_equal(res.unexplained_variability, correct)

    correct = pd.DataFrame(
        {
            'p5': [0.7, 0],
            'mean': [1.525424, 0.711864],
            'p95': [3.2, 1],
            'stdev': [0.704565, 0.456782],
            'ref': [1.525424, 1.0],
            'categorical': [False, True],
            'other': [np.nan, 0],
        },
        index=['WGT', 'APGRX'],
    )
    correct.index.name = 'covariate'
    pd.testing.assert_frame_equal(res.covariate_statistics, correct)


def test_get_params(load_model_for_test, create_model_for_test, testdata):
    model_frem = load_model_for_test(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    dist = model_frem.random_variables.etas[-1]
    rvs = list(dist.names)
    npars = 2

    param_names = get_params(model_frem, rvs, npars)
    assert param_names == ['CL', 'V']

    model_multiple_etas = re.sub(r'(V=TVV\*EXP\(ETA\(2\)\))', r'\1*EXP(ETA(3))', model_frem.code)

    model = create_model_for_test(model_multiple_etas)
    model = model.replace(dataset=model_frem.dataset)
    dist = model.random_variables.etas[-1]
    rvs = list(dist.names)
    npars = 3

    param_names = get_params(model, rvs, npars)
    assert param_names == ['CL', 'V(1)', 'V(2)']

    model_separate_declare = re.sub(
        r'(V=TVV\*EXP\(ETA\(2\)\))',
        'ETA2=ETA(2)\n      V=TVV*EXP(ETA2)',
        model_frem.code,
    )

    model = create_model_for_test(model_separate_declare)
    model = model.replace(dataset=model_frem.dataset)
    dist = model.random_variables.etas[-1]
    rvs = list(dist.names)
    npars = 2

    param_names = get_params(model, rvs, npars)
    print(param_names)
    assert param_names == ['CL', 'V']


def test_psn_frem_results(testdata):
    res = psn_frem_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5
    assert ofv['model_1'] == approx(730.894727)
    assert ofv['model_2'] == approx(896.974324)
    assert ofv['model_3'] == approx(868.657803)
    assert ofv['model_3b'] == approx(852.803483)
    assert ofv['model_4'] == approx(753.302743)

    correct = """model type		TVCL  TVV  IVCL  OMEGA_2_1  IVV  OMEGA_3_1  OMEGA_3_2  BSV_APGR  OMEGA_4_1  OMEGA_4_2  OMEGA_4_3  BSV_WGT  SIGMA_1_1
model_1  init      0.004693   1.00916    0.030963         NaN    0.031128         NaN         NaN         NaN         NaN         NaN         NaN         NaN    0.013241
model_1  estimate  0.005818   1.44555    0.111053         NaN    0.201526         NaN         NaN         NaN         NaN         NaN         NaN         NaN    0.016418
model_2  init           NaN       NaN         NaN         NaN         NaN         NaN         NaN    1.000000         NaN         NaN    0.244579    1.000000         NaN
model_2  estimate       NaN       NaN         NaN         NaN         NaN         NaN         NaN    1.000000         NaN         NaN    0.244579    1.000000         NaN
model_3  init           NaN       NaN    0.115195    0.007066    0.209016   -0.010583    0.107027    1.000008    0.171529    0.404278    0.244448    1.002173         NaN
model_3  estimate       NaN       NaN    0.115195    0.007066    0.209016   -0.010583    0.107027    1.000010    0.171529    0.404278    0.244448    1.002170         NaN
model_3b init      0.005818   1.44555    0.125999    0.020191    0.224959   -0.012042    0.115427    1.000032    0.208475    0.415588    0.244080    1.007763    0.016418
model_3b estimate  0.005818   1.44555    0.126000    0.020191    0.224959   -0.012042    0.115427    1.000030    0.208475    0.415588    0.244080    1.007760    0.016418
model_4  init      0.005818   1.44555    0.126000    0.020191    0.224959   -0.012042    0.115427    1.000030    0.208475    0.415588    0.244080    1.007760    0.016418
model_4  estimate  0.007084   1.38635    0.220463    0.195326    0.176796    0.062712    0.117271    1.039930    0.446939    0.402075    0.249237    1.034610    0.015250
"""  # noqa E501
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1], sep=r'\s+')
    pd.testing.assert_frame_equal(res.parameter_inits_and_estimates, correct, rtol=1e-4)

    pc = res.base_parameter_change
    assert len(pc) == 5
    assert pc['TVCL'] == 21.77321763763502
    assert pc['TVV'] == -4.095327038151563
    assert pc['IVCL'] == pytest.approx(98.52052623522104, abs=1e-12)
    assert pc['IVV'] == -12.271369451088198
    assert pc['SIGMA_1_1'] == pytest.approx(-7.110618417927009, abs=1e-12)

    correct = """,mean,stdev
APGR,6.42372,2.237640
WGT,1.525424,0.704565
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0])
    pd.testing.assert_frame_equal(res.estimated_covariates, correct, rtol=1e-5)

    correct = """condition,parameter,CL,V
all,CL,0.025328,0.022571
all,V,0.022571,0.020115
APGR,CL,0.216681,0.188254
APGR,V,0.188254,0.163572
WGT,CL,0.027391,0.021634
WGT,V,0.021634,0.020540
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    pd.testing.assert_frame_equal(res.parameter_variability, correct, rtol=1e-4)

    correct = """condition,parameter,APGR,WGT
all,CL,-0.020503,0.628814
all,V,0.00930905,0.544459
each,CL,0.0269498,0.613127
each,V,0.0503961,0.551581
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    pd.testing.assert_frame_equal(res.coefficients, correct, rtol=1e-5)


def test_create_results(testdata):
    res = create_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5


def test_modeling_create_results(testdata):
    res = tools.run.create_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5


def test_create_report(testdata, tmp_path):
    res = tools.read_results(testdata / 'frem' / 'results.json')
    shutil.copy(testdata / 'frem' / 'results.json', tmp_path)
    tools.create_report(res, tmp_path)
    html = tmp_path / 'results.html'
    assert html.is_file()
    assert html.stat().st_size > 500000
