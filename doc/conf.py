import sys
import pathlib

# Identify location of project sources for autodoc
sys.path.insert(0, str(pathlib.Path('..', 'src').resolve()))

# Configure as per https://www.sphinx-doc.org/en/master/usage/configuration.html
project = 'normit'
copyright = '%Y, Steven Bethard'
author = 'Steven Bethard'
release = version = '0.1'

html_theme = 'sphinx_rtd_theme'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]
autodoc_typehints = 'description'
# autodoc_member_order = 'bysource'
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
}
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'python-dateutil': ('https://dateutil.readthedocs.io/en/stable', None),
}