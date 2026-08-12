# ChimeraX-ModernDSSP
Modern DSSP secondary structure prediction and visualization

Allows use of a modern version of DSSP instead of the legacy version installed in ChimeraX.

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
