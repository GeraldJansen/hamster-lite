# Hamster - The Gnome Time Tracker

Hamster is time tracking for individuals. It helps you to keep track of how
much time you have spent during the day on activities you choose to track.

Some additional information is available in the
[wiki](https://github.com/projecthamster/hamster/wiki)
and a static copy of the user documentation is online
[here](https://geraldjansen.github.io/hamster-doc/).

During the period 2015-2017 there was a major effort to
[rewrite hamster](https://github.com/projecthamster/hamster-gtk)
(repositories: `hamster-lib/dbus/cli/gtk`).
Unfortunately, after considerable initial progress the work has remained in alpha state
for some time now. Hopefully the effort will be renewed in the future.

In the meantime, this sub-project aims to revive development of the "legacy" Hamster
code base, maintaining database compatibility with the widely installed
[v1.04](https://github.com/projecthamster/hamster/releases/tag/hamster-time-tracker-1.04),
but migrating to `Gtk3` and `python3`. This will allow package maintainers to provide
new packages for recent releases of mainstream Linux distributions for which the old
1.04-based versions are no longer provided.

With respect to 1.04, some of the GUI ease of use has been lost, especially for handling
tags, and the stats display is minimal now. So if you are happy with your hamster
application and it is still available for your distribution, upgrade is not recommended
yet.

In the meantime recent (v2.2+) releases have good backward data compatibility and are
reasonably usable. The aim is to provide a new stable v3.0 release in the coming
months (i.e. late 2019).


## Installation

You can use the usually stable `master` or [download stable releases](https://github.com/projecthamster/hamster/releases).

If you upgraded from an existing installation make sure to kill the running
daemons:

```bash
pkill -f hamster-service
pkill -f hamster-windows-service
# check (should be empty)
pgrep -af hamster
```

#### Dependencies


##### Debian-based

ubuntu (tested in 19.04 and 18.04):
```bash
sudo apt install gettext intltool gconf2 gir1.2-gconf-2.0 python3-gi-cairo
sudo apt install gnome-doc-utils yelp
```


##### openSUSE

Leap-15.0 and Leap-15.1:
```bash
sudo zypper install intltool python3-pyxdg python3-cairo python3-gobject-Gdk
sudo zypper install gnome-doc-utils xml2po yelp
```

##### RPM-based

*RPM-based instructions below should be updated for python3 (issue [#369](https://github.com/projecthamster/hamster/issues/369)).*

`yum install gettext intltool gnome-python2-gconf dbus-python`

If the hamster help pages are not accessible ("unable to open `help:hamster-time-tracker`"),
then a [Mallard](https://en.wikipedia.org/wiki/Mallard_(documentation))-capable help reader is required,
such as [yelp](https://wiki.gnome.org/Apps/Yelp/).


#### Trying the development version

To use the development version (backup `hamster.db` first !):
```
# either
pgrep -af hamster
# and kill them one by one
# or be bold and kill all process with "hamster" in their command line
pkill -ef hamster
src/hamster-service &
src/hamster-windows-service &
src/hamster-cli
```


#### Building and installing

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


#### Migrating from hamster-applet

Previously Hamster was installed everywhere under `hamster-applet`. As
the applet is long gone, the paths and file names have changed to
`hamster-time-tracker`. To clean up previous installs follow these steps:

```bash
git checkout d140d45f105d4ca07d4e33bcec1fae30143959fe
./waf configure build --prefix=/usr
sudo ./waf uninstall
```

## Contributing

1. [Fork](https://github.com/projecthamster/hamster/fork) this project
2. Create a topic branch - `git checkout -b my_branch`
3. Push to your branch - `git push origin my_branch`
4. Submit a [Pull Request](https://github.com/projecthamster/hamster/pulls) with your branch
5. That's it!

See [How to contribute](https://github.com/projecthamster/hamster/wiki/How-to-contribute) for more information.
