# ChimeraX-DSSP
Modern DSSP secondary structure prediction and visualization

Allows use of a modern version of DSSP instead of the legacy version installed in ChimeraX.

# dev notes
To build a bundle, start ChimeraX and execute the command:

```
devel build PATH_TO_SOURCE_CODE_FOLDER
```

Python source code and other resource files are copied into a build sub-folder below the source code folder. C/C++ source files, if any, are compiled and also copied into the build folder. The files in build are then assembled into a Python wheel in the dist sub-folder. The file with the .whl extension in the dist folder is the ChimeraX bundle.

To test the bundle, execute the ChimeraX command:

```
devel install PATH_TO_SOURCE_CODE_FOLDER
```

This will build the bundle, if necessary, and install the bundle in ChimeraX. Bundle functionality should be available immediately.

To remove temporary files created while building the bundle, execute the ChimeraX command:

```
devel clean PATH_TO_SOURCE_CODE_FOLDER
```

Some files, such as the bundle itself, may still remain and need to be removed manually.