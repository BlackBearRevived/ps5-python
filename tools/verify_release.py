#!/usr/bin/env python3
# PS5-Python - Verify generated release artifacts.
# Copyright (C) 2026 BlackBearReloaded
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
from pathlib import Path, PurePosixPath
import struct
import sys
import tarfile


def verify_elf(artifact, name):
    if len(artifact) < 64 or artifact[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError(f"{name} is not a 64-bit little-endian ELF")
    elf_type, machine, version, entry, ph_offset = struct.unpack_from("<HHIQQ", artifact, 16)
    ph_size, ph_count = struct.unpack_from("<HH", artifact, 54)
    if elf_type not in (2, 3) or machine != 62 or version != 1:
        raise ValueError(f"{name} is not an x86-64 executable ELF")

    program_header = struct.Struct("<IIQQQQQQ")
    ph_end = ph_offset + ph_size * ph_count
    if ph_offset < 64 or ph_size != program_header.size or ph_end > len(artifact):
        raise ValueError(f"{name} has an invalid ELF program header table")
    for kind, flags, offset, address, _, file_size, memory_size, _ in program_header.iter_unpack(
        memoryview(artifact)[ph_offset:ph_end]
    ):
        if (
            kind == 1
            and flags & 1
            and file_size <= memory_size
            and offset + file_size <= len(artifact)
            and address <= entry < address + file_size
        ):
            return
    raise ValueError(f"{name} has no executable load segment containing its entry point")


def verify(directory, tag):
    prefix = f"python-ps5-{tag}"
    launchers = ("python.elf", "python-web.elf", "python-app-supervisor.elf")
    archive = directory / f"{prefix}.tar.gz"
    checksum = directory / f"{prefix}-SHA256SUMS"
    artifacts = {archive.name, *(f"{prefix}-{name}" for name in launchers)}
    if {p.name for p in directory.iterdir()} != artifacts | {checksum.name}:
        raise ValueError("Unexpected release file list")
    lines = checksum.read_text(encoding="ascii").splitlines()
    expected = dict(line.split("  ", maxsplit=1)[::-1] for line in lines)
    if len(lines) != len(artifacts) or set(expected) != artifacts:
        raise ValueError("Checksum manifest does not cover exactly the released artifacts")
    for name, digest in expected.items():
        with (directory / name).open("rb") as binary:
            if hashlib.file_digest(binary, "sha256").hexdigest() != digest:
                raise ValueError(f"Checksum mismatch: {name}")

    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            if not path.parts or path.parts[0] != prefix or ".." in path.parts:
                raise ValueError(f"Unexpected bundle path: {member.name}")
            if not member.isfile() and not member.isdir():
                raise ValueError(f"Unsupported bundle entry: {member.name}")
        files = {m.name for m in members if m.isfile()}
        for folder in ("runtime/cpython-lib", "web", "apps"):
            if not any(name.startswith(f"{prefix}/{folder}/") for name in files):
                raise ValueError(f"Missing bundle content: {folder}")
        for name in launchers:
            member = f"{prefix}/runtime/{name}"
            if member not in files:
                raise ValueError(f"Missing launcher: {member}")
            artifact = (directory / f"{prefix}-{name}").read_bytes()
            verify_elf(artifact, name)
            with bundle.extractfile(member) as payload:
                if payload.read() != artifact:
                    raise ValueError(f"Bundled and standalone forms of {name} differ")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: verify_release.py ARTIFACT_DIRECTORY TAG")
    verify(Path(sys.argv[1]), sys.argv[2])
    print("Verified release checksums, runtime bundle layout, and three x86-64 launchers.")
