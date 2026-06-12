from nbclient import NotebookClient
from nbformat import read, write
from pathlib import Path

nb_path = Path('notebooks/economical_analysis_clean.ipynb')
out_path = Path('notebooks/economical_analysis_executed.ipynb')

with nb_path.open('r', encoding='utf-8') as f:
    nb = read(f, as_version=4)
client = NotebookClient(nb, timeout=600, kernel_name='python3')
try:
    print('Starting notebook execution...')
    client.execute()
    with out_path.open('w', encoding='utf-8') as f:
        write(nb, f)
    print('Executed notebook saved to', out_path)
    print('Finished notebook execution.')
except Exception as e:
    partial_path = Path('notebooks/economical_analysis_partial.ipynb')
    with partial_path.open('w', encoding='utf-8') as f:
        write(nb, f)
    print('Notebook execution failed; partial notebook saved to', partial_path)
    print('Error:', e)
    raise
