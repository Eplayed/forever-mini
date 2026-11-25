# -*- coding: utf-8 -*-
"""Shared Lua table-literal parser and snapshot helpers for Forever addon extractors."""
import datetime
import hashlib
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(WEB, "app", "data", "upstream")


def toc_version(src, addon, toc_name=None):
    """Read ## Version: from an addon .toc file."""
    path = os.path.join(src, addon, toc_name or (addon + ".toc"))
    if not os.path.isfile(path):
        return "版本未记"
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            m = re.match(r"\s*##\s*Version:\s*(.+)", line)
            if m:
                return m.group(1).strip()
    return "版本未记"


def file_stamp(path):
    """Return byte size, sha256, and mtime date for a source file."""
    with open(path, "rb") as f:
        data = f.read()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "fileDate": datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d"),
    }


def assert_no_percent(obj, label):
    """Red-line guard: drop rates / percentages must never appear in extracted snapshots."""
    hits = re.findall(r"\d+%", json.dumps(obj, ensure_ascii=False))
    if hits:
        sys.exit("%s 含百分比字样（触犯红线）：%s" % (label, hits[:5]))


def write_snapshot(out_dir, filename, doc):
    """Write formatted UTF-8 JSON snapshot and return its path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return path


class LuaParser:
    """Minimal recursive-descent parser for static Lua table literals (with optional L[...] lookup)."""

    def __init__(self, text, start=0, locale=None):
        self.s = text
        self.n = len(text)
        self.i = start
        self.locale = locale or {}

    def skip_ws(self):
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif s.startswith("--[[", self.i):
                end = s.find("]]", self.i + 4)
                self.i = (end + 2) if end != -1 else n
            elif s.startswith("--", self.i):
                nl = s.find("\n", self.i + 2)
                self.i = (nl + 1) if nl != -1 else n
            else:
                break

    def read_string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while self.i < self.n:
            c = self.s[self.i]
            if c == "\\":
                self.i += 1
                if self.i < self.n:
                    esc = self.s[self.i]
                    out.append({"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'"}.get(esc, esc))
                    self.i += 1
            elif c == q:
                self.i += 1
                return "".join(out)
            else:
                out.append(c)
                self.i += 1
        raise ValueError("Unterminated string at %d" % self.i)

    def read_number(self):
        m = re.match(r"-?(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", self.s[self.i:])
        if not m:
            raise ValueError("Invalid number near %r" % self.s[self.i:self.i + 20])
        tok = m.group(0)
        self.i += len(tok)
        if tok.startswith(("0x", "-0x")):
            return int(tok, 16)
        return float(tok) if ("." in tok or "e" in tok or "E" in tok) else int(tok)

    def read_ident(self):
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", self.s[self.i:])
        if not m:
            raise ValueError("Expected identifier near %r" % self.s[self.i:self.i + 20])
        self.i += len(m.group(0))
        return m.group(0)

    def parse_value(self):
        self.skip_ws()
        c = self.s[self.i]
        if c == "{":
            return self.parse_table()
        if c in "\"'":
            return self.read_string()
        if c == "-" or c.isdigit():
            return self.read_number()
        if self.s.startswith("L[", self.i):
            self.i += 2
            self.skip_ws()
            key = self.read_string()
            self.skip_ws()
            if self.s[self.i] != "]":
                raise ValueError("Expected ']' after L[...] near %r" % self.s[self.i:self.i + 20])
            self.i += 1
            return self.locale.get(key, key)
        ident = self.read_ident()
        if ident == "true":
            return True
        if ident == "false":
            return False
        if ident == "nil":
            return None
        return ident

    def parse_table(self):
        assert self.s[self.i] == "{"
        self.i += 1
        arr, obj = [], {}
        is_dict = False
        while True:
            self.skip_ws()
            if self.i >= self.n:
                raise ValueError("Unterminated table")
            if self.s[self.i] == "}":
                self.i += 1
                break
            c = self.s[self.i]
            if c == "[":
                if not is_dict:
                    is_dict = True
                    obj = {i + 1: v for i, v in enumerate(arr)}
                self.i += 1
                key = self.parse_value()
                self.skip_ws()
                if self.s[self.i] != "]":
                    raise ValueError("Expected ']' at %d" % self.i)
                self.i += 1
                self.skip_ws()
                if self.s[self.i] != "=":
                    raise ValueError("Expected '=' at %d" % self.i)
                self.i += 1
                obj[key] = self.parse_value()
            else:
                m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*", self.s[self.i:])
                if m and not self.s.startswith(("L[", "true", "false", "nil"), self.i):
                    if not is_dict:
                        is_dict = True
                        obj = {i + 1: v for i, v in enumerate(arr)}
                    self.i += m.end()
                    obj[m.group(1)] = self.parse_value()
                else:
                    val = self.parse_value()
                    if is_dict:
                        obj[len(obj) + 1] = val
                    else:
                        arr.append(val)
            self.skip_ws()
            if self.i < self.n and self.s[self.i] in ",;":
                self.i += 1
        return obj if is_dict else arr


def parse_assignment(text, marker_regex, locale=None):
    """Find `marker_regex` followed by `{ ... }` and parse the Lua table literal."""
    m = re.search(marker_regex, text)
    if not m:
        raise ValueError("找不到标记：%s" % marker_regex)
    idx = text.index("{", m.start())
    return LuaParser(text, idx, locale=locale).parse_table()
