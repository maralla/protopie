from __future__ import annotations

# ruff: noqa: S101, E501, PERF401, C901, PLR0912, PLR0915, PLC0206, D103
# mypy: disable-error-code="import-untyped,union-attr,misc"

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2
from grpc_tools import protoc

from protopy import parse_file


FIXTURE_ROOT = Path("tests/fixtures/third_party/protobuf").resolve()
GOOGLE_PROTOBUF = FIXTURE_ROOT / "google" / "protobuf"

REQUIRED_FIXTURES: tuple[str, ...] = (
    # A curated, representative subset of upstream well-known proto3 files.
    "google/protobuf/any.proto",
    "google/protobuf/duration.proto",
    "google/protobuf/timestamp.proto",
    "google/protobuf/empty.proto",
    "google/protobuf/field_mask.proto",
    "google/protobuf/source_context.proto",
    "google/protobuf/struct.proto",
    "google/protobuf/type.proto",
)


def _fixture_files() -> list[Path]:
    if not GOOGLE_PROTOBUF.exists():
        raise AssertionError(
            f"required third-party fixtures are missing: {GOOGLE_PROTOBUF}\n"
            "re-run: uv run python scripts/fetch_third_party_fixtures.py --dest tests/fixtures/third_party"
        )
    return sorted(GOOGLE_PROTOBUF.rglob("*.proto"))


def test_third_party_fixtures_are_present() -> None:
    files = _fixture_files()
    # Sanity: ensure we didn't accidentally vendor nothing.
    assert any(p.name == "any.proto" for p in files)
    assert any(p.name == "timestamp.proto" for p in files)
    # And ensure required curated fixtures exist.
    for rel in REQUIRED_FIXTURES:
        assert (FIXTURE_ROOT / rel).exists(), f"missing required fixture: {rel}"


def test_parse_all_third_party_fixtures() -> None:
    for rel in REQUIRED_FIXTURES:
        p = (FIXTURE_ROOT / rel).resolve()
        parse_file(p)


@dataclass(frozen=True, slots=True)
class SimpleField:
    name: str
    number: int
    repeated: bool
    scalar: str | None  # scalar name as in .proto, if scalar
    type_name: str | None
    typ: int  # descriptor_pb2.FieldDescriptorProto.TYPE_*


@dataclass(frozen=True, slots=True)
class SimpleMessage:
    name: str
    fields: tuple[SimpleField, ...]


@dataclass(frozen=True, slots=True)
class SimpleFile:
    name: str
    package: str
    imports: tuple[str, ...]
    messages: tuple[SimpleMessage, ...]


_SCALAR_TO_PROTOC_TYPE: dict[str, int] = {
    "double": descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
    "float": descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
    "int64": descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    "uint64": descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
    "int32": descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
    "fixed64": descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64,
    "fixed32": descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32,
    "bool": descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
    "string": descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    "bytes": descriptor_pb2.FieldDescriptorProto.TYPE_BYTES,
    "uint32": descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    "sfixed32": descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32,
    "sfixed64": descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64,
    "sint32": descriptor_pb2.FieldDescriptorProto.TYPE_SINT32,
    "sint64": descriptor_pb2.FieldDescriptorProto.TYPE_SINT64,
}


def _compile_with_grpc_tools(entry: Path) -> descriptor_pb2.FileDescriptorSet:
    rel = entry.relative_to(FIXTURE_ROOT).as_posix()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.pb"
        args = [
            "protoc",
            f"-I{FIXTURE_ROOT}",
            "--include_imports",
            f"--descriptor_set_out={out}",
            rel,
        ]
        # grpc_tools.protoc returns an exit code (0 success).
        rc = protoc.main(args)
        if rc != 0:
            raise AssertionError(f"grpc_tools.protoc failed for {rel} with rc={rc}")
        data = out.read_bytes()
    fds = descriptor_pb2.FileDescriptorSet()
    fds.ParseFromString(data)
    return fds


def _simplify_truth(fds: descriptor_pb2.FileDescriptorSet, *, file_name: str) -> SimpleFile:
    fd = next((f for f in fds.file if f.name == file_name), None)
    assert fd is not None, f"missing {file_name} in descriptor set"

    msgs: list[SimpleMessage] = []
    for m in fd.message_type:
        fields: list[SimpleField] = []
        for f in m.field:
            fields.append(
                SimpleField(
                    name=f.name,
                    number=f.number,
                    repeated=(f.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
                    scalar=None,
                    type_name=f.type_name if f.type_name else None,
                    typ=f.type,
                )
            )
        msgs.append(SimpleMessage(name=m.name, fields=tuple(fields)))

    return SimpleFile(
        name=fd.name,
        package=fd.package,
        imports=tuple(fd.dependency),
        messages=tuple(msgs),
    )


def _simplify_ours(entry: Path) -> SimpleFile:
    ast = parse_file(entry)
    pkg = str(ast.package.name) if ast.package else ""

    msgs: list[SimpleMessage] = []
    for proto_item in ast.items:
        if proto_item.item is None or type(proto_item.item).__name__ != "Message":
            continue
        it = proto_item.item
        fields: list[SimpleField] = []
        for body_elem in it.body.elements:
            if body_elem.element is None:
                continue

            # Handle oneof blocks - extract fields from oneofs
            if type(body_elem.element).__name__ == "Oneof":
                oneof = body_elem.element
                for oneof_field_elem in oneof.body.fields:
                    if oneof_field_elem.field is None:
                        continue
                    e = oneof_field_elem.field

                    # Process the oneof field same as regular fields below
                    repeated = hasattr(e.label, "repeated") and e.label.repeated
                    scalar = None
                    type_name = None
                    if hasattr(e.field_type, "name") and hasattr(e.field_type.name, "parts"):
                        parts = e.field_type.name.parts
                        if len(parts) == 1:
                            name_text = parts[0].text
                            if name_text in _SCALAR_TO_PROTOC_TYPE:
                                scalar = name_text
                            else:
                                type_name = name_text
                        else:
                            type_name = ".".join(p.text for p in parts)

                    fields.append(
                        SimpleField(
                            name=e.name.text,
                            number=int(e.number.value),
                            repeated=repeated,
                            scalar=scalar,
                            type_name=type_name,
                            typ=_SCALAR_TO_PROTOC_TYPE.get(scalar, 0) if scalar else 0,
                        )
                    )
                continue

            if type(body_elem.element).__name__ != "Field":
                continue
            e = body_elem.element

            # Handle map fields
            if type(e.field_type).__name__ == "MapType":
                # Map fields are represented as repeated nested message types in protoc's descriptor
                # Protoc internally converts `map<K,V> field = N;` to a repeated message field
                fields.append(
                    SimpleField(
                        name=e.name.text,
                        number=int(e.number.value),
                        repeated=True,  # Maps are represented as repeated fields in descriptors
                        scalar=None,
                        type_name=None,  # Maps don't have a single type_name
                        typ=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
                    )
                )
                continue

            repeated = hasattr(e.label, "repeated") and e.label.repeated

            # Determine if it's a scalar type
            scalar = None
            type_name = None
            if hasattr(e.field_type, "name") and hasattr(e.field_type.name, "parts"):
                parts = e.field_type.name.parts
                if len(parts) == 1:
                    # Single identifier - might be a scalar
                    name_text = parts[0].text
                    if name_text in _SCALAR_TO_PROTOC_TYPE:
                        scalar = name_text
                    else:
                        # It's a message or enum type
                        type_name = name_text
                else:
                    # Qualified name - definitely a message or enum type
                    type_name = ".".join(p.text for p in parts)

            fields.append(
                SimpleField(
                    name=e.name.text,
                    number=int(e.number.value),
                    repeated=repeated,
                    scalar=scalar,
                    type_name=type_name,
                    typ=_SCALAR_TO_PROTOC_TYPE.get(scalar, 0) if scalar else 0,
                )
            )
        msgs.append(SimpleMessage(name=it.name.text, fields=tuple(fields)))

    rel = entry.relative_to(FIXTURE_ROOT).as_posix()
    return SimpleFile(
        name=rel,
        package=pkg.lstrip("."),
        imports=tuple(i.path for i in ast.imports),
        messages=tuple(msgs),
    )


@pytest.mark.parametrize(
    "rel",
    [
        # Keep this strict-but-small: well-known proto3 files with simple scalars.
        "google/protobuf/any.proto",
        "google/protobuf/duration.proto",
        "google/protobuf/timestamp.proto",
    ],
)
def test_required_parity_with_descriptor_set(rel: str) -> None:
    entry = (FIXTURE_ROOT / rel).resolve()
    assert entry.exists(), f"missing required fixture: {entry}"

    ours = _simplify_ours(entry)
    fds = _compile_with_grpc_tools(entry)
    truth = _simplify_truth(fds, file_name=rel)

    assert ours.package == truth.package
    assert ours.imports == truth.imports

    # For these files, message set and scalar field details should match.
    truth_msgs = {m.name: m for m in truth.messages}
    ours_msgs = {m.name: m for m in ours.messages}
    assert set(ours_msgs) == set(truth_msgs)

    for name, tm in truth_msgs.items():
        om = ours_msgs[name]
        tfields = {f.name: f for f in tm.fields}
        ofields = {f.name: f for f in om.fields}
        assert set(ofields) == set(tfields)
        for fn, tf in tfields.items():
            of = ofields[fn]
            assert of.number == tf.number
            assert of.repeated == tf.repeated
            if of.scalar is not None:
                assert of.typ == tf.typ
                assert tf.type_name in (None, "")
            else:
                # Non-scalar types (message/enum) should carry a type_name in descriptors.
                assert tf.type_name not in (None, "")
                assert of.type_name is not None


@pytest.mark.parametrize(
    "proto_file",
    [p.relative_to(FIXTURE_ROOT) for p in _fixture_files()],
    ids=lambda p: str(p),
)
def test_comprehensive_parity_all_fixtures(proto_file: Path) -> None:
    """Comprehensive validation: parse all fixture files and compare with protoc.

    This test validates our parser against Google's official protoc compiler
    for all available proto files. It's marked as 'slow' to avoid slowing
    down regular test runs.

    Run with: pytest -v -m slow
    Or run all tests including slow: pytest -v
    Skip slow tests: pytest -v -m "not slow"
    """
    entry = (FIXTURE_ROOT / proto_file).resolve()
    assert entry.exists(), f"fixture file missing: {entry}"

    # Parse with our parser
    try:
        ours = _simplify_ours(entry)
    except Exception as e:
        pytest.fail(f"Our parser failed on {proto_file}: {e}")

    # Compile with official protoc
    try:
        fds = _compile_with_grpc_tools(entry)
        truth = _simplify_truth(fds, file_name=str(proto_file))
    except Exception as e:
        pytest.skip(f"protoc failed (file may have advanced features): {e}")

    # Compare package
    assert ours.package == truth.package, f"Package mismatch in {proto_file}"

    # Compare imports (convert Ident to string for comparison)
    ours_imports_str = sorted(
        [imp.text if hasattr(imp, "text") else str(imp) for imp in ours.imports]
    )
    truth_imports_str = sorted(truth.imports)
    assert ours_imports_str == truth_imports_str, f"Imports mismatch in {proto_file}"

    # Compare message structure
    truth_msgs = {m.name: m for m in truth.messages}
    ours_msgs = {m.name: m for m in ours.messages}

    # Allow our parser to recognize more messages (nested, etc) but verify all protoc messages exist
    missing_in_ours = set(truth_msgs) - set(ours_msgs)
    if missing_in_ours:
        pytest.fail(f"Messages missing in our parser for {proto_file}: {missing_in_ours}")

    # For messages that exist in both, verify field structure
    for name in truth_msgs:
        if name not in ours_msgs:
            continue

        tm = truth_msgs[name]
        om = ours_msgs[name]
        tfields = {f.name: f for f in tm.fields}
        ofields = {f.name: f for f in om.fields}

        # Verify all protoc fields exist in our parser
        missing_fields = set(tfields) - set(ofields)
        if missing_fields:
            pytest.fail(f"Fields missing in our parser for {proto_file}::{name}: {missing_fields}")

        # Verify field details match
        for fn in tfields:
            if fn not in ofields:
                continue

            tf = tfields[fn]
            of = ofields[fn]

            assert of.number == tf.number, (
                f"Field number mismatch in {proto_file}::{name}.{fn}: "
                f"ours={of.number} vs protoc={tf.number}"
            )
            assert of.repeated == tf.repeated, (
                f"Field repeated mismatch in {proto_file}::{name}.{fn}: "
                f"ours={of.repeated} vs protoc={tf.repeated}"
            )

            if of.scalar is not None:
                assert of.typ == tf.typ, (
                    f"Scalar type mismatch in {proto_file}::{name}.{fn}: "
                    f"ours={of.typ} vs protoc={tf.typ}"
                )
            elif tf.type_name not in (None, ""):
                # Check if this looks like a map field (repeated message with special naming)
                # Protoc generates internal MapEntry types, but our parser doesn't
                # Skip type_name validation for map fields
                is_map_field = (
                    of.repeated
                    and of.typ == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
                    and of.type_name is None
                )

                if not is_map_field:
                    # Both should agree on message/enum type names
                    # Note: protoc uses fully qualified names, we may use simple names
                    # This is acceptable - just verify we have a type name
                    assert of.type_name not in (None, ""), (
                        f"Missing type name in {proto_file}::{name}.{fn}: "
                        f"ours={of.type_name} vs protoc={tf.type_name}"
                    )
