# Hamster-lite

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.

Hamster-lite is an experimental branch of them main
[Hamster Time Tracker] (https://github.com/projecthamster/hamster/wiki).
The sqlite3 database store remains fully interchangeable with the main branch.
In fact, on first start-up the Hamster DB is copied from
~/.local/share/hamster-applet/hamster.db if it exists. The hamster-lite DB is
normally ~/.local/share/hamster-lite/hamster-lite.db (depends on
xdg\_data_home).

User documentation for this version remains largely the same as that of
the main branch. A static copy is available online
[here](https://geraldjansen.github.io/hamster-doc/).

Some functionality of the main branch has been removed in hamster-lite in
order to achieve some code simplification. D-bus support has been removed,
meaning this version is not compatible with hamster-shell-extension. (Note
that an alternative extension -
[argos-hamster-plugin](https://github.com/matclab/argos-hamster-plugin) -
is compatible and can be adapted by substituting `hamster` by `hamster-lite`).
Extensibility of the backend storage to anything other than the sqlite3 DB
has also been removed.


## Installation

```
git clone --branch=hamster-lite git@github.com:GeraldJansen/hamster.git hamster-lite
```

#### Dependencies


##### Debian-based (tested in Ubuntu 19.04)

```bash
sudo apt install gettext intltool gconf2 gir1.2-gconf-2.0 python3-gi-cairo python3-distutils python3-dbus python3-xdg
```

##### other

Current (late 2019) dependencies for
[Hamster](https://github.com/projecthamster/hamster/blob/master/README.md)
should work.

#### Trying the development version

To use the development version (backup `hamster-lite.db` first !):

```
cd hamster-lite && ./hamster-lite
```

(Note there are no dbus daemons that need to be stopped or restarted as for the
main hamster version.)


#### Building and installing system wide

```bash
./waf configure build
# thanks to the parentheses the umask of your shell will not be changed
( umask 0022 && sudo ./waf install; )
```
The `umask 0022` is safe for all, but important for users with more restrictive umask,
as discussed [here](https://github.com/projecthamster/hamster/pull/421#issuecomment-520167143).

Now restart your panels/docks and you should be able to add Hamster!


#### Uninstall

```bash
./waf configure
sudo ./waf uninstall
```


## Contributing

1. [Fork](https://github.com/GeraldJansen/hamster/fork) this project
   and use the GitHub project settings to make hamster-lite the main branch
2. Clone your fork locally -
   `git clone --branch=hamster-lite git@github.com:yourname/hamster.git hamster-lite`
3. Always start from the hamster-lite branch - `git checkout hamster-lite`
4. Create a topic branch - `git checkout -b my_branch`
5. Push to your branch - `git push origin my_branch`
6. Submit a [Pull Request](https://github.com/projecthamster/hamster/pulls) with your branch
That's it!

See [How to contribute](https://github.com/projecthamster/hamster/wiki/How-to-contribute)
for related information (some adaptation needed).
