#!/usr/bin/env python3
"""Checks the version header, markers and Appendix E of the Atsign Protocol
specification against each other.

Usage: check_spec_versions.py <specification.md>

Exits 1, printing one line per problem, when:
- the line under the title is not the header, there is more than one header,
  or the header does not name the newest production block, or its tag link or
  date differs from that block's;
- a "Since atServer X.Y.Z" or "Unreleased" marker, or any link to a block,
  names a block that does not exist or text that does not match its anchor,
  or a "Since atServer" marker outside a code block is not a link;
- an Appendix E heading is not a block heading, a production block lacks its
  release line or a calendar date, or the blocks are not newest first with
  Unreleased at the top.
"""

import datetime
import re
import sys

APPENDIX = '## Appendix E, Changes by atServer version'
RELEASES = re.escape('https://github.com/atsign-foundation/at_server/'
                     'releases/tag/')
VERSION = r'(\d+\.\d+\.\d+)'

HEADER = re.compile(
    r'\*\*This document describes atServer ' + VERSION + r'\*\* \(production'
    r' release \[p' + VERSION + r'\]\(' + RELEASES + r'p' + VERSION
    + r'\), ([^)]*)\)\.')
BLOCK_HEADING = re.compile(r'^### (?:atServer ' + VERSION + r'|(Unreleased))$')
RELEASE_LINE = re.compile(
    r'^Production release \[p' + VERSION + r'\]\(' + RELEASES + r'p'
    + VERSION + r'\),(?: (\d{4}-\d{2}-\d{2})\.)?')
LINKED_SINCE = re.compile(
    r'[Ss]ince\s+atServer\s+\[' + VERSION + r'\]\(#([^)\s]*)\)')
PLAIN_SINCE = re.compile(r'[Ss]ince\s+atServer\s+' + VERSION)
UNRELEASED_MARKER = re.compile(
    r'\[(?:Unreleased|Removed, unreleased)\]\(#([^)\s]*)\)')
BLOCK_LINK = re.compile(r'\[([^\]]*)\]\(#(atserver-\d+|unreleased)\)')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')


def anchor(version):
    """The GitHub anchor of the block heading for [version]."""
    return 'atserver-' + version.replace('.', '')


def key(version):
    return tuple(int(part) for part in version.split('.'))


def prose_flags(lines):
    """For each line, whether it is prose: outside fenced code blocks and
    not a fence itself."""
    flags, fence = [], None
    for line in lines:
        opening = FENCE.match(line)
        if fence is None and opening:
            fence = opening.group(1)
            flags.append(False)
        elif fence is not None:
            if opening and opening.group(1)[0] == fence[0] \
                    and len(opening.group(1)) >= len(fence) \
                    and not line.strip()[len(opening.group(1)):].strip():
                fence = None
            flags.append(False)
        else:
            flags.append(True)
    return flags


def paragraph(lines, start):
    """The paragraph that starts at or after [start], its lines joined by
    spaces."""
    i = start
    while i < len(lines) and not lines[i].strip():
        i += 1
    joined = []
    while i < len(lines) and lines[i].strip():
        joined.append(lines[i].strip())
        i += 1
    return ' '.join(joined)


def blocks(lines):
    """The Appendix E blocks in order, as (version, or None for Unreleased,
    line number, first paragraph after the heading), and the line numbers of
    headings that are not block headings; None when there is no Appendix
    E."""
    try:
        start = lines.index(APPENDIX)
    except ValueError:
        return None
    found, stray = [], []
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('## '):
            break
        if lines[i].startswith('#'):
            heading = BLOCK_HEADING.match(lines[i])
            if heading:
                found.append((heading.group(1), i + 1, paragraph(lines, i + 1)))
            else:
                stray.append(i + 1)
    return found, stray


def check_blocks(found, stray):
    """Problems with the blocks themselves, and each production block's
    date."""
    problems, dates = [], {}
    for number in stray:
        problems.append(f'line {number}: an Appendix E heading that is not'
                        ' "### atServer X.Y.Z" or "### Unreleased"')
    if not found or found[0][0] is not None:
        problems.append('Appendix E does not open with an "### Unreleased"'
                        ' block')
    for version, number, _ in found[1:]:
        if version is None:
            problems.append(f'line {number}: an Unreleased block that is not'
                            ' at the top of Appendix E')

    production = [(v, n, first) for v, n, first in found if v is not None]
    for version, number, first in production:
        release = RELEASE_LINE.match(first)
        if not release:
            problems.append(f'line {number}: block atServer {version} does'
                            ' not start "Production release [pX.Y.Z](...),'
                            ' YYYY-MM-DD."')
        elif release.group(1) != version or release.group(2) != version:
            problems.append(f'line {number}: block atServer {version} links'
                            f' release p{release.group(1)}')
        elif release.group(3) is None:
            problems.append(f'line {number}: block atServer {version} has no'
                            ' date')
        else:
            try:
                datetime.date.fromisoformat(release.group(3))
                dates[version] = release.group(3)
            except ValueError:
                problems.append(f'line {number}: block atServer {version} is'
                                f' dated {release.group(3)}, which is not a'
                                ' calendar date')

    for (newer, number, _), (older, _, _) in zip(production, production[1:]):
        if key(newer) <= key(older):
            problems.append(f'line {number}: block atServer {newer} is not'
                            f' newer than the block after it, {older}')
        elif newer in dates and older in dates and dates[newer] < dates[older]:
            problems.append(f'line {number}: block atServer {newer} is dated'
                            f' {dates[newer]}, before {older}\'s'
                            f' {dates[older]}')
    return problems, dates


def check_header(lines, flags, newest, dates):
    title = next((i for i, line in enumerate(lines)
                  if line.startswith('# ')), None)
    first = None
    if title is not None:
        first = next((i for i in range(title + 1, len(lines))
                      if lines[i].strip()
                      and not lines[i].lstrip().startswith('<!--')), None)
    header = HEADER.match(paragraph(lines, first)) if first is not None \
        else None
    if not header:
        return ['the line under the title is not "**This document describes'
                ' atServer X.Y.Z** (production release [pX.Y.Z](...),'
                ' date)."']
    problems = []
    prose = ' '.join(line for line, kept in zip(lines, flags) if kept)
    if len(HEADER.findall(re.sub(r'\s+', ' ', prose))) > 1:
        problems.append('more than one "This document describes atServer"'
                        ' header')
    described, linked, target, date = header.groups()
    if described != newest:
        problems.append(f'the header describes atServer {described}, but the'
                        f' newest production block is {newest}')
    if linked != described or target != described:
        problems.append(f'the header describes atServer {described} but'
                        f' links p{linked} at p{target}')
    if described == newest and newest in dates and dates[newest] != date:
        problems.append(f'the header dates atServer {described} "{date}",'
                        f' but its block says {dates[newest]}')
    return problems


def check_markers(prose, code, anchors, versions):
    problems = []
    for since in LINKED_SINCE.finditer(prose):
        version, target = since.groups()
        if target != anchor(version):
            problems.append(f'"Since atServer {version}" links #{target},'
                            f' not #{anchor(version)}')
        elif target not in anchors:
            problems.append(f'"Since atServer {version}" links a block that'
                            ' does not exist')
    for since in PLAIN_SINCE.finditer(prose):
        problems.append(f'"Since atServer {since.group(1)}" outside a code'
                        ' block is not a link to its block')
    for marker in UNRELEASED_MARKER.finditer(prose):
        if marker.group(1) != 'unreleased' or 'unreleased' not in anchors:
            problems.append(f'an Unreleased marker links #{marker.group(1)},'
                            ' not an existing Unreleased block')
    rest = UNRELEASED_MARKER.sub('', LINKED_SINCE.sub('', prose))
    for link in BLOCK_LINK.finditer(rest):
        text, target = link.groups()
        named = re.fullmatch(r'(?:atServer\s+)?' + VERSION, text.strip())
        if target not in anchors:
            problems.append(f'a link to #{target} names a block that does'
                            ' not exist')
        elif named and anchor(named.group(1)) != target:
            problems.append(f'a link reading "{text}" goes to #{target}, not'
                            f' #{anchor(named.group(1))}')
    for since in PLAIN_SINCE.finditer(code):
        if since.group(1) not in versions:
            problems.append(f'"since atServer {since.group(1)}" in a code'
                            ' block names a version with no block')
    return problems


def check(text):
    """Every problem found in [text], a specification, as a line each."""
    lines = text.split('\n')
    appendix = blocks(lines)
    if appendix is None:
        return [f'no "{APPENDIX}" heading']
    found, stray = appendix
    problems, dates = check_blocks(found, stray)
    versions = [v for v, _, _ in found if v is not None]
    flags = prose_flags(lines)
    if versions:
        problems += check_header(lines, flags, versions[0], dates)
    anchors = {anchor(v) for v in versions}
    if found and found[0][0] is None:
        anchors.add('unreleased')
    prose = ' '.join(line for line, kept in zip(lines, flags) if kept)
    code = ' '.join(line for line, kept in zip(lines, flags)
                    if not kept and not FENCE.match(line))
    problems += check_markers(prose, code, anchors, set(versions))
    return problems


def main(argv):
    if len(argv) != 2:
        print('Usage: check_spec_versions.py <specification.md>',
              file=sys.stderr)
        return 2
    with open(argv[1], encoding='utf-8') as spec:
        problems = check(spec.read())
    for problem in problems:
        print(f'{argv[1]}: {problem}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
