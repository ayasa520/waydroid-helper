from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

# Collect all pywayland modules and data files
datas, binaries, hiddenimports = collect_all('pywayland')

# Also collect submodules explicitly
hiddenimports += collect_submodules('pywayland')

# Ensure all pywayland submodules are included
hiddenimports += [
    'pywayland._ffi',
    'pywayland.client',
    'pywayland.client.display',
    'pywayland.client.eventqueue',
    'pywayland.protocol',
    'pywayland.utils',
]

# Try to find pywayland installation and collect all Python files
try:
    import pywayland
    pywayland_path = os.path.dirname(pywayland.__file__)

    # Collect all .py files from pywayland
    for root, dirs, files in os.walk(pywayland_path):
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), pywayland_path)
                src_path = os.path.join(root, file)
                dst_path = os.path.join('pywayland', rel_path)
                datas.append((src_path, os.path.dirname(dst_path)))
except ImportError:
    pass
