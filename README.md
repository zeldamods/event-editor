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

Alternatively, add:

```ini
[paths]
actor_json_root=/path/to/folder
```
to the configuration file, where `/path/to/folder` is a path to a folder containing `.json` files named after each event actor.

This is intended for use where the rom option is not available, and requires manually crafted `.json` files. Currently the program provides some tools that can assist in the generation of these files:

0. Set the `actor_json_root` path in the configuration file
1. Open an existing event flow and switch to the *Actors* tab
2. Right-click on an actor > *Export JSON*
    - Save it in the folder specified in the configuration file
    - Do not change the filename, as it is used to find the actor when auto-completing
3. Right-click on an action/query to *Jump to events* that use it 
4. Right-click on an event > *Edit...* to view parameters and click *Copy JSON*
    - The parameter values used in the chosen event will be used as default values for auto-completion *(can be manually edited)*
5. Open the generated `.json` file and replace (paste) the copied action/query

##### Example JSON (formatted)
```json
// EventActor.json
{
    "actions": {
        "Talk": {
            "IsWaitFinish": false
        }
    },
    "queries": {
    }
}
```

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
