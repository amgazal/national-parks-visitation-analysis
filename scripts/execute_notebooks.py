"""Execute both notebooks with fresh kernels using this Python environment."""
from pathlib import Path
import os
import sys
import tempfile
import json

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLBACKEND', 'Agg')
with tempfile.TemporaryDirectory(prefix='nps-kernel-') as temporary:
    kernel = Path(temporary) / 'nps-review'
    kernel.mkdir()
    (kernel / 'kernel.json').write_text(json.dumps({
        'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        'display_name': 'NPS analysis', 'language': 'python'}))
    manager = KernelSpecManager(kernel_dirs=[temporary])
    for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(notebook, timeout=600, kernel_name='nps-review',
                                resources={'metadata': {'path': str(ROOT)}},
                                kernel_manager_class=__import__('jupyter_client').KernelManager)
        client.create_kernel_manager()
        client.km.kernel_spec_manager = manager
        client.execute()
        # Keep a portable default kernel in the committed notebook metadata.
        notebook.metadata.kernelspec = dict(display_name='Python 3', language='python', name='python3')
        nbformat.write(notebook, path)
        print(f'Executed {path.name}', flush=True)
