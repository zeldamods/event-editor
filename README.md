## EventEditor for Breath of the Wild

### Known issues

* Unlinking events while in fork/join will break graph generation most of the time. So using that option is not recommended when fork/join events are involved.

* It's quite... buggy.

### What needs to be done

* Timeline files (reverse engineering)

* Collect event info from EventInfo and have a metadata file for each event flow, so that:
    * EventInfo can be automatically regenerated
    * All copies of an event flow can be automatically updated

* Reading valid actor actions and queries from aiprogs
    * An AAMP library will need to be written or adapted from aamptool.
    * For special 'actors' such as AutoPlacement and TipsSystemActor, use hardcoded action/query lists.
    * Read parameters from AI definitions

* Node order shuffling to get less crossings. This used to be a dagre.js feature but it got removed...

### License

This software is licensed under the terms of the GNU General Public License, version 2 or later.
