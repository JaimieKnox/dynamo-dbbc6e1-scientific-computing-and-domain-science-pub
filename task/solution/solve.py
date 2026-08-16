#!/usr/bin/env python3
from pathlib import Path

from estimator import estimate_to_file

estimate_to_file(Path("/app/data"), Path("/app/output/domain_cif.csv"))
