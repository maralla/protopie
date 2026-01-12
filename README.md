protopy
=======

`protopy` is a LALR(1) parser for protobuf.


**Disclaimer**: This project is heavily assisted by code agents.


*Note that currently only proto3 syntax is supported.*

Quickstart
----------

```python
from protopy import parse_files

result = parse_files(
    entrypoints=["/abs/path/to/root.proto"],
    import_paths=["/abs/path/to/include"],
)

# result.files maps absolute path -> AST File node
root_ast = result.files[result.entrypoints[0]]
```

License
-------

MIT(LICENSE)
