protopie
========

LALR(1) parser for protobuf.


One interesting aspect about the implementation of the parser is that we utilize Python type
annotations to define the grammar productions. And the whole project passes the strict mypy type checker.


**Disclaimer**: This project is heavily assisted by code agents.


*Note that currently only proto3 syntax is supported.*

Installation
------------

```bash
uv add protopie
```

Quickstart
----------

#### Parse source code directly

```python
from protopie import parse_source

source = '''
syntax = "proto3";

message User {
  string name = 1;
  int32 age = 2;
}
'''

ast = parse_source(source)
```

#### Parse files with import resolution

```python
from protopie import parse_files

result = parse_files(
    entrypoints=["/abs/path/to/root.proto"],
    import_paths=["/abs/path/to/include"],
)

# result.files maps absolute path -> AST File node
root_ast = result.files[result.entrypoints[0]]
```

License
-------

[MIT](LICENSE)
