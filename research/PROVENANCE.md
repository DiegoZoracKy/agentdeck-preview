# Historical artifact provenance

Research Records and reviewed reference artifacts preserve the observations and
metadata captured when they were produced. They are not rewritten to resemble a
new execution or a different machine.

Some historical artifacts already present in the public repository contain
absolute local paths and masked credential-related metadata. These paths describe
the original host; they are not portable inputs or instructions to access that
machine. Masked metadata is not an authentication credential. Reproduction uses
the documented Study sources and new external output directories.

The source update retains those historical bytes. If a future public presentation
needs less host metadata, it must be a separately identified projection with an
explicit relationship to its source, rather than a silent edit of a Record.

A bundled Record can also name an original source revision that is not reachable
from the public Git history. That field remains historical origin metadata; it
does not make the revision part of the current public release. Reference probes
pin their canonical Record bytes and Game implementation fingerprints. Fresh
execution writes new Records and identifies the environment actually used.

The Hidden Signal and Last Potion source locks are explicitly derived acceptance
artifacts. They leave historical probes, Records and snapshots intact. They check
the same authored sources across supported Python versions while retaining the
full environment-specific identities of new Research artifacts.
