#! /usr/bin/env python
'''
Brian2 setup script
'''

# isort:skip_file

import io
import sys
import os
import platform
from pkg_resources import parse_version
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from distutils.errors import CompileError, DistutilsPlatformError

import versioneer

REQUIRED_CYTHON_VERSION = '0.29'

try:
    import Cython
    if parse_version(Cython.__version__) < parse_version(REQUIRED_CYTHON_VERSION):
        raise ImportError('Cython version %s is too old' % Cython.__version__)
    from Cython.Build import cythonize
    cython_available = True
except ImportError:
    cython_available = False


def has_option(name):
    try:
        sys.argv.remove('--%s' % name)
        return True
    except ValueError:
        pass
    # allow passing all cmd line options also as environment variables
    env_val = os.getenv(name.upper().replace('-', '_'), 'false').lower()
    if env_val == "true":
        return True
    return False


WITH_CYTHON = has_option('with-cython')
FAIL_ON_ERROR = has_option('fail-on-error')

pyx_fname = os.path.join('brian2', 'synapses', 'cythonspikequeue.pyx')
cpp_fname = os.path.join('brian2', 'synapses', 'cythonspikequeue.cpp')

if WITH_CYTHON or not os.path.exists(cpp_fname):
    fname = pyx_fname
    if not cython_available:
        if FAIL_ON_ERROR and WITH_CYTHON:
            raise RuntimeError('Compilation with Cython requested/necessary but '
                               'Cython >= %s is not available.' % REQUIRED_CYTHON_VERSION)
        else:
            sys.stderr.write('Compilation with Cython requested/necessary but '
                             'Cython >= %s is not available.\n' % REQUIRED_CYTHON_VERSION)
            fname = None
    if not os.path.exists(pyx_fname):
        if FAIL_ON_ERROR and WITH_CYTHON:
            raise RuntimeError(('Compilation with Cython requested/necessary but '
                                'Cython source file %s does not exist') % pyx_fname)
        else:
            sys.stderr.write(('Compilation with Cython requested/necessary but '
                                'Cython source file %s does not exist\n') % pyx_fname)
            fname = None
else:
    fname = cpp_fname

if fname is not None:
    if (platform.system() == 'Linux' and
            platform.architecture()[0] == '32bit' and
            platform.machine() == 'x86_64'):
        # We are cross-compiling (most likely to build a 32Bit package for conda
        # on travis), set paths and flags for 32Bit explicitly
        print('Configuring compilation for cross-compilation to 32 Bit')
        extensions = [Extension("brian2.synapses.cythonspikequeue",
                                [fname],
                                include_dirs=[], # numpy include dir will be added later
                                library_dirs=['/lib32', '/usr/lib32'],
                                extra_compile_args=['-m32'],
                                extra_link_args=['-m32'])]
    else:
        extensions = [Extension("brian2.synapses.cythonspikequeue",
                                [fname],
                                include_dirs=[])]  # numpy include dir will be added later
    if fname == pyx_fname:
        extensions = cythonize(extensions)
else:
    extensions = []


class optional_build_ext(build_ext):
    '''
    This class allows the building of C extensions to fail and still continue
    with the building process. This ensures that installation never fails, even
    on systems without a C compiler, for example.
    If brian is installed in an environment where building C extensions
    *should* work, use the "--fail-on-error" option or set the environment
    variable FAIL_ON_ERROR to true.
    '''
    def build_extension(self, ext):
        import numpy
        numpy_incl = numpy.get_include()
        if hasattr(ext, 'include_dirs') and not numpy_incl in ext.include_dirs:
                ext.include_dirs.append(numpy_incl)
        try:
            build_ext.build_extension(self, ext)
        except (CompileError, DistutilsPlatformError) as ex:
            if FAIL_ON_ERROR:
                raise ex
            else:
                error_msg = ('Building %s failed (see error message(s) '
                             'above) -- pure Python version will be used '
                             'instead.') % ext.name
                sys.stderr.write('*' * len(error_msg) + '\n' +
                                 error_msg + '\n' +
                                 '*' * len(error_msg) + '\n')


# Use readme file as long description
with io.open(os.path.join(os.path.dirname(__file__), 'README.rst'),
             encoding='utf-8') as f:
    long_description = f.read()

setup(name='Brian2',
      version=versioneer.get_version(),
      packages=find_packages(),
      package_data={# include template files
                    'brian2.codegen.runtime.numpy_rt': ['templates/*.py_'],
                    'brian2.codegen.runtime.cython_rt': ['templates/*.pyx'],
                    'brian2.codegen.runtime.GSLcython_rt': ['templates/*.pyx'],
                    'brian2.devices.cpp_standalone': ['templates/*.cpp',
                                                      'templates/*.h',
                                                      'templates/makefile',
                                                      'templates/win_makefile',
                                                      'templates_GSL/*.cpp',
                                                      'brianlib/*.cpp',
                                                      'brianlib/*.h'],
                    # include test template files
                    'brian2.tests.test_templates.fake_package_1': ['templates/*.txt'],
                    'brian2.tests.test_templates.fake_package_2': ['templates/*.txt'],
                    # Include RALLPACK test data, external code, and pytest config
                    'brian2.tests': ['rallpack_data/README',
                                     'rallpack_data/ref_*',
                                     'func_def_cpp.cpp',
                                     'func_def_cpp.h',
                                     'func_def_cython.pyx',
                                     'func_def_cython.pxd',
                                     'pytest.ini'],
                    # include C++/Cython version of spike queue
                    'brian2.synapses': ['cspikequeue.cpp',
                                        'cythonspikequeue.pyx',
                                        'stdint_compat.h'],
                    # include randomkit
                    'brian2.random': ['randomkit/randomkit.c',
                                      'randomkit/randomkit.h']
                    },
      install_requires=['numpy>=1.17',
                        'cython>=0.29',
                        'sympy>=1.2',
                        'pyparsing',
                        'jinja2>=2.7',
                        'py-cpuinfo;platform_system=="Windows"',
                        'setuptools>=24.2'
                       ],
      setup_requires=['numpy>=1.10',
                      'setuptools>=24.2'
                      ],
      cmdclass=versioneer.get_cmdclass({'build_ext': optional_build_ext}),
      provides=['brian2'],
      extras_require={'test': ['pytest',
                               'pytest-xdist>=1.22.3'],
                      'docs': ['sphinx>=1.8',
                               'ipython>=5',
                               'sphinx-tabs']},
      zip_safe=False,
      ext_modules=extensions,
      url='http://www.briansimulator.org/',
      project_urls={
        'Documentation': 'https://brian2.readthedocs.io/',
        'Source': 'https://github.com/brian-team/brian2',
        'Tracker': 'https://github.com/brian-team/brian2/issues'
      },
      description='A clock-driven simulator for spiking neural networks',
      long_description=long_description,
      long_description_content_type='text/x-rst',
      author='Marcel Stimberg, Dan Goodman, Romain Brette',
      author_email='team@briansimulator.org',
      keywords='computational neuroscience simulation',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Bio-Informatics'
      ],
      python_requires='>=3.7'
      )
