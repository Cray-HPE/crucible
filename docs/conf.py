#
#  MIT License
#
#  (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.
#

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
import os
import sys
from importlib.metadata import version
from importlib.metadata import PackageNotFoundError
try:
    version = version('crucible')
except PackageNotFoundError:
    pass

sys.path.insert(0, os.path.abspath('..'))

project = 'The Crucible'
copyright = '2023, Cray / HPE'
author = 'Russell Bunch'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_copybutton',
    'sphinx_autodoc_typehints',
    'sphinx_rtd_theme',
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_title = f"{project} Documentation ({version})"
locale_dirs = ['locale/']   # path is example but recommended.
language = 'en'
gettext_compact = False     # optional.
versioning_conditions = ['text']
# -- Options for HTML output -------------------------------------------------
html_show_sphinx = False
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    'logo_only': True,
    'navigation_depth': 5,
}
html_static_path = ['_static']
html_favicon = '_static/favicon.ico'
html_logo = '_static/crucible.png'
html_context = {
    'display_github': True,
    'github_user': 'Cray-HPE',
    'github_repo': 'crucible',
    'github_version': 'poc/docs/',
}
# html_additional_pages = {'index': 'index.html.j2'}
