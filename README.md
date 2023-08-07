# pymp4

[![Build status](https://github.com/beardypig/pymp4/actions/workflows/ci.yml/badge.svg)](https://github.com/beardypig/pymp4/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/pymp4)](LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/pymp4)](https://pypi.org/project/pymp4)
[![Coverage](https://codecov.io/gh/beardypig/pymp4/branch/master/graph/badge.svg)](https://app.codecov.io/github/beardypig/pymp4)

Python MP4 box parser and toolkit based on the [construct](https://github.com/construct/construct) library.

## Usage

```python
>>> from pymp4.parser import Box
>>> from io import BytesIO

>>> Box.build(dict(
    type=b"ftyp",
    major_brand="iso5",
    minor_version=1,
    compatible_brands=["iso5", "avc1"]))
b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1'

>>> ftyp = Box.parse(b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x01iso5avc1')
>>> print(ftyp)
Container:
    type = ftyp
    major_brand = iso5
    minor_version = 1
    compatible_brands = ListContainer:
        iso5
        avc1

```

## Contributors

<a href="https://github.com/beardypig"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/16033421?v=4&h=25&w=25&fit=cover&mask=circle&maxage=7d" alt=""/></a>
<a href="https://github.com/truedread"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/25360375?v=4&h=25&w=25&fit=cover&mask=circle&maxage=7d" alt=""/></a>
<a href="https://github.com/orca-eaa5a"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/28733566?v=4&h=25&w=25&fit=cover&mask=circle&maxage=7d" alt=""/></a>
<a href="https://github.com/rlaphoenix"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/17136956?v=4&h=25&w=25&fit=cover&mask=circle&maxage=7d" alt=""/></a>

## License

[Apache License, Version 2.0](LICENSE)
