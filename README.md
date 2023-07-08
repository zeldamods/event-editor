## EventEditor for Breath of the Wild

### Setup

Install Python 3.6+ (**64 bit version**) and PyQt5, then run `pip install eventeditor`.

### Configuration

The configuration file is stored:

* On Linux or macOS: at `~/.config/eventeditor/eventeditor.ini`
* On Windows: at `%APPDATA%/eventeditor/eventeditor.ini`

### Auto-completion

#### Breath of the Wild

In order to enable auto-completion for actors, actions, and queries, add:

```ini
[paths]
rom_root=/path/to/game_rom
```

to EventEditor's configuration file, where `/path/to/game_rom` is a path such that
`/path/to/game_rom/Pack/Bootup.pack/Actor/AIDef/AIDef_Game.product.sbyml` exists.
An easy, recommended way to get the required file structure without extracting every archive
is to use [botwfstools](https://github.com/leoetlino/botwfstools).

#### Other games

Alternatively, JSON actor definitions can be generated under *Flowchart* > *Export actor definition data to JSON*. This will generate information for auto-completion from the currently open event flow. The first time this is run, a prompt will appear asking for where to save this information.

This action can be safely repeated in case other event flows contain actors, actions, or queries that have yet to be included in the JSON file (existing entries will not be overwritten).

### Known issues

* On Linux, if the main window view is a completely blank screen, even after opening a file, try running `QTWEBENGINE_DISABLE_SANDBOX=1 eventeditor` to start the tool.

* Unlinking events while in fork/join will break graph generation most of the time. So using that option is not recommended when fork/join events are involved.

### What needs to be done

* Timeline files (reverse engineering)

* Collect event info from EventInfo and have a metadata file for each event flow, so that:
    * EventInfo can be automatically regenerated
    * All copies of an event flow can be automatically updated

* Node order shuffling to get less crossings. This used to be a dagre.js feature but it got removed...

### License

This software is licensed under the terms of the GNU General Public License, version 2 or later.
