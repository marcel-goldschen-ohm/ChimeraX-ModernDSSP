# ChimeraX-ModernDSSP
Modern DSSP secondary structure analysis and visualization

*Author:* Marcel Goldschen-Ohm

**Why?** Allows use of a modern version of DSSP instead of the legacy version installed in ChimeraX which does not annotate things such as pi-helices.

**Requires installation of DSSP.** For example, on macOS you can install it with Homebrew: `brew install brewsci/bio/dssp`, in which case the executable may be located at `/opt/homebrew/bin/mkdssp` depending on your homebrew setup. Tested on `mkdssp version 4.6.1`.

**In ChimeraX**, launch the plugin GUI (`Tools / Structure Analysis / Modern DSSP Secondary Structure`). Click the `Settings` button and set the executable path to `your/path/to/mkdssp`. Click the `Run` button to run DSSP on all visible or selected protein models. The `Color Ribbons` and `Color Atoms` buttons will apply distinct colors based on secondary structure type to all visible or selected models for which a DSSP calculation exists to either the ribbon (e.g., cartoon) or atom (e.g., licorice) representations, respectively. The color scheme can be viewed and edited in `Settings`. By default, DSSP is not re-run on models that have an existing DSSP calculation. To do so, click the `Clear` button to clear all exising DSSP calculations.

# dev notes
In ChimeraX:
```
devel build PATH_TO_SOURCE_CODE_FOLDER
devel install PATH_TO_SOURCE_CODE_FOLDER
```

If you make any changes, you need to cleanup the tool before re-installing to avoid issues with caching of your old tool.
```
toolshed uninstall ChimeraX-YourToolName
devel clean PATH_TO_SOURCE_CODE_FOLDER
```
