import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import pytest
from fastapi.testclient import TestClient
from api.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
