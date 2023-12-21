# card-production

<!--
Copyright 2023, Collabora, Ltd.

SPDX-License-Identifier: CC-BY-4.0
-->

Some Python tools to help in a small scall smartcard production workflow.

Maintained at <https://github.com/rpavlik/card-production>

## Introduction

This is mainly for internal use so documentation is limited. However, from my
experience researching this process, even scripts with minimal documentation are
valuable since most of the smartcard ecosystem seems focused on enterprises with
1000+ card deployments. This is definitely **not for that purpose**. This is for
"I bought a handful of blank Java Cards and want to use them as mini hardware
security modules, instead of being tied to the limited capabilities and
sole-sourced YubiKey 5 or having to go all the way to an enterprise HSM."

## Dependencies

- Python modules:
  - `dataclasses-json`
  - `click` v7+
  - `toml` (not the 3.11-bundled `tomllib`)
- Java JRE: Needed for `gp`.
- A card reader and associated software so that java and OpenSC can both see it.
- [GlobalPlatformPro][] aka `gp` - Place `gp.jar` in this directory. The script does
  actually know other ways to invoke it, but they aren't exposed to the config
  files.
- [GidsApplet][] - Right now this is my favorite applet for general use so it's
  the first one supported. Place the `.cap` file in this directory: see
  [`cardproduction/gids.py`](cardproduction/gids.py) for the filename it looks
  for. You got it: that's not exposed to the config files yet either.
  - I am probably using a build from my fork, but...

[GlobalPlatformPro]: https://github.com/martinpaljak/GlobalPlatformPro
[GidsApplet]: https://github.com/vletoux/GidsApplet

To get everything except `gp` and the applet itself, as least for my machine and
card reader:

```sh
sudo apt install python3-dataclasses-json python3-click python3-toml \
     default-jre-headless opensc pcscd libccid
```

I'm using blank J3R180 cards for most of this, but nothing in this repo requires
or depends on any particular card details beyond "GlobalPlatform supported"
which is basically all blank Java Cards that I can find.

## File types

- GP parameter file: TOML file with one value, stores the ISD key used by the gp
  tool to be able to install/remove/etc applets. Often generated at production
  time randomly per *batch* of cards.
- GIDS parameter file: TOML file with three values, often generated at
  production time randomly *per card*. Contains GIDS admin key (long hex
  string), serial number (can be generated as a random hex string), and PIN (6
  digits right now).
- [GIDS card production file](samplecard.sample.toml) (link goes to sample):
  TOML file describing parameters to take a card from "blank java card" all the
  way to "GIDS card, loaded with keys/certificates, and ISD key changed to avoid
  vulnerability from rogue applet installs". The sample is well documented
  because there are a lot of options.

## Running

You'll probably do this, except with a differnt card production file.

```sh
python3 -m cardproduction.cli.produce_gids samplecard.sample.toml
```

**Be careful!** if you mess up especially the ISD key stuff, you can "brick"
your cards quite quickly: this is a security feature.

## License

Dependencies have their own licenses, read and follow them!

The scripts themselves are `GPL-3.0-only`, config files and the like are
`CC0-1.0`, and this documentation is `CC-BY-4.0`. This repo follows the
[REUSE specification](https://reuse.software) so each file is clearly marked
with copyright and license in a machine and human readable way.

All license texts are in the `LICENSES` folder.

It's a part of all the licenses but it bears repeating here:

**Use at your own risk!**

I am publishing this not to necessarily build a community, but to record my
findings and procedures. I am not responsible if you brick your cards, fail to
meet cybersecurity standards, lose control of your private keys, etc.

## Acknowledgments and thanks

This tool was initially developed and maintained by Rylie Pavlik in the course
of her work at the open-source software consultancy
[Collabora](https://collabora.com). Thanks to Collabora and their "Open First"
mantra for supporting the development of this tool.

Thanks also to the developers of the projects this builds upon, especially those
being wrapped or manipulated directly by these scripts:

- Martin Paljak and community contributors to [GlobalPlatformPro][] - a modern,
  open way of manipulating applets on widely available Java Cards. (Martin is
  also the author of the primary build system for open source Java Card applets,
  ant-javacard.)
- Vincent LeToux ([MySmartLogon](https://www.mysmartlogon.com/) among other
  ventures) for the excellent [GidsApplet][] (and for patience with me) - it is
  compatible with a large range of cards and a large range of software packages,
  and is one of the few applets I've found that is compatible with 4096-bit RSA
  keys (and even lets you import them, after a small upstreamed patch) if the
  underlying Java Card is willing.

Trademarks are property of their respective owners.
