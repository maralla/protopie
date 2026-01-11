from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from protopy import parse_source


def _ident() -> st.SearchStrategy[str]:
    # Keep it simple and avoid keywords for the generator.
    head = st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"))
    tail = st.text(alphabet=list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"), min_size=0, max_size=12)
    return st.builds(lambda h, t: h + t, head, tail).filter(
        lambda s: s not in {
            "syntax",
            "import",
            "package",
            "option",
            "message",
            "enum",
            "service",
            "rpc",
            "returns",
            "stream",
            "oneof",
            "map",
            "repeated",
            "reserved",
            "to",
            "max",
            "weak",
            "public",
            "true",
            "false",
        }
    )


@st.composite
def proto_sources(draw) -> str:
    # Generate a limited, always-valid proto3 subset that exercises many productions.
    pkg = draw(st.one_of(st.none(), st.lists(_ident(), min_size=1, max_size=4)))
    path_atom = st.text(
        alphabet=list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/"),
        min_size=1,
        max_size=16,
    )
    imports = draw(st.lists(path_atom, max_size=3))

    # A few messages with scalar fields only (keeps generation small but meaningful).
    msg_count = draw(st.integers(min_value=0, max_value=4))
    msgs = []
    field_no = 1
    for _ in range(msg_count):
        mname = draw(_ident())
        fcount = draw(st.integers(min_value=0, max_value=6))
        fields = []
        for _ in range(fcount):
            fname = draw(_ident())
            ftype = draw(st.sampled_from(["int32", "int64", "string", "bytes", "bool"]))
            rep = draw(st.booleans())
            label = "repeated " if rep else ""
            fields.append(f"  {label}{ftype} {fname} = {field_no};")
            field_no += 1
        msgs.append("message " + mname + " {\n" + "\n".join(fields) + ("\n" if fields else "") + "}")

    parts = ['syntax = "proto3";', ""]
    if pkg is not None:
        parts.append("package " + ".".join(pkg) + ";")
        parts.append("")
    for imp in imports:
        # Keep imports syntactically valid; loader isn't invoked here.
        parts.append(f'import "{imp}.proto";')
    if imports:
        parts.append("")
    parts.extend(msgs)
    parts.append("")
    return "\n".join(parts)


@given(proto_sources())
@settings(
    max_examples=300,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_fuzz_roundtrip_stable_format(src: str) -> None:
    # Parse -> format -> parse -> format should converge (idempotent formatting).
    ast1 = parse_source(src, file="fuzz.proto")
    out1 = ast1.format()
    ast2 = parse_source(out1, file="fuzz.proto")
    out2 = ast2.format()
    assert out2 == out1

