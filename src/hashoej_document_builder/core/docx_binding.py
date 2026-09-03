"""Validation of DOCX document template bindings and Jinja/docxtpl syntax."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import docx
import docxtpl
import jinja2
from jinja2 import nodes

from hashoej_document_builder.core.errors import DOCXBindingValidationError

ALLOWED_LOOP_ATTRIBUTES = frozenset(
    {"index", "index0", "first", "last", "length", "revindex", "revindex0", "depth", "depth0", "cycle"}
)

ALLOWED_COMPARISON_OPS = frozenset({"eq", "ne", "in", "notin"})


@dataclass
class LexicalScope:
    """Represents a lexical scope for variable bindings and loop state."""

    parent: LexicalScope | None = None
    is_in_loop: bool = False
    loop_target: str | None = None
    loop_field: dict[str, Any] | None = None

    def lookup_target(self, name: str) -> tuple[bool, dict[str, Any] | None]:
        """Look up whether name is a locally bound loop target in this or an enclosing scope."""
        if self.is_in_loop and self.loop_target == name:
            return True, self.loop_field
        if self.parent is not None:
            return self.parent.lookup_target(name)
        return False, None

    def in_loop(self) -> bool:
        """Check if currently inside any lexical loop body."""
        if self.is_in_loop:
            return True
        if self.parent is not None:
            return self.parent.in_loop()
        return False


def extract_docx_xml(docx_path: Path | str) -> str:
    """Extract and patch all Jinja XML content from a DOCX document's body, headers, and footers."""
    try:
        tpl = docxtpl.DocxTemplate(docx_path)
        temp_doc = docx.Document(tpl.template_file)
        xml = tpl.xml_to_string(temp_doc._element.body)
        xml = tpl.patch_xml(xml)

        for uri in [tpl.HEADER_URI, tpl.FOOTER_URI]:
            for rel_key, val in temp_doc._part.rels.items():
                if (val.reltype == uri) and (val.target_part.blob):
                    _xml = tpl.xml_to_string(docxtpl.template.parse_xml(val.target_part.blob))
                    xml += tpl.patch_xml(_xml)

        return xml
    except Exception as exc:
        raise DOCXBindingValidationError(
            f"Invalid or corrupt DOCX document template {docx_path}: {exc}"
        ) from exc


def validate_docx_binding(docx_path: Path | str, form_definition: dict[str, Any]) -> None:
    """Validate that a DOCX document template is syntactically valid and binds only to declared document data fields.

    Enforces:
      - Lexical scoping for loops (sequential and nested loops maintain their own target bindings).
      - Strict output grammar: simple variable output, declared repeater child access, and loop metadata.
      - Narrow condition grammar: simple boolean presence, not, and/or, equality (==, !=), and membership (in, not in).
      - Rejection of 'info' fields as document data references.
      - Rejection of 'super', standalone 'loop', or 'loop.*' outside loops.
      - Rejection of arbitrary expressions, function calls, macros, filters, arithmetic, and subscripting.

    Raises:
        DOCXBindingValidationError: If the DOCX is corrupt, has invalid syntax, references unknown fields,
                                    or contains unapproved template constructs.
    """
    path = Path(docx_path)
    if not path.is_file():
        raise DOCXBindingValidationError(f"DOCX template file not found: {path}")

    # 1. Extract XML
    xml = extract_docx_xml(path)

    # 2. Parse Jinja AST
    env = jinja2.Environment()
    try:
        ast = env.parse(xml)
    except jinja2.exceptions.TemplateSyntaxError as exc:
        raise DOCXBindingValidationError(
            f"Invalid Jinja/docxtpl syntax in {path.name}: {exc.message} (line {exc.lineno})"
        ) from exc
    except Exception as exc:
        raise DOCXBindingValidationError(
            f"Failed to parse template AST for {path.name}: {exc}"
        ) from exc

    # 3. Map declared document-data fields (excluding info fields)
    data_fields: dict[str, dict[str, Any]] = {}
    for step in form_definition.get("steps", []):
        for field in step.get("fields", []):
            if field.get("type") != "info":
                data_fields[field["id"]] = field

    # 4. Scope-aware recursive AST validation
    root_scope = LexicalScope()
    _validate_node(ast, root_scope, data_fields, path.name)


def _validate_node(
    node: nodes.Node,
    scope: LexicalScope,
    data_fields: dict[str, dict[str, Any]],
    path_name: str,
) -> None:
    """Recursively validate an AST node and its children within the given lexical scope."""
    if isinstance(node, nodes.Template):
        for child in node.body:
            _validate_node(child, scope, data_fields, path_name)
    elif isinstance(node, nodes.Output):
        for expr in node.nodes:
            if isinstance(expr, nodes.TemplateData):
                continue
            _validate_output_expr(expr, scope, data_fields, path_name)
    elif isinstance(node, nodes.If):
        _validate_condition_expr(node.test, scope, data_fields, path_name)
        for child in node.body:
            _validate_node(child, scope, data_fields, path_name)
        for child in getattr(node, "elif_", []):
            _validate_node(child, scope, data_fields, path_name)
        for child in getattr(node, "else_", []):
            _validate_node(child, scope, data_fields, path_name)
    elif isinstance(node, nodes.For):
        if getattr(node, "recursive", False):
            raise DOCXBindingValidationError(f"Recursive loops are not allowed in {path_name}.")
        if getattr(node, "test", None) is not None:
            raise DOCXBindingValidationError(f"Loop filtering (if-clauses in for-loops) is not allowed in {path_name}.")

        if not isinstance(node.iter, nodes.Name):
            raise DOCXBindingValidationError(
                f"Loop iterable must be a direct field reference, found {type(node.iter).__name__} in {path_name}."
            )
        if not isinstance(node.target, nodes.Name):
            raise DOCXBindingValidationError(
                f"Loop target must be a simple variable name in {path_name}."
            )

        iter_name = node.iter.name
        target_name = node.target.name

        if iter_name not in data_fields:
            raise DOCXBindingValidationError(
                f"DOCX template loop iterates over unknown field {iter_name!r}. "
                f"Declared fields: {sorted(data_fields.keys())}"
            )

        iter_field = data_fields[iter_name]
        field_type = iter_field.get("type")
        if field_type not in ("repeater", "multiselect"):
            raise DOCXBindingValidationError(
                f"DOCX template loop iterates over field {iter_name!r} of type {field_type!r}, "
                "which is not a repeater or multiselect field."
            )

        loop_scope = LexicalScope(
            parent=scope,
            is_in_loop=True,
            loop_target=target_name,
            loop_field=iter_field,
        )

        for child in node.body:
            _validate_node(child, loop_scope, data_fields, path_name)
        for child in getattr(node, "else_", []):
            _validate_node(child, scope, data_fields, path_name)
    elif isinstance(node, nodes.TemplateData):
        pass
    else:
        raise DOCXBindingValidationError(
            f"Unsupported template construct {type(node).__name__} in {path_name}. "
            "Only simple variables, if-conditions, loops, repeater child access, and docxtpl structural tags are allowed."
        )


def _validate_output_expr(
    expr: nodes.Expr,
    scope: LexicalScope,
    data_fields: dict[str, dict[str, Any]],
    path_name: str,
) -> None:
    """Validate that an output expression ({{ ... }}) conforms to the simple output grammar."""
    if isinstance(expr, nodes.Name):
        name = expr.name
        if name == "loop":
            raise DOCXBindingValidationError(
                f"Invalid standalone variable 'loop' in {path_name}. Use 'loop.index', etc. inside a loop."
            )
        if name == "super":
            raise DOCXBindingValidationError(f"Variable 'super' is not permitted in {path_name}.")

        is_target, loop_field = scope.lookup_target(name)
        if is_target and loop_field is not None:
            if loop_field.get("type") == "multiselect":
                # Valid: direct scalar item output in multiselect loop
                return
            raise DOCXBindingValidationError(
                f"Cannot output entire repeater row object {name!r} in {path_name}. Use '{name}.<child_field>'."
            )

        if name in data_fields:
            return

        raise DOCXBindingValidationError(
            f"DOCX template references unknown variable {name!r}. "
            f"Declared fields: {sorted(data_fields.keys())}"
        )

    elif isinstance(expr, nodes.Getattr):
        if not isinstance(expr.node, nodes.Name):
            raise DOCXBindingValidationError(
                f"Chained or dynamic attribute access is not allowed in {path_name}."
            )

        base_name = expr.node.name
        attr_name = expr.attr

        if base_name == "loop":
            if not scope.in_loop():
                raise DOCXBindingValidationError(
                    f"Variable 'loop.{attr_name}' is only valid inside a for-loop body in {path_name}."
                )
            if attr_name not in ALLOWED_LOOP_ATTRIBUTES:
                raise DOCXBindingValidationError(
                    f"Unsupported loop attribute {attr_name!r} in {path_name}."
                )
            return

        is_target, loop_field = scope.lookup_target(base_name)
        if is_target and loop_field is not None:
            if loop_field.get("type") == "repeater":
                child_ids = {c["id"] for c in loop_field.get("fields", []) if c.get("type") != "info"}
                if attr_name not in child_ids:
                    raise DOCXBindingValidationError(
                        f"DOCX template references unknown child field {attr_name!r} on repeater {loop_field['id']!r}. "
                        f"Declared child fields: {sorted(child_ids)}"
                    )
                return
            raise DOCXBindingValidationError(
                f"Attribute access {attr_name!r} is not allowed on multiselect loop item {base_name!r}."
            )

        raise DOCXBindingValidationError(
            f"Attribute access on variable {base_name!r} is not allowed in {path_name}."
        )

    else:
        raise DOCXBindingValidationError(
            f"Unsupported expression construct {type(expr).__name__} in output tag in {path_name}. "
            "Only simple variable outputs, repeater child access, and loop metadata are permitted."
        )


def _validate_condition_expr(
    expr: nodes.Expr,
    scope: LexicalScope,
    data_fields: dict[str, dict[str, Any]],
    path_name: str,
) -> None:
    """Validate that an if-condition expression conforms to the supported boolean grammar."""
    if isinstance(expr, nodes.Name):
        name = expr.name
        if name in ("loop", "super"):
            raise DOCXBindingValidationError(f"Invalid condition variable {name!r} in {path_name}.")
        is_target, loop_field = scope.lookup_target(name)
        if is_target and loop_field is not None:
            if loop_field.get("type") == "multiselect":
                return
            raise DOCXBindingValidationError(
                f"Invalid condition on repeater row object {name!r} in {path_name}."
            )
        if name in data_fields:
            return
        raise DOCXBindingValidationError(
            f"DOCX condition references unknown variable {name!r}. "
            f"Declared fields: {sorted(data_fields.keys())}"
        )

    elif isinstance(expr, nodes.Getattr):
        if not isinstance(expr.node, nodes.Name):
            raise DOCXBindingValidationError(
                f"Chained or dynamic attribute access is not allowed in condition in {path_name}."
            )
        base_name = expr.node.name
        attr_name = expr.attr
        is_target, loop_field = scope.lookup_target(base_name)
        if is_target and loop_field is not None and loop_field.get("type") == "repeater":
            child_ids = {c["id"] for c in loop_field.get("fields", []) if c.get("type") != "info"}
            if attr_name not in child_ids:
                raise DOCXBindingValidationError(
                    f"DOCX condition references unknown child field {attr_name!r} on repeater {loop_field['id']!r}. "
                    f"Declared child fields: {sorted(child_ids)}"
                )
            return
        raise DOCXBindingValidationError(
            f"Attribute access on variable {base_name!r} is not allowed in condition in {path_name}."
        )

    elif isinstance(expr, nodes.Not):
        _validate_condition_expr(expr.node, scope, data_fields, path_name)

    elif isinstance(expr, (nodes.And, nodes.Or)):
        _validate_condition_expr(expr.left, scope, data_fields, path_name)
        _validate_condition_expr(expr.right, scope, data_fields, path_name)

    elif isinstance(expr, nodes.Compare):
        _validate_condition_expr(expr.expr, scope, data_fields, path_name)
        for op in expr.ops:
            if op.op not in ALLOWED_COMPARISON_OPS:
                raise DOCXBindingValidationError(
                    f"Unsupported comparison operator {op.op!r} in {path_name}. "
                    f"Only equality (==, !=) and membership (in, not in) are allowed."
                )
            if op.op in ("eq", "ne"):
                if isinstance(op.expr, nodes.Const):
                    pass
                else:
                    _validate_condition_expr(op.expr, scope, data_fields, path_name)
            elif op.op in ("in", "notin"):
                if isinstance(op.expr, (nodes.List, nodes.Tuple)):
                    for item in op.expr.items:
                        if not isinstance(item, nodes.Const):
                            raise DOCXBindingValidationError(
                                f"Elements in comparison collection must be literal constants in {path_name}."
                            )
                else:
                    _validate_condition_expr(op.expr, scope, data_fields, path_name)

    elif isinstance(expr, nodes.Const):
        pass

    else:
        raise DOCXBindingValidationError(
            f"Unsupported condition construct {type(expr).__name__} in {path_name}."
        )
