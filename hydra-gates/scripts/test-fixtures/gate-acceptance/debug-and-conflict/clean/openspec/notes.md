Release
=======

A Markdown SETEXT H1 underline of exactly seven `=` characters is
byte-identical to git's conflict separator, and `^={7}$` matched it. This file
is the gate-21 near-miss: it must NOT be reported, because there is no
`<<<<<<< ` or `>>>>>>> ` anywhere in it.

Subheading
==========

A longer underline never matched and is here only so the discriminator is not
accidentally satisfied by length.
