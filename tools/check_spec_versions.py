#!/usr/bin/env python3
"""Checks the version header, markers and Appendix E of the Atsign Protocol
specification against each other.

Usage: check_spec_versions.py <specification.md>

Exits 1, printing one line per problem, when:
- the header does not name the newest production block, or its tag link or
  date differs from that block's;
- a "Since atServer X.Y.Z" or "Unreleased" marker links to a block that does
  not exist, or a "Since atServer" marker outside a code block is not a link;
- a production block lacks its release line or date, or the blocks are not
  newest first with Unreleased at the top.
"""

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
BLOCK_LINK = re.compile(r'\]\(#(atserver-\d+|unreleased)\)')


def anchor(version):
    """The GitHub anchor of the block heading for [version]."""
    return 'atserver-' + version.replace('.', '')


def key(version):
    return tuple(int(part) for part in version.split('.'))


def split_code(lines):
    """The text outside fenced code blocks and the text inside them, each
    with its line breaks turned into spaces."""
    prose, code, fenced = [], [], False
    for line in lines:
        if line.lstrip().startswith('```'):
            fenced = not fenced
        elif fenced:
            code.append(line)
        else:
            prose.append(line)
    return ' '.join(prose), ' '.join(code)


def blocks(lines):
    """The Appendix E blocks in order, as (version, or None for Unreleased,
    line number, first non-blank line after the heading); None when there is
    no Appendix E."""
    try:
        start = lines.index(APPENDIX)
    except ValueError:
        return None
    found = []
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('## '):
            break
        heading = BLOCK_HEADING.match(lines[i])
        if heading:
            first = next((line for line in lines[i + 1:] if line.strip()), '')
            found.append((heading.group(1), i + 1, first))
    return found


def check_blocks(found):
    """Problems with the blocks themselves, and each production block's
    date."""
    problems, dates = [], {}
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
            dates[version] = release.group(3)

    for (newer, number, _), (older, _, _) in zip(production, production[1:]):
        if key(newer) <= key(older):
            problems.append(f'line {number}: block atServer {newer} is not'
                            f' newer than the block after it, {older}')
        elif newer in dates and older in dates and dates[newer] < dates[older]:
            problems.append(f'line {number}: block atServer {newer} is dated'
                            f' {dates[newer]}, before {older}\'s'
                            f' {dates[older]}')
    return problems, dates


def check_header(text, newest, dates):
    header = HEADER.search(re.sub(r'\s+', ' ', text))
    if not header:
        return ['no "**This document describes atServer X.Y.Z** (production'
                ' release [pX.Y.Z](...), date)." header']
    described, linked, target, date = header.groups()
    problems = []
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
        if link.group(1) not in anchors:
            problems.append(f'a link to #{link.group(1)} names a block that'
                            ' does not exist')
    for since in PLAIN_SINCE.finditer(code):
        if since.group(1) not in versions:
            problems.append(f'"since atServer {since.group(1)}" in a code'
                            ' block names a version with no block')
    return problems


def check(text):
    """Every problem found in [text], a specification, as a line each."""
    lines = text.split('\n')
    found = blocks(lines)
    if found is None:
        return [f'no "{APPENDIX}" heading']
    problems, dates = check_blocks(found)
    versions = [v for v, _, _ in found if v is not None]
    if versions:
        problems += check_header(text, versions[0], dates)
    anchors = {anchor(v) for v in versions}
    if found and found[0][0] is None:
        anchors.add('unreleased')
    prose, code = split_code(lines)
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
