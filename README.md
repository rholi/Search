# Search
Search for files in fman with Cmd+F7 / Ctrl+F7

![Screenshot](search1.png?raw=true "Screenshot")
![Screenshot](search2.png?raw=true "Screenshot")

## Usage
Use the hotkey Cmd+F7 on Mac or Ctrl+F7 on Windows and Linux 
or use the Command Palette to run the `Search` command.

On Macs's, you can use Spotlight to search for files and text within files.

### "use regex" checkbox
When checked you can search your files with regex syntax.

*Examples for "file filter"*

All files

```*.*```

Pdf files

```*.pdf```

All files containing "Test"

```*Test*```

All files starting with "Test"

```Test*```

With "use regex" unchecked the filename needs to contain every word you type (separated with a space).

Case will be ignored.

*Examples for "file filter"*

All files containing "Test"

```Test```

All files containing "Test" and "final"

```Test final```

Note that this mode will also search the extension of the file.

So if you want to only search pdf files use

```Test pdf```




## Installation
Use fman's
[built-in command for installing plugins](https://fman.io/docs/installing-plugins).
 
