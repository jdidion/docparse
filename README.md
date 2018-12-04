# docparse

Library to parse common python docstring formats.

# Usage

```python
import docparse

def func(x: int):
  """This is a function with a Google-style docstring.

  Args:
    x: A paramter named 'x'

  Returns:
    The square of x.
  """
  return x*x

func_docs = docparse.parse_docs(func)

print(func_docs.summary)
print(func_docs.parameters["x"])
print(func_docs.returns)
```

# Todo

* Add support for Sphinx documentation style (https://github.com/rahulrrixe/parinx)
* Autodetect documentation style (https://github.com/dadadel/pyment/blob/master/pyment/docstring.py)
* Use enum for sections
* Add convenience function to parse all docs in file
