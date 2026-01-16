"""Comprehensive feature coverage tests for proto3 parser.

Tests both valid (should parse) and invalid (should fail) cases,
comparing behavior with Google's protoc compiler.
"""

from __future__ import annotations

# ruff: noqa: S101, S603, PLW1510, TRY300, PT006, E501, F841
# mypy: disable-error-code="import-untyped"

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from protopie import parse_source
from protopie.errors import ParseError


def _compile_with_protoc(source: str, timeout: float = 2.0) -> tuple[bool | None, str]:
    """Try to compile source with protoc, return (success, error_message).

    Args:
        source: Proto source code to compile
        timeout: Maximum time in seconds to wait for protoc (default: 2.0s)

    Returns:
        Tuple of (success, error_message). Returns (None, "timeout") if timeout exceeded.

    """
    with tempfile.TemporaryDirectory() as tmpdir:
        proto_file = Path(tmpdir) / "test.proto"
        proto_file.write_text(source, encoding="utf-8")
        desc_file = Path(tmpdir) / "test.pb"

        try:
            # Run protoc as subprocess with timeout
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grpc_tools.protoc",
                    f"--proto_path={tmpdir}",
                    f"--descriptor_set_out={desc_file}",
                    str(proto_file),
                ],
                timeout=timeout,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and desc_file.exists():
                return (True, "")
            return (False, "protoc compilation failed")
        except subprocess.TimeoutExpired:
            return (None, "timeout")


class TestValidFeatures:
    """Test that all proto3 features parse correctly and match protoc behavior."""

    @pytest.mark.parametrize(
        "source,description",
        [
            # Basic syntax
            ('syntax = "proto3";\n', "minimal file"),
            ('syntax = "proto3";\npackage test;\n', "with package"),
            # Messages
            ('syntax = "proto3";\nmessage Empty {}\n', "empty message"),
            ('syntax = "proto3";\nmessage M { string f = 1; }\n', "message with field"),
            ('syntax = "proto3";\nmessage M { repeated string f = 1; }\n', "repeated field"),
            # Scalar types
            ('syntax = "proto3";\nmessage M { int32 f = 1; }\n', "int32"),
            ('syntax = "proto3";\nmessage M { int64 f = 1; }\n', "int64"),
            ('syntax = "proto3";\nmessage M { uint32 f = 1; }\n', "uint32"),
            ('syntax = "proto3";\nmessage M { uint64 f = 1; }\n', "uint64"),
            ('syntax = "proto3";\nmessage M { sint32 f = 1; }\n', "sint32"),
            ('syntax = "proto3";\nmessage M { sint64 f = 1; }\n', "sint64"),
            ('syntax = "proto3";\nmessage M { fixed32 f = 1; }\n', "fixed32"),
            ('syntax = "proto3";\nmessage M { fixed64 f = 1; }\n', "fixed64"),
            ('syntax = "proto3";\nmessage M { sfixed32 f = 1; }\n', "sfixed32"),
            ('syntax = "proto3";\nmessage M { sfixed64 f = 1; }\n', "sfixed64"),
            ('syntax = "proto3";\nmessage M { float f = 1; }\n', "float"),
            ('syntax = "proto3";\nmessage M { double f = 1; }\n', "double"),
            ('syntax = "proto3";\nmessage M { bool f = 1; }\n', "bool"),
            ('syntax = "proto3";\nmessage M { string f = 1; }\n', "string"),
            ('syntax = "proto3";\nmessage M { bytes f = 1; }\n', "bytes"),
            # Map fields
            ('syntax = "proto3";\nmessage M { map<string, int32> f = 1; }\n', "map field"),
            ('syntax = "proto3";\nmessage M { map<int32, string> f = 1; }\n', "map with int key"),
            ('syntax = "proto3";\nmessage M { map<bool, bytes> f = 1; }\n', "map with bool key"),
            # Nested messages
            ('syntax = "proto3";\nmessage M { message N {} }\n', "nested message"),
            (
                'syntax = "proto3";\nmessage M { message N { string f = 1; } }\n',
                "nested with field",
            ),
            # Enums
            ('syntax = "proto3";\nenum E { ZERO = 0; }\n', "simple enum"),
            ('syntax = "proto3";\nenum E { ZERO = 0; ONE = 1; }\n', "enum with values"),
            ('syntax = "proto3";\nmessage M { enum E { ZERO = 0; } }\n', "nested enum"),
            # Oneofs
            ('syntax = "proto3";\nmessage M { oneof o { string a = 1; int32 b = 2; } }\n', "oneof"),
            # Reserved
            ('syntax = "proto3";\nmessage M { reserved 1, 2, 3; }\n', "reserved numbers"),
            ('syntax = "proto3";\nmessage M { reserved 1 to 10; }\n', "reserved range"),
            ('syntax = "proto3";\nmessage M { reserved 1 to max; }\n', "reserved to max"),
            ('syntax = "proto3";\nmessage M { reserved "foo", "bar"; }\n', "reserved names"),
            # Options
            ('syntax = "proto3";\noption java_package = "com.example";\n', "file option"),
            ('syntax = "proto3";\nmessage M { option deprecated = true; }\n', "message option"),
            (
                'syntax = "proto3";\nmessage M { string f = 1 [deprecated = true]; }\n',
                "field option",
            ),
            ('syntax = "proto3";\nenum E { option deprecated = true; ZERO = 0; }\n', "enum option"),
            ('syntax = "proto3";\nenum E { ZERO = 0 [deprecated = true]; }\n', "enum value option"),
            # Services
            (
                'syntax = "proto3";\nservice S { rpc M (E) returns (E); }\nmessage E {}\n',
                "service with rpc",
            ),
            (
                'syntax = "proto3";\nservice S { rpc M (E) returns (E) {} }\nmessage E {}\n',
                "rpc with empty body",
            ),
            (
                'syntax = "proto3";\nservice S { rpc M (stream E) returns (E); }\nmessage E {}\n',
                "streaming request",
            ),
            (
                'syntax = "proto3";\nservice S { rpc M (E) returns (stream E); }\nmessage E {}\n',
                "streaming response",
            ),
            # Comments (should be ignored)
            ('syntax = "proto3";\n// comment\nmessage M {}\n', "line comment"),
            ('syntax = "proto3";\n/* comment */\nmessage M {}\n', "block comment"),
        ],
    )
    def test_valid_feature_parses(self, source: str, description: str) -> None:
        """Test that valid proto3 features parse successfully."""
        # Test with our parser
        try:
            our_result = parse_source(source, file="test.proto")
            our_success = True
        except Exception as e:
            our_success = False
            pytest.fail(f"Our parser failed on {description}: {e}")

        # Test with protoc
        protoc_success, protoc_error = _compile_with_protoc(source)

        # Both should succeed
        assert our_success, f"Our parser should parse {description}"
        assert protoc_success, f"protoc should parse {description}: {protoc_error}"


class TestInvalidFeatures:
    """Test that invalid proto3 is rejected and we fail similarly to protoc."""

    @pytest.mark.parametrize(
        "source,description,error_pattern",
        [
            # Invalid syntax (proto3-only parser)
            ("syntax = proto3;\n", "unquoted syntax", None),
            # Invalid field numbers
            ('syntax = "proto3";\nmessage M { string f = 0; }\n', "field number 0", None),
            ('syntax = "proto3";\nmessage M { string f = -1; }\n', "negative field number", None),
            ('syntax = "proto3";\nmessage M { string f = 19000; }\n', "reserved range", None),
            (
                'syntax = "proto3";\nmessage M { string f = 536870912; }\n',
                "field number too large",
                None,
            ),
            # Duplicate field numbers
            (
                'syntax = "proto3";\nmessage M { string a = 1; int32 b = 1; }\n',
                "duplicate number",
                None,
            ),
            # Invalid map keys
            ('syntax = "proto3";\nmessage M { map<float, int32> f = 1; }\n', "float map key", None),
            (
                'syntax = "proto3";\nmessage M { map<double, int32> f = 1; }\n',
                "double map key",
                None,
            ),
            ('syntax = "proto3";\nmessage M { map<bytes, int32> f = 1; }\n', "bytes map key", None),
            ('syntax = "proto3";\nmessage M { map<M, int32> f = 1; }\n', "message map key", None),
            # Invalid enum
            ('syntax = "proto3";\nenum E { ONE = 1; }\n', "enum without zero", None),
            ('syntax = "proto3";\nenum E {}\n', "empty enum", None),
            # Invalid reserved
            ('syntax = "proto3";\nmessage M { reserved; }\n', "empty reserved", None),
            ('syntax = "proto3";\nmessage M { reserved 10 to 1; }\n', "backwards range", None),
            # Syntax errors
            ('syntax = "proto3";\nmessage M { string = 1; }\n', "missing field name", None),
            ('syntax = "proto3";\nmessage M { string f; }\n', "missing field number", None),
            ('syntax = "proto3";\nmessage M { string f = 1 }\n', "missing semicolon", None),
            ('syntax = "proto3";\nmessage M\n', "unclosed message", None),
            ('syntax = "proto3";\nmessage { string f = 1; }\n', "missing message name", None),
            # Invalid imports
            ('syntax = "proto3";\nimport;\n', "empty import", None),
            ('syntax = "proto3";\nimport other.proto;\n', "unquoted import", None),
            # Invalid package
            ('syntax = "proto3";\npackage;\n', "empty package", None),
            ('syntax = "proto3";\npackage 123;\n', "numeric package", None),
        ],
    )
    def test_invalid_feature_rejected(
        self, source: str, description: str, error_pattern: str | None
    ) -> None:
        """Test that invalid proto3 is rejected by our parser.

        We should fail on the same things protoc fails on.
        """
        # Test with our parser
        our_error = None
        try:
            parse_source(source, file="test.proto")
            our_success = True
        except ParseError as e:
            our_success = False
            our_error = str(e)
        except Exception as e:
            our_success = False
            our_error = str(e)

        # Test with protoc
        protoc_success, protoc_error = _compile_with_protoc(source)

        # Both should fail
        if protoc_success:
            pytest.skip(f"protoc accepts {description} - not an error case")

        assert not our_success, (
            f"Our parser should reject {description}, but parsed successfully. "
            f"protoc error: {protoc_error}"
        )

        # If we have a pattern, verify it's in our error message
        if error_pattern and our_error:
            assert error_pattern.lower() in our_error.lower(), (
                f"Expected error pattern '{error_pattern}' in error message: {our_error}"
            )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.parametrize(
        "source,description",
        [
            # Large field numbers
            ('syntax = "proto3";\nmessage M { string f = 536870911; }\n', "max field number"),
            # Many fields
            (
                'syntax = "proto3";\nmessage M { '
                + " ".join(f"string f{i} = {i};" for i in range(1, 101))
                + " }\n",
                "100 fields",
            ),
            # Deep nesting
            (
                'syntax = "proto3";\nmessage M1 { message M2 { message M3 { message M4 { message M5 {} } } } }\n',
                "deeply nested messages",
            ),
            # Long identifiers
            ('syntax = "proto3";\nmessage ' + "A" * 100 + " {}\n", "long message name"),
            # Many enum values
            (
                'syntax = "proto3";\nenum E { '
                + " ".join(f"V{i} = {i};" for i in range(100))
                + " }\n",
                "100 enum values",
            ),
            # Unicode in strings
            ('syntax = "proto3";\nmessage M { string f = 1; } // 你好世界\n', "unicode comment"),
            # Empty lines and whitespace
            ('syntax = "proto3";\n\n\nmessage M {\n\n  string f = 1;\n\n}\n', "extra whitespace"),
        ],
    )
    def test_edge_case(self, source: str, description: str) -> None:
        """Test edge cases work correctly."""
        # Test with our parser
        try:
            our_result = parse_source(source, file="test.proto")
            our_success = True
        except Exception as e:
            our_success = False
            our_error = str(e)

        # Test with protoc
        protoc_success, protoc_error = _compile_with_protoc(source)

        # Both should have same outcome
        assert our_success == protoc_success, (
            f"Behavior mismatch on {description}: "
            f"our_success={our_success}, protoc_success={protoc_success}"
            + (f"\nOur error: {our_error}" if not our_success else "")
            + (f"\nprotoc error: {protoc_error}" if not protoc_success else "")
        )
