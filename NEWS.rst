=============
Version 0.1.3
=============
* Fixed bug in date adustment from edit window (#16).
* Improved formatting of activities in overview (#18).

=============
Version 0.1.2
=============

* Moved towards Gtk.Application structure.
* Added docs pages for https://geraldjansen.github.io/hamster-lite/.
* Tweaked some shortcut keys (notably Enter same as Ctrl-R)

=============
Version 0.1.0
=============

* Forked from https://projecthamster/hamster between v2.2.2 and v3.0
  and integrated most changes merged for v3.0.
* Removed DBus support and dependency (i.e. no more inter-application
  communication except through hamster-lite CLI).
* Simplified Storage object, limiting it sqlite3 DB backend.
* Added simple json config file and removed gconf dependency.
* Removed translations of help pages (mostly outdated).

See  https://github.com/projecthamster/hamster/blob/0a23d68e/NEWS for
older history.
