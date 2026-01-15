from __future__ import annotations

from pathlib import Path

import pytest

from protopy import ParseError, parse_files, parse_source


def test_missing_syntax_is_error() -> None:
    with pytest.raises(ParseError) as e:
        parse_source('package foo; message A {}', file="x.proto")
    assert "missing syntax" in str(e.value)
    assert "x.proto" in str(e.value)


def test_syntax_must_be_proto3() -> None:
    with pytest.raises(ParseError) as e:
        parse_source('syntax = "proto2";', file="x.proto")
    assert "only proto3" in str(e.value)


def test_parse_message_enum_service_and_format_roundtrip() -> None:
    src = """syntax = "proto3";

package foo.bar;

import "dep.proto";

option java_package = "x";

message A {
  reserved 1 to 3, 9;
  reserved "old";
  int32 id = 1;
  repeated string tags = 2 [deprecated = true];
  oneof choice {
    string a = 3;
    bytes b = 4;
  }
  enum E {
    option allow_alias = true;
    ZERO = 0;
    NONE = 0;
  }
}

service S {
  rpc Get (A) returns (A);
  rpc Get1 (A) returns (A);
  rpc Get2 (A) returns (A) {}
  rpc Get3 (A) returns (A) {
    option features.abcd = "hi";
    option features.efg = "foo";
  }
}
"""
    ast1 = parse_source(src, file="x.proto")
    out = ast1.format()
    ast2 = parse_source(out, file="x.proto")
    assert ast2.format() == out


def test_import_resolution(tmp_path: Path) -> None:
    dep = tmp_path / "dep.proto"
    dep.write_text('syntax = "proto3"; message Dep {}', encoding="utf-8")
    root = tmp_path / "root.proto"
    root.write_text('syntax = "proto3"; import "dep.proto"; message Root {}', encoding="utf-8")

    res = parse_files(entrypoints=[root], import_paths=[])
    assert str(root.resolve()) in res.files
    assert str(dep.resolve()) in res.files


def test_import_not_found_is_nice_error(tmp_path: Path) -> None:
    root = tmp_path / "root.proto"
    root.write_text('syntax = "proto3"; import "missing.proto"; message Root {}', encoding="utf-8")
    with pytest.raises(ParseError) as e:
        parse_files(entrypoints=[root], import_paths=[])
    assert "import not found" in str(e.value)

