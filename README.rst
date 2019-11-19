Hamster-lite
============

**Work in Progress**

Hamster is a personal time tracking tool. It helps you to keep track of
how much time you have spent during the day on activities you choose to
track.

Hamster-lite is an experimental fork of the main `Hamster Time
Tracker <https://github.com/projecthamster/hamster/wiki>`__. The sqlite3
database store remains fully interchangeable. In fact, on first start-up
the Hamster DB is copied from hamster-time-tracker (or older
hamster-applet) in ~/.local/share if it exists. The hamster-lite DB is
normally ~/.local/share/hamster-lite/hamster-lite.db (depends on
xdg_data_home).

User documentation for this version remains largely the same as that of
the main Hamster application. A static copy is available online
`here <https://geraldjansen.github.io/hamster-doc/>`__.

Some functionality has been removed in hamster-lite in order to achieve
some code simplification. D-bus support has been removed, meaning this
version is not compatible with hamster-shell-extension. (Note that an
alternative extension -
`argos-hamster-plugin <https://github.com/matclab/argos-hamster-plugin>`__
- is compatible and can be adapted by substituting ``hamster`` by
``hamster-lite``). Extensibility of the backend storage to anything
other than the sqlite3 DB has also been removed. Configuration data is
stored in a json file (i.e. no gconf/dconf dependency).

Installation
------------

::

   git clone git@github.com:GeraldJansen/hamster-lite.git

Dependencies
~~~~~~~~~~~~

Debian-based (tested in Ubuntu 19.04)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: bash

   sudo apt install gettext intltool python3-gi-cairo python3-distutils python3-xdg

Other
^^^^^

Current (late 2019) dependencies for
`Hamster <https://github.com/projecthamster/hamster/blob/master/README.md>`__
should work, keeping in mind that the dbus and gconf dependencies are no
longer needed.

Trying the development version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the development version (backup ``hamster-lite.db`` first !):

::

   cd hamster-lite && ./hamster-lite  (or ./hamster-lite --help)

(Note there are no dbus daemons that need to be stopped or restarted as
for the main Hamster version.)

Building and installing system wide
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   ./waf configure build
   # thanks to the parentheses the umask of your shell will not be changed
   ( umask 0022 && sudo ./waf install; )

Now restart your panels/docks and you should be able to add Hamster!

Uninstall
~~~~~~~~~

.. code:: bash

   ./waf configure
   sudo ./waf uninstall

Contributing
------------

1. `Fork <https://github.com/GeraldJansen/hamster-lite/fork>`__ this
   project and use the GitHub project settings to make hamster-lite the
   main branch
2. Clone your fork locally -
   ``git clone git@github.com:yourname/hamster-lite.git``
3. Create a topic branch - ``git checkout -b my_branch``
4. Push to your branch - ``git push origin my_branch``
5. Submit a `Pull
   Request <https://github.com/GeraldJansen/hamster-lite/pulls>`__ with
   your branch That’s it!

See `How to
contribute <https://github.com/projecthamster/hamster/wiki/How-to-contribute>`__
for related information (some adaptation needed).
