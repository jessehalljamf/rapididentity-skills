#!/usr/bin/env python3
"""Semantic-ish diff between two Connect action-set XML bodies.

Strips signals that are *expected* to differ between two copies of the same
action set without representing a real content change - the `about` section's
`Author:` / `Last Modified by:` / `Version:` comment lines, and the root
`actionDef` element's platform-maintained metadata attributes - then
pretty-prints both trees and prints a unified diff of what's left.

An empty diff means the two copies are identical in substance, regardless of
what their Author/Version/modifiedMs metadata claims. A non-empty diff means
the `about` section's `Version:` line can't be trusted for at least one copy
(see "Determining Which Copy Is Newer" in SKILL.md) - it shows exactly what
changed instead of dumping two walls of minified XML.

Usage:
    python3 compare_action_sets.py FILE_A FILE_B

Exit codes: 0 = no substantive differences, 1 = differences found, 2 = error.
Requires Python 3.9+ (uses xml.etree.ElementTree.indent).
"""

import difflib
import sys
import xml.etree.ElementTree as ET

ET.register_namespace("", "urn:idauto.net:dss:actiondef")

VOLATILE_ROOT_ATTRS = {
    "modifiedMs",
    "modifiedBy",
    "modifiedByName",
    "version",
    "changeCount",
}
VOLATILE_COMMENT_PREFIXES = ("Author:", "Last Modified by:", "Version:")


def strip_volatile(root: ET.Element) -> None:
    for elem in root.iter():
        if elem.tag.endswith("actionDef"):
            for attr in VOLATILE_ROOT_ATTRS:
                elem.attrib.pop(attr, None)
        elif elem.tag.endswith("arg") and elem.get("name") == "comment":
            value = elem.get("value") or ""
            if value.startswith(VOLATILE_COMMENT_PREFIXES):
                label = value.split(":", 1)[0]
                elem.set("value", f"{label}: <stripped for comparison>")


def load(path: str) -> ET.Element:
    root = ET.parse(path).getroot()
    strip_volatile(root)
    return root


def render(root: ET.Element) -> list:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode").splitlines(keepends=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_action_sets.py FILE_A FILE_B", file=sys.stderr)
        return 2
    a_path, b_path = sys.argv[1], sys.argv[2]
    try:
        a_lines = render(load(a_path))
        b_lines = render(load(b_path))
    except (ET.ParseError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    diff = list(
        difflib.unified_diff(a_lines, b_lines, fromfile=a_path, tofile=b_path)
    )
    if not diff:
        print(
            "No substantive differences (ignoring Author/Last Modified by/Version "
            "and platform metadata)."
        )
        return 0
    sys.stdout.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
