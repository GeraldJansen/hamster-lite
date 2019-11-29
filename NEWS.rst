======================
Hamster-lite Changelog
======================

Version 0.2.0 WIP
=================
* Switched to Gtk.Application with overview as the MainWindow and
  others as modal dialogs (blocking the main window)
* Removed help pages and added link to online documentation instead
* Restored About dialog
* Added preference setting 'escape_quits_main' (config file only)
* Removed (unused) integration code for task list (GTG, etc.)


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
