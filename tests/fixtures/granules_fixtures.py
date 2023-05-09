"""
fixtures to help with debugging granule objects

"""
import pytest
import os
import pickle


@pytest.fixture(scope="function")
def data_directory():
    dir = os.path.join(os.path.dirname(__file__), '..', 'test_data')
    yield dir

@pytest.fixture(scope="function")
def granule_pickle_file_path(data_directory):
    pickle_file =  os.path.join(data_directory, 'granules.pkl')
    return pickle_file

@pytest.fixture(scope="function")
def granules_fixture(granule_pickle_file_path):
    with open(granule_pickle_file_path, 'rb') as fh:
        data = pickle.load(fh)
    yield data
