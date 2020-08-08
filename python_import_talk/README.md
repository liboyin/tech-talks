# PUG Talk: From Python import *

### A Common Source of Confusion

* Thanks to the obscure error messages and easy-to-break nature.
* If we have a knowledge / usage ratio among all Python features, the import mechanism might have the lowest score!
* This talk assumes Python 3.5+. For Python 2 users: official support for Python 2.7 will stop in 2020.

### Basic Usages

For the standard library, everything "just works". It'll be hard to get errors here.

```python
>>> import sys
>>> from os import path
>>> import numpy as np
>>> import xml.etree.ElementTree as et
>>> from os.path import is_file, is_dir
```

If you have a lot to import:

```python
>>> from os.path import (abspath, basename, dirname, exists,
                         is_file, is_dir, join, split)
>>> from os.path import abspath, basename, dirname, exists,\
                        is_file, is_dir, join, split
```

Don't import everything unless you know exactly what's in the imported module. For example, the following import shadows built-in `min()`, `max()`, and `sum()` with the `NumPy` version, which have totally different signatures!

Demo: run in PyCharm interactive console. See how many things got poured into the default namespace.

```python
>>> from numpy import *
```

### Modules & Packages

Let's check the glossary first:

Module:

> An object that serves as an organizational unit of Python code. Modules have a namespace containing arbitrary Python objects. Modules are loaded into Python by the process of importing.

In other words, each module is an independent namespace. Different modules can have objects with the same name. (See Zen of Python, #19!) Python takes advantage of this fact a lot, allowing the language to have very dynamic behaviours, e.g. duck typing.

Package:

> A Python module which can contain submodules or recursively, subpackages. Technically, a package is a Python module with an `__path__` attribute.

This is the precise definition, but probably not a very helpful one, because the `__path__` attribute is generated automatically for each level of the package structure. Let's see an example:

```python
>>> import xml.etree.ElementTree
>>> xml.__path__
['/Users/libo/.miniconda3/envs/py36/lib/python3.6/xml']
>>> xml.etree.__path__
['/Users/libo/.miniconda3/envs/py36/lib/python3.6/xml/etree']
>>> xml.etree.ElementTree.__path__
Traceback (most recent call last):
  File "/Users/libo/.miniconda3/envs/py36/lib/python3.6/site-packages/IPython/core/interactiveshell.py", line 2910, in run_code
    exec(code_obj, self.user_global_ns, self.user_ns)
  File "<ipython-input-8-56b3c29080c2>", line 1, in <module>
    xml.etree.ElementTree.__path__
AttributeError: module 'xml.etree.ElementTree' has no attribute '__path__'
```

The last error is because `ElementTree` is, as suggested by its CamelCase name, a class in module `xml.etree` instead of a module by itself.

Side note: in `containers`, modules with CamelCase name are Python classes; modules with lower case name are implemented in C. This is in accordance with PEP-8.

Importing:

> The process by which Python code in one module is made available to Python code in another module.

For most users, it is sufficient to know the following:

1. Every Python file is a module. A package is a collection of modules in a hierarchy.
2. When a module is found, a `types.ModuleType` instance is created, and is binded to a name in the local scope. There is only one `ModuleType`, but it is just a normal Python class. You can extend the default module behaviour by subclassing it.
3. When a module is loaded, all statements from that module are executed in that module's global namespace in the same way a script is executed. This is true even if only certain members/functions are imported, e.g. `from math import pi, sin, cos`.
4. All imported modules are cached under `sys.modules`. This means that in the following case,  repeated function calls won't import `pandas` over and over again [1]:
    
    ```python
    def get_csv_shape(file_path):
        import pandas as pd
        return pd.read_csv(file_path).shape
    ```

    [1]. Unless executed in multiprocessing. Multithreaded import is locked (not the usual GIL) as a special case by the Python interpreter.

5. This also means that if there are any changes in the imported module, changes won't be picked up. This can be particularly annoying when working in interactive mode. For simple program structures, use this IPython/Jupyter trick:

    ```python
    %load_ext autoreload
    %autoreload 2
    ```

    However, this trick is not guaranteed to work for complex program structures. We'll come back to this topic later.

### Package Structure & Relative Import

```
my_pkg
├── sub1
│   ├── __init__.py
│   ├── x.py
│   └── y.py
├── sub2
│   ├── __init__.py
│   └── __main__.py
├── __init__.py
└── top.py
```

`__init__.py` is essential for nested imports (with the exception of namespace package, which I'll talk about in our next demo). `__init__.py` is usually empty, but it's also a common practise to organise all its sub-components (e.g. `asincio`). From a software engineering point of view, it is recommended to keep `__init__.py` simple, as readers probably won't expect much from it.

Demo: `my_pkg/sub1/__init__.py`:

```python
>>> from .x import print_name as print_x
>>> from .y import print_name as print_y
# controls what's imported by from my_pkg.sub1 import *
>>> __all__ = ['print_x', 'print_y']
```

`from .x import ...` is called an explicit relative import. The dot means "from the same directory". Two dots would mean "from the parent directory". In Python 2, we could write `from x import ...`, but not in Python 3. The reason is that `from x import ...` can also refer to a totally different package `x` on `sys.path`. In a complex program structure, explicit relative import is a lot less error-prone. (See Zen of Python, #2!)

To allow import statements to navigate up & down the hierarchy, each module in a package has a unique fully qualified name, relative to a path in `sys.path` (which we will also talk about later). For example, if our CWD is the parent directory of `my_pkg`, then the fully-qualified name for `my_pkg/sub1/x.py` is `my_pkg.sub1.x`. If our CWD is `my_pkg`, then the fully-qualified name for `sub1/x.py` is `sub1.x`.

The fully qualified name of a module also decides the sequence of import. For example, while importing `my_pkg.sub1.x`, the Python interpreter first imports `my_pkg` by calling `my_pkg/__init__.py`, then `my_pkg.sub1` by calling `my_pkg/sub1/__init__.py`, then `my_pkg.sub1.x`.

(Demo: try import with Python interpreter launched from the parent dir of `my_pkg`, and from `my_pkg`.)

(Demo: read code in `my_pkg/sub2`.)

There is one important exception to fully qualified names: the fully qualified name of the entry point is always `__main__`. A common error with importing is to use relative imports from the entry point:

```bash
(py36) Libos-MBP:demo1 libo$ python my_pkg/sub2/__main__.py
Traceback (most recent call last):
  File "/Users/libo/.miniconda3/envs/py36/lib/python3.6/runpy.py", line 193, in _run_module_as_main
    "__main__", mod_spec)
  File "/Users/libo/.miniconda3/envs/py36/lib/python3.6/runpy.py", line 85, in _run_code
    exec(code, run_globals)
  File "my_pkg/sub2/__main__.py", line 5, in <module>
    from ..sub1 import *
ImportError: attempted relative import with no known parent package
```

or this:

```bash
(py36) Libos-MBP:demo1 libo$ python my_pkg/sub1/__init__.py
importing __main__
Traceback (most recent call last):
  File "my_pkg/sub1/__init__.py", line 18, in <module>
    from .x import print_name as print_x
ModuleNotFoundError: No module named '__main__.x'; '__main__' is not a package

```

Another possible error is that the Python interpreter executes the entry point in the `__main__` namespace, in which the module got imported again, resulting in a double execution:

```bash
(py36) Libos-MBP:demo1 libo$ python -m my_pkg.sub1.__init__
importing my_pkg.sub1
importing my_pkg.sub1.x
importing my_pkg.sub1.y
importing __main__
```

The solution to this problem is to use the `if __name__ == '__main__'` guard.

We can also explicitly designate the entry point of a package by naming the entry point `__main__.py`. This demo puts the entry point in `my_pkg/sub2` to demonstrate importing from a parallel sub-package, but the same pattern can be used for unit testing.

```bash
(py36) Libos-MBP:demo1 libo$ python -m my_pkg.sub2
importing my_pkg.sub2
importing my_pkg.sub1
importing my_pkg.sub1.x
importing my_pkg.sub1.y
my_pkg.sub1.x.print_name
my_pkg.sub1.y.print_name
my_pkg.sub2.__main__.print_name
```

### Module Lookup

Module lookup is by sequentially traversing `sys.path`. (I believe most Python users have modified `sys.path` at some stage, despite not recommended.) If the package is not on `sys.path`, then there is no hope of successfully importing it [2]. However, the interpreter not only looks for Python source files on `sys.path`. Run Python in verbose mode, and all import attempts will be displayed.

[2]. With some exceptions. But we have to go very far to do so. We will (hopefully) come back to this topic.

Demo: `python -vv` to see all import attempts at interpreter startup time.

`sys.path` is constructed from CWD, `PYTHONPATH`, `sys.prefix`, site configurations, and user configurations. Most details here are beyond the scope of this talk, but here are a few:

* `sys.prefix` and `sys.exec_prefix` decide where your interpreter and its accompanying packages are. Virtualenv (already heritage now) uses these variables to allow isolated execution environments.
* If you want to add something to `sys.path`, consider `PYTHONPATH`. `PYTHONPATH` is prepended to `sys.path`, giving it the highest priority. Example: `env PYTHONPATH=/foo:/bar python -S` [3].

[3]. `python -S` runs Python without initialising site configuration.

We mentioned `__path__` in the glossary section before. `__path__` is a list generated automatically for each level of imported messages to assist with the import of its submodules. And because it's a list, we can add things to it. For example, here's a hack that's useful for plugins:

```python
import xml.etree.ElementTree
xml.__path__.append('.')
import xml.my_pkg
```

We'll revisit module lookup later after introducing `importlib`.

### Namespace Packages

This is a cool new feature added in Python 3.3 via PEP-420. It is very easy to understand, so I'll jump straight into the demo. Note the absence of `__init__.py`. Without `__init__.py`, a package becomes a namespace package. But if any one these packages contains an `__init__.py`, that particular package will take over.

```
demo2
├── my_pkg
│   └── my_pkg
│       └── x.py
└── sub2
    └── my_pkg
        └── y.py
```

To make it work, we must manually add `sub1` and `sub2` to `sys.path`. Note that `sub1` and `sub2` do not have to be adjacent at all:

```python
>>> sys.path.extend(['./sub1', './sub2'])
>>> import my_pkg
>>> my_pkg.__path__
_NamespacePath(['./sub1/my_pkg', './sub2/my_pkg'])
```

Then we can import as if `sub1` and `sub2` don't exist. We can also import from one in another, but we'll lose IDE assistance because everything is dynamic. In other words, this namespace package is logically equivalent to:

```
demo2
└── my_pkg
    ├── __init__.py
    ├── x.py
    └── y.py
```

(Demo: also try import in the verbose mode!)

### importlib: Imported for Imports

`importlib` is a collection of import-related utilities. It was added in Python 3.1, and it opens up many internals of the import mechanism.

#### `importlib.import_module()`

`import_module()` handles dynamic imports, i.e. import a module given its fully qualified name. It is a high-level wrapper of the built-in function `__import__()`. The latter should not be used directly.

#### `importlib.reload()`

We have mentioned previously that Python caches loaded modules in `sys.modules`, and this can cause some issues. `importlib.reload()` reloads a module, and updates the cache. What it does is really simple: it reads the file again, and executes it in the original namespace. Unfortunately, this can cause more issues:

1. `reload()` does not handle dependencies. (demo with `my_pkg/sub1`)
2. Existing instances won't (and cannot possibly) update, because `__init__` is not called again during reloading. (demo with `my_pkg/top.py`)
3. `reload()` doesn't clean the cache before executing the code. (demo with a new field)

The `autoreload` trick in IPython/Jupyter uses `reload()`. `%autoreload 2` means to reload everything before executing code. So issue 2 and 3 are actually the desired behaviour here! This is a great example of the context-dependent nature of import.

After all, restarting the interpreter is always a safe choice.

#### `importlib.util.find_spec()`

Usually when we are not sure whether a package exists, we use the EAFP pattern [4]:

```python
try:
    import json
except ImportError:
    import simplejson as json
```

[4]. "Easier to Ask for Forgiveness than Permission"

However, there is a caveat: This `try` clause will fail if `json` exists, but a different `ImportError` was raised during its import process. In such cases, the code will always silently load `simplejson`. This can cause much confusion.

As a solution, use the following pattern, which allows much cleaner conditions:

```python
from importlib.util import find_spec
if find_spec('json'):
    import json
else:
    import simplejson as json
```

Side note: The boolean value of a custom object is `True` by default.

### Module Lookup Revisited

Disclaimer: This following section goes deep into the implementation of the import mechanism. They may very well change in the future.

`find_spec` returns a `ModuleSpec` instance, but results for different packages look different:

```python
>>> find_spec('itertools')
ModuleSpec(
    name='itertools',
    loader=<class '_frozen_importlib.BuiltinImporter'>,
    origin='built-in'
)
>>> find_spec('my_pkg')
ModuleSpec(
    name='my_pkg',
    loader=<_frozen_importlib_external.SourceFileLoader object at 0x111557a90>,
    origin='/Users/libo/Documents/PUG_Import_Talk/demo1/my_pkg/__init__.py',
    submodule_search_locations=['/Users/libo/Documents/PUG_Import_Talk/demo1/my_pkg']
)
```

This is because they are generated by different meta path finders. We can find all of them in `sys.meta_path`:

```python
>>> sys.meta_path 
[
    _frozen_importlib.BuiltinImporter,
    _frozen_importlib.FrozenImporter,
    _frozen_importlib_external.PathFinder,
    <six._SixMetaPathImporter at 0x10ac13be0>,
    <pkg_resources.extern.VendorImporter at 0x10c9fb5f8>,
    <pkg_resources._vendor.six._SixMetaPathImporter at 0x10ca9afd0>
]
>>> sys.meta_path[0].find_spec('my_pkg')
>>> sys.meta_path[0].find_spec('itertools')
ModuleSpec(
    name='itertools',
    loader=<class '_frozen_importlib.BuiltinImporter'>,
    origin='built-in'
)
>>> sys.meta_path[1].find_spec('my_pkg')
>>> sys.meta_path[2].find_spec('my_pkg')
ModuleSpec(
    name='my_pkg',
    loader=<_frozen_importlib_external.SourceFileLoader object at 0x10da42be0>,
    origin='/Users/libo/Documents/PUG_Import_Talk/demo1/my_pkg/__init__.py',
    submodule_search_locations=['/Users/libo/Documents/PUG_Import_Talk/demo1/my_pkg']
)
```

It turns out that once the Python interpreter failed to find a cached version of a module, it turns to `sys.meta_path`. Different meta path finders represent different path-finding strategies. If a path finder successfully found the loader for a given package, it returns a `ModuleSpec`; otherwise it returns `None`, and passes to the next meta path finder in the list. Because path finders are just Python objects, we can create our own:

```python
>>> class MyFinder:
...     @classmethod
...     def find_spec(cls, name, *args, **kwargs):
...             print(f'finding {name}') 
>>> import sys
>>> sys.meta_path.insert(0, MyFinder)  # so that all imports goes through MyFinder
>>> import threading
finding threading
finding time
finding traceback
finding linecache
finding tokenize
finding token
```

This opens up a lot of possibilities. It allows us to bypass settings in `sys.path`, import from an URL, etc.

An `ModuleSpec` instance contains a reference to a loader. The loader takes the import target, executes it, and updates the `sys.modules` cache.

Demo: show available methods in a loader.

```python
>>> spec = find_spec('my_pkg.sub1')
>>> spec.loader.get_source('my_pkg.sub1')
# output source code of my_pkg/sub1/__init__.py
```

And we are back to the beginning.

### Further Reading

* The import system: https://docs.python.org/3/reference/import.html
* Importlib: https://docs.python.org/3/library/importlib.html
* Python glossary: https://docs.python.org/3/glossary.html
* Relative imports for the billionth time: https://stackoverflow.com/questions/14132789/relative-imports-for-the-billionth-time
* Traps for the Unwary in Python’s Import System: http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html
* Brett Cannon: How Import Works: https://www.youtube.com/watch?v=Nsg886UOahw
* David Beazley: Modules and Packages - Live and Let Die: http://www.dabeaz.com/modulepackage/index.html
* IPython autoreload: http://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html
* PEP 8 - Style Guide for Python Code: https://www.python.org/dev/peps/pep-0008/
* PEP 20 - The Zen of Python: https://www.python.org/dev/peps/pep-0020/
* PEP 328 - Imports: Multi-Line and Absolute/Relative: https://www.python.org/dev/peps/pep-0328/
* PEP 420 - Implicit Namespace Packages: https://www.python.org/dev/peps/pep-0420/
