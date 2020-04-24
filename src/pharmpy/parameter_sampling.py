import numpy as np
import pandas as pd

from pharmpy.math import is_posdef, nearest_posdef, sample_truncated_joint_normal


def sample_from_covariance_matrix(model, modelfit_results=None, parameters=None,
                                  force_posdef=False, n=1):
    """Sample parameter vectors using the covariance matrix

       if modelfit_results is not provided the results from the model will be used

       parameters - use to only sample a subset of the parameters. None means all

       returns a dataframe with one sample per row
    """
    if modelfit_results is None:
        modelfit_results = model.modelfit_results

    if parameters is None:
        parameters = list(modelfit_results.parameter_estimates.index)

    pe = modelfit_results.parameter_estimates[parameters]
    index = pe.index
    mu = pe.to_numpy()
    sigma = modelfit_results.covariance_matrix[parameters].loc[parameters].to_numpy()
    if not is_posdef(sigma):
        raise ValueError("Uncertainty covariance matrix not positive-definite")
    parameter_summary = model.parameters.summary().loc[parameters]
    parameter_summary = parameter_summary[~parameter_summary['fix']]
    a = parameter_summary.lower.astype('float64').to_numpy()
    b = parameter_summary.upper.astype('float64').to_numpy()

    # reject non-posdef
    kept_samples = pd.DataFrame()
    remaining = n
    while remaining > 0:
        samples = sample_truncated_joint_normal(mu, sigma, a, b, n=remaining)
        df = pd.DataFrame(samples, columns=index)
        if not force_posdef:
            selected = df[df.apply(model.random_variables.validate_parameters, axis=1,
                                   use_cache=True)]
        else:
            selected = df.transform(model.random_variables.nearest_valid_parameters, axis=1)
        kept_samples = pd.concat((kept_samples, selected))
        remaining = n - len(kept_samples)

    return kept_samples.reset_index(drop=True)


def sample_individual_estimates(model, parameters=None, samples_per_id=100):
    """Sample individual estimates given their covariance.

       parameters - A list of a subset of parameters to sample
                    None means all.
       returns a pool of samples as a DataFrame
    """
    ests = model.modelfit_results.individual_estimates
    covs = model.modelfit_results.individual_estimates_covariance
    if parameters is None:
        parameters = ests.columns
    ests = ests[parameters]
    samples = pd.DataFrame()
    for (idx, mu), sigma in zip(ests.iterrows(), covs):
        sigma = sigma[parameters].loc[parameters]
        sigma = nearest_posdef(sigma)
        id_samples = np.random.multivariate_normal(mu.values, sigma.values, size=samples_per_id)
        id_df = pd.DataFrame(id_samples, columns=ests.columns)
        id_df.index = [idx] * len(id_df)        # ID as index
        samples = pd.concat((samples, id_df))
    return samples
