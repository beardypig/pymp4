# pymp4
Python MP4 box parser and toolkit

# Usage

`pymp4` is based on the excellent parsing library [construct](https://github.com/construct/construct).

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

# Upgrade to Construct 2.10

The current master of pymp4 is based on construct v2.8.8. This is an old
version (years ago): it does not have a public doc page, several improvements
have been introduced and the general consensus seems to point to an upgrade.

Unfortunately several breaking changes have been introduced, making the
transition harder. Construct's doc does not help very much either.

This is a first attempt at building pymp4 based on construct v 2.10.60. There
have been no attempts to parse an actual mp4 file with it, this is just a first
pass to understand the implications of this migration.

The most important impacts seems to be:

- changed all String classes to PaddedString
- using new argument order for Const
- replaced custom "Prefixedincludedsize" class with the new "Prefixed" one,
  supporting the case where length field accounts for its own length
- adjusted offsets/end field calculation based on the different way the
  Prefixed class work
- getting rid of all "Embedded" structs (entirely deprecated and removed from
  construct 2.10), in favour of "named", nested structs.

All tests are passing, but no effort has been made for the moment to make sure
all applied changes are covered.

The most impacting change is the removal of "Embedded". The change makes it
harder to use the "Box" structure and introduces an additional "box_body"
field that seems somehow unnecessary and artificial with respect to what
obtained by using "Embedded". This becomes quickly annoying especially when
trying to build or parse boxes with more than a few levels of nesting (have
a look at how the code in "test_moov_build" changes).

It is possible that "Box" and "ContainerBox" can be redesigned, improving
usability.

Defects / Next steps:

- some constructs use binary string, other handle standard python (unicode)
  strings for essentially the same fields. An effort should be made if possible
  to be allow a more coherent usage.
- add new tests to cover all applied changes

## Test

Just run ```make``` to build a virtual env and run tests.
