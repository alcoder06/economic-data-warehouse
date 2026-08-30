import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from nbclient import NotebookClient
from nbformat import read, write
from pathlib import Path

nb_path = Path('notebooks/uzbekistan_economic_analysis.ipynb')
out_path = Path('notebooks/uzbekistan_economic_analysis_executed.ipynb')

with nb_path.open('r', encoding='utf-8') as f:
    nb = read(f, as_version=4)
# The notebook reads data/gold with relative paths, so the kernel has to start
# in the repository root rather than in notebooks/.
client = NotebookClient(nb, timeout=600, kernel_name='python3',
                        resources={'metadata': {'path': str(nb_path.parent.parent)}})
try:
    print('Starting notebook execution...')
    client.execute()
    with out_path.open('w', encoding='utf-8') as f:
        write(nb, f)
    print('Executed notebook saved to', out_path)
    print('Finished notebook execution.')
except Exception as e:
    partial_path = Path('notebooks/uzbekistan_economic_analysis_partial.ipynb')
    with partial_path.open('w', encoding='utf-8') as f:
        write(nb, f)
    print('Notebook execution failed; partial notebook saved to', partial_path)
    print('Error:', e)
    raise
