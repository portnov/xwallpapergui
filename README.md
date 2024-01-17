xwallpapergui README
====================

`xwallpapergui` is a GUI for
[xwallpaper](https://github.com/stoeckmann/xwallpaper) utility, aimed to
simplify management of wallpapers in multimonitor setups.

![Screenshot_20240117_182149-1](https://github.com/portnov/xwallpapergui/assets/284644/0340f57f-6742-4ff9-8ac1-9ba616c9e29f)

It is intended for the following usecases:

* You use a laptop as a workstation, and sometimes you want to use laptop's
  monitor together with big external monitors, sometimes not.
* Sometimes you work at office and use external monitor, sometimes you work who
  knows where and use laptop's monitor.
* You go to different places with your laptop, plugging it to different sets of
  monitors. For example, at home you have only one external monitor, so in
  addition to it you enable laptop's monitor, in office you have two big
  external monitors and do not need laptop's monitor, in meeting room you work
  with laptop's monitor and plug a projector.
* You want to use one configuration (set of dotfiles in your `~/.config`) at
  several computers with different monitors.

In such situations, it becomes obvious that the set of wallpapers that you want
to see on your monitors depends on which exactly monitors you use and how are
they positioned. For example, in one place you have one monitor to the right of
another, and in another place you have one monitor on top of another. In one
case you may want to see a panorama landscape, in another the Eifel tower.

`xwallpapergui` uses the notion of "configuration", which is exactly the set of
currently enabled monitors and their positions. One of configurations is used
at each time, others just exist for later usage.

All configurations are stored in `~/.config/xwallpapergui/xwallpapergui.conf`
file.

Assumptions and limitations
---------------------------

As it was mentioned, `xwallpapergui` is using the `xwallpaper` utility. That
utility is not all-powerful. For example, it can not work in environments which
create a special window underneath all other windows, to handle clicks on
desktop, show desktop icons and manage wallpapers themeselves. Among such
environments are Gnome, KDE/Plasma, LXQt and so on.

Usage
-----

If you simply launch `xwallpapergui.py`, it will show a GUI window, allowing
you to see existing configurations and edit them.
At the top of window, there is a combobox showing all existing configurations.
Currently used configuration is marked with `[*]` sign.
It is possible to give more meaningful name to configuration by use of "Rename"
button.

When you launch `xwallpapergui` the first time, or the first time with this
specific set of monitors, it will automatically create a new configuration and
allow to edit it.

In the middle it shows all displays that exist in the selected configuration,
positioned according to xrandr settings. Each screen shows a preview of
wallpaper you configured for it (or just a green rectangle if the wallpaper was
not configured yet).

When you select a screen with mouse click, the details about selected screen
are displayed in the lower part of the window.

You can specify a wallpaper for specific screen in several ways:

* Select the screen by clicking on it's rectangle, and then press the "Browse"
  button below. Standard "Open file" dialog will appear.
* Double-click the screen rectangle. The same "Open file" dialog will appear.
* Drag-n-drop the wallpaper file from another application (file manager, for
  example) onto screen rectangle.

Press "Apply" button to set the wallpapers from selected configuration.

`xwallpapergui` also has simple command-line interface:

```
$ xwallpapergui.py list
```

will print the list of all existing configurations and details about them.

```
$ xwallpapergui.py apply
```

will automatically detect the configuration which should be used with currently
enabled monitors, and apply wallpapers from that configuration. You may wish to
configure your desktop environment to automatically launch this command every
time a monitor is plugged or unplugged.

Prerequisites
-------------

* Python 3.8+
* PyQt5
* `xwallpaper`

License
-------

GPL-3, see LICENSE.

