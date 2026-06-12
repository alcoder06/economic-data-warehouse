import importlib.util
import sys
from pathlib import Path

files = ['load_data.py','metrics.py','regression_diagnostics.py','forecasting.py']
for fname in files:
    path = Path('scripts') / fname
    mod_name = fname.replace('.py','')
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(mod_name, 'OK')
    except Exception as e:
        print(mod_name, 'ERROR', e)
