from __future__ import annotations

from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from protopy import parse_source


def _ident() -> st.SearchStrategy[str]:
    head = st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"))
    tail = st.text(
        alphabet=list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"),
        min_size=0,
        max_size=12,
    )
    # Exclude boolean literals and keywords that create LALR(1) conflicts
    return st.builds(lambda h, t: h + t, head, tail).filter(
        lambda s: s not in {
            # Boolean literals (never allowed as identifiers)
            "true",
            "false",
            # Keywords that create LALR(1) conflicts (empirically tested)
            "option",
            "repeated",
            "optional",
            "oneof",
            "reserved",
            "enum",
            "message",
            "extend",
            "stream",
            # Note: syntax, map, import, weak, public, package, to, max,
            # service, rpc, returns are now ALLOWED as identifiers!
        }
    )


@st.composite
def proto_sources(draw: Any) -> str:  # noqa: C901, PLR0912, PLR0915, ANN401
    """Generate comprehensive proto3 files with all major features."""
    pkg = draw(st.one_of(st.none(), st.lists(_ident(), min_size=1, max_size=3)))
    path_atom = st.text(
        alphabet=list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/"),
        min_size=1,
        max_size=12,
    )
    imports = draw(st.lists(path_atom, max_size=2))

    # All scalar types
    scalar_types = [
        "int32", "int64", "uint32", "uint64", "sint32", "sint64",
        "fixed32", "fixed64", "sfixed32", "sfixed64",
        "float", "double", "bool", "string", "bytes"
    ]

    parts = ['syntax = "proto3";', ""]
    used_names = set()  # Track all used names to avoid conflicts

    # Package
    if pkg is not None:
        parts.append("package " + ".".join(pkg) + ";")
        parts.append("")

    # Imports
    parts.extend(f'import "{imp}.proto";' for imp in imports)
    if imports:
        parts.append("")

    # File-level options (optional)
    if draw(st.booleans()):
        opt_name = draw(st.sampled_from(["java_package", "java_outer_classname"]))
        opt_val = draw(_ident())
        parts.append(f'option {opt_name} = "{opt_val}";')
        parts.append("")

    # Generate enums with unique names
    enum_count = draw(st.integers(min_value=0, max_value=2))
    enum_names = []
    for _ in range(enum_count):
        ename = draw(_ident().filter(lambda n: n not in used_names))
        used_names.add(ename)
        enum_names.append(ename)
        value_count = draw(st.integers(min_value=1, max_value=3))
        enum_values_used = set()
        values = []
        # First value must be 0 in proto3
        first_val = draw(_ident())
        enum_values_used.add(first_val)
        values.append(f"  {first_val} = 0;")
        for i in range(1, value_count):
            val_name = draw(_ident().filter(lambda n: n not in enum_values_used))  # noqa: B023
            enum_values_used.add(val_name)
            values.append(f"  {val_name} = {i};")
        parts.append(f"enum {ename} {{")
        parts.extend(values)
        parts.append("}")
        parts.append("")

    # Generate messages with various features
    msg_count = draw(st.integers(min_value=1, max_value=3))
    msg_names = []

    for _ in range(msg_count):
        mname = draw(_ident().filter(lambda n: n not in used_names))
        used_names.add(mname)
        msg_names.append(mname)
        msg_body = []
        field_no = 1
        field_names_used = set()
        reserved_field_names = set()

        # Reserved names (optional) - track them to avoid conflicts
        if draw(st.integers(min_value=0, max_value=5)) == 0:
            reserved_names = []
            for _ in range(draw(st.integers(min_value=1, max_value=2))):
                rname = draw(_ident())
                reserved_names.append(f'"{rname}"')
                reserved_field_names.add(rname)
            msg_body.append(f"  reserved {', '.join(reserved_names)};")

        # Reserved numbers (optional)
        if draw(st.integers(min_value=0, max_value=5)) == 0:
            if draw(st.booleans()):
                msg_body.append(f"  reserved {field_no};")
                field_no += 1
            else:
                start = field_no
                end = field_no + draw(st.integers(min_value=1, max_value=2))
                msg_body.append(f"  reserved {start} to {end};")
                field_no = end + 1

        # Regular fields
        fcount = draw(st.integers(min_value=0, max_value=3))
        for _ in range(fcount):
            fname = draw(
                _ident().filter(
                    lambda n: n not in field_names_used  # noqa: B023
                    and n not in reserved_field_names  # noqa: B023
                )
            )
            field_names_used.add(fname)
            ftype = draw(st.sampled_from(scalar_types))

            # Optional, repeated, or regular
            label_choice = draw(st.sampled_from(["", "repeated", "optional"]))
            label = f"{label_choice} " if label_choice else ""

            msg_body.append(f"  {label}{ftype} {fname} = {field_no};")
            field_no += 1

        # Map fields (optional)
        max_field_no = 50
        if draw(st.integers(min_value=0, max_value=3)) == 0 and field_no < max_field_no:
            map_key = draw(st.sampled_from(["int32", "int64", "string", "bool"]))
            map_val = draw(st.sampled_from(scalar_types[:5]))
            map_name = draw(
                _ident().filter(
                    lambda n: n not in field_names_used  # noqa: B023
                    and n not in reserved_field_names  # noqa: B023
                )
            )
            field_names_used.add(map_name)
            msg_body.append(f"  map<{map_key}, {map_val}> {map_name} = {field_no};")
            field_no += 1

        # Oneof (optional)
        if draw(st.integers(min_value=0, max_value=3)) == 0 and field_no < max_field_no:
            oneof_name = draw(_ident())
            oneof_fields = []
            for _ in range(draw(st.integers(min_value=1, max_value=2))):
                oneof_fname = draw(
                    _ident().filter(
                        lambda n: n not in field_names_used  # noqa: B023
                        and n not in reserved_field_names  # noqa: B023
                    )
                )
                field_names_used.add(oneof_fname)
                oneof_fields.append(
                    f"    {draw(st.sampled_from(scalar_types[:5]))} "
                    f"{oneof_fname} = {field_no};"
                )
                field_no += 1
            msg_body.append(f"  oneof {oneof_name} {{")
            msg_body.extend(oneof_fields)
            msg_body.append("  }")

        # Nested enum (optional)
        if draw(st.integers(min_value=0, max_value=5)) == 0:
            nested_enum = draw(_ident())
            msg_body.append(f"  enum {nested_enum} {{")
            msg_body.append(f"    {draw(_ident())} = 0;")
            msg_body.append("  }")

        # Nested message (optional)
        if draw(st.integers(min_value=0, max_value=5)) == 0:
            nested_msg = draw(_ident())
            msg_body.append(f"  message {nested_msg} {{")
            if draw(st.booleans()):
                nested_field_type = draw(st.sampled_from(scalar_types[:3]))
                nested_field_name = draw(_ident())
                msg_body.append(f"    {nested_field_type} {nested_field_name} = 1;")
            msg_body.append("  }")

        parts.append(f"message {mname} {{")
        parts.extend(msg_body)
        parts.append("}")
        parts.append("")

    # Service (optional)
    if draw(st.integers(min_value=0, max_value=3)) == 0 and msg_names:
        sname = draw(_ident().filter(lambda n: n not in used_names))
        parts.append(f"service {sname} {{")
        rpc_count = draw(st.integers(min_value=1, max_value=2))
        rpc_names_used = set()
        for _ in range(rpc_count):
            rpc_name = draw(_ident().filter(lambda n: n not in rpc_names_used))
            rpc_names_used.add(rpc_name)
            req_type = draw(st.sampled_from(msg_names))
            resp_type = draw(st.sampled_from(msg_names))
            req_stream = "stream " if draw(st.booleans()) else ""
            resp_stream = "stream " if draw(st.booleans()) else ""
            rpc_line = (
                f"  rpc {rpc_name} ({req_stream}{req_type}) "
                f"returns ({resp_stream}{resp_type});"
            )
            parts.append(rpc_line)
        parts.append("}")
        parts.append("")

    return "\n".join(parts)


@given(proto_sources())
@settings(
    max_examples=300,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_roundtrip_stable_format(src: str) -> None:
    """Test that parsing and formatting is idempotent (roundtrip stable)."""
    ast1 = parse_source(src, file="fuzz.proto")
    out1 = ast1.format()
    ast2 = parse_source(out1, file="fuzz.proto")
    out2 = ast2.format()
    assert out2 == out1  # noqa: S101

