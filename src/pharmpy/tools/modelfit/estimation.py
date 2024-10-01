import time
from functools import partial

from pharmpy.deps import numpy as np
from pharmpy.deps import scipy, symengine
from pharmpy.modeling import cleanup_model, get_thetas
from pharmpy.tools.modelfit.ucp import (
    build_initial_values_matrix,
    build_parameter_coordinates,
    build_starting_ucp_vector,
    calculate_gradient_scale,
    descale_matrix,
    descale_thetas,
    get_parameter_symbols,
    scale_matrix,
    scale_thetas,
    split_ucps,
)


def build_matrix_gradients(coords):
    # Build dA/dx for each matrix parameter x
    n = coords[-1][0] + 1
    grads = []
    for row, col in coords:
        D = np.zeros((n, n))
        D[row, col] = 1.0
        grads.append(D)
    return grads


def build_zero_gradients(coords, n):
    size = coords[-1][0] + 1
    A = np.zeros((size, size))
    zeros = [A] * n
    return zeros


def build_parameter_symbolic_gradients(nthetas, omega_coords, sigma_coords):
    omegas = (
        build_zero_gradients(omega_coords, nthetas)
        + build_matrix_gradients(omega_coords)
        + build_zero_gradients(omega_coords, len(sigma_coords))
    )
    sigmas = build_zero_gradients(
        sigma_coords, nthetas + len(omega_coords)
    ) + build_matrix_gradients(sigma_coords)
    return omegas, sigmas


def init(model):
    model = cleanup_model(model)
    dv = next(iter(model.dependent_variables))  # Assuming only one DV
    y = symengine.sympify(
        model.statements.full_expression(dv)
    )  # Function of THETA, ETA , EPS and COVs
    y_norvs = y.subs({rv: 0 for rv in model.random_variables.names})

    symbolic_eta_gradient = [y.diff(eta_name) for eta_name in model.random_variables.etas.names]
    symbolic_eps_gradient = [y.diff(eps_name) for eps_name in model.random_variables.epsilons.names]

    parameter_symbols = get_parameter_symbols(model)

    symbolic_dG_dx_all = [
        [eta.diff(param) for eta in symbolic_eta_gradient] for param in parameter_symbols
    ]
    symbolic_dH_dx_all = [
        [eps.diff(param) for eps in symbolic_eps_gradient] for param in parameter_symbols
    ]

    df = model.dataset
    dvcol = model.datainfo.dv_column.name
    idcol = model.datainfo.id_column.name
    ids = df[idcol].unique()

    omega_inits = build_initial_values_matrix(model.random_variables.etas, model.parameters)
    sigma_inits = build_initial_values_matrix(model.random_variables.epsilons, model.parameters)
    omega_scale = scale_matrix(omega_inits)
    sigma_scale = scale_matrix(sigma_inits)
    omega_coords = build_parameter_coordinates(omega_inits)
    sigma_coords = build_parameter_coordinates(sigma_inits)

    theta_scale = scale_thetas(get_thetas(model))
    omega_grads, sigma_grads = build_parameter_symbolic_gradients(
        len(theta_scale[0]), omega_coords, sigma_coords
    )
    x = build_starting_ucp_vector(theta_scale, omega_coords, sigma_coords)

    func = partial(
        ofv_func,
        theta_scale,
        omega_scale,
        sigma_scale,
        omega_coords,
        sigma_coords,
        symbolic_eta_gradient,
        symbolic_eps_gradient,
        y_norvs,
        parameter_symbols,
        ids,
        df,
        idcol,
        dvcol,
        symbolic_dG_dx_all,
        symbolic_dH_dx_all,
        omega_grads,
        sigma_grads,
    )
    return x, func


def ofv_func(
    theta_scale,
    omega_scale,
    sigma_scale,
    omega_coords,
    sigma_coords,
    symbolic_eta_gradient,
    symbolic_eps_gradient,
    y_norvs,
    parameter_symbols,
    ids,
    df,
    idcol,
    dvcol,
    symbolic_dG_dx_all,
    symbolic_dH_dx_all,
    omega_grads,
    sigma_grads,
    x,
):

    theta_ucp, omega_ucp, sigma_ucp = split_ucps(x, omega_coords, sigma_coords)

    theta = descale_thetas(theta_ucp, theta_scale)
    omega = descale_matrix(omega_ucp, omega_scale)
    sigma = descale_matrix(sigma_ucp, sigma_scale)

    print(theta, omega, sigma)

    theta_subs = {parameter_symbols[i]: value for i, value in enumerate(theta)}
    subs_eta_gradient = [deta.subs(theta_subs) for deta in symbolic_eta_gradient]
    subs_eps_gradient = [deps.subs(theta_subs) for deps in symbolic_eps_gradient]
    subs_y_norvs = y_norvs.subs(theta_subs)

    OFVsum = 0.0
    gradsum = [0.0] * len(x)

    for curid in ids:
        curdf = df[df[idcol] == curid]
        DVi = np.array(curdf[dvcol])
        Gi = np.array([[float(val) for val in subs_eta_gradient]] * len(DVi))
        Hi = np.array([[float(val) for val in subs_eps_gradient]] * len(DVi))
        PREDi = np.array([float(subs_y_norvs)] * len(DVi))
        RESi = DVi - PREDi
        Ci = Gi @ omega @ Gi.T + (Hi @ sigma @ Hi.T) * np.eye(len(DVi))
        try:
            Ci_inv = np.linalg.inv(Ci)
        except np.linalg.LinAlgError:
            return np.inf, np.zeros_like(x)
        OFVi = np.log(np.linalg.det(Ci)) + RESi.T @ Ci_inv @ RESi
        OFVsum += OFVi

        # gradient calculation
        for i, param in enumerate(parameter_symbols):
            symbolic_dG_dx = symbolic_dG_dx_all[i]
            symbolic_dH_dx = symbolic_dH_dx_all[i]
            symbolic_dP_dx = y_norvs.diff(param)
            symbolic_dG_dx_subs = [e.subs(theta_subs) for e in symbolic_dG_dx]
            symbolic_dH_dx_subs = [e.subs(theta_subs) for e in symbolic_dH_dx]
            symbolic_dP_dx_subs = symbolic_dP_dx.subs(theta_subs)
            dGi = np.array([[float(val) for val in symbolic_dG_dx_subs]] * len(DVi))
            dHi = np.array([[float(val) for val in symbolic_dH_dx_subs]] * len(DVi))
            neg_dPi = -np.array([float(symbolic_dP_dx_subs)] * len(DVi))
            symb_omega = omega_grads[i]
            symb_sigma = sigma_grads[i]
            dCi = (
                dGi @ omega @ Gi.T
                + Gi @ symb_omega @ Gi.T
                + Gi @ omega @ dGi.T
                + (dHi @ sigma @ Hi.T) * np.eye(len(DVi))
                + (Hi @ symb_sigma @ Hi.T) * np.eye(len(DVi))
                + (Hi @ sigma @ dHi.T) * np.eye(len(DVi))
            )
            grad_i = (
                np.trace(Ci_inv @ dCi)
                + (neg_dPi).T @ Ci_inv @ RESi
                + RESi.T @ (-Ci_inv @ dCi @ Ci_inv @ RESi + Ci_inv @ (neg_dPi))
            )
            gradsum[i] += grad_i

    grad_scale = calculate_gradient_scale(
        theta_ucp,
        omega_ucp,
        sigma_ucp,
        theta_scale,
        omega_scale,
        sigma_scale,
        omega_coords,
        sigma_coords,
    )
    grad = gradsum * grad_scale

    print("OFV", OFVsum)
    print("Gradient", grad)
    return OFVsum, grad


def estimate(model):
    x, func = init(model)

    start_time = time.time()
    res = scipy.optimize.minimize(func, x, jac=True, method='BFGS')
    end_time = time.time()
    print(res)

    print(f"Estimation time: {end_time - start_time} s")
