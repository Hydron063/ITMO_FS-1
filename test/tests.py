import pandas as pd

from filters.GiniIndexFilter import GiniIndexFilter
from filters.SpearmanCorrelationFilter import SpearmanCorrelationFilter


def filter_test(filter, X, y, answer):
    try:
        assert filter.run(X, y).keys() == answer.keys()
        print('Test passed')
    except AssertionError:
        print('Test failed')


def wrapper_test(wrapper):
    pass  # TODO test wrapper algorithm


def electricity_preprocess():
    data = pd.read_csv('data/electricity-normalized.csv')
    data['class'] = data['class'].apply(lambda x: 0 if x == 'DOWN' else 1)
    target = data['class']
    data = data.drop(['class'], axis=1)
    return data, target



electricity_X, electricity_y = electricity_preprocess()
filter_tests = [
    (SpearmanCorrelationFilter(0.3), electricity_X, electricity_y,
     {'date': 0.9999999989252104, 'day': 0.9999999499088564, 'period': 0.9999999991477627,
      'nswprice': 0.9999999989323045, 'nswdemand': 0.9999999993656636, 'vicprice': 0.9999999987695205,
      'vicdemand': 0.9999999993251367, 'transfer': 0.999999999146249}),
    (GiniIndexFilter(0.3), electricity_X, electricity_y, {})
]

if __name__ == '__main__':
    for test in filter_tests:
        filter_test(*test)