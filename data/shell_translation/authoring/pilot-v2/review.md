# Pilot v2 review pack

2026-10-10 (Europe/Budapest). Data prepared; no training started.

These samples are for human review of meaning. Every command is also covered by the release's Docker validation; that does not prove the English paraphrases are correct.

## Added coverage

| Capability | Groups | Examples |
| --- | ---: | ---: |
| content-versus-name-search | 100 | 600 |
| copy-move-destination | 300 | 1800 |
| count-units | 150 | 900 |
| current-location-listing | 6 | 36 |
| current-location-search | 30 | 180 |
| directory-creation | 200 | 1200 |
| directory-creation-composition | 50 | 300 |
| explicit-removal | 100 | 600 |
| filename-directory-composition | 50 | 300 |
| filesystem-filter-composition | 250 | 1500 |
| filesystem-filters | 300 | 1800 |
| listing-options | 300 | 1800 |
| literal-empty-files | 100 | 600 |
| literal-search-options | 350 | 2100 |
| ordered-file-reading | 100 | 600 |
| path-resolution | 200 | 1200 |
| permission-scope | 200 | 1200 |
| read-overwrite-append | 100 | 600 |
| recursive-directory-transfer | 100 | 600 |
| root-home-parent-current | 4 | 24 |
| start-end-lines-bytes | 400 | 2400 |

## content-versus-name-search

### coverage-v2-grep-0008 (train)

```json
{"op": "grep", "pattern": "NOTICE.cinder", "source": "cinder-journal-tree", "recursive": true}
```

```bash
grep -Frl -- NOTICE.cinder cinder-journal-tree
```

- Search "cinder-journal-tree" recursively for literal text "NOTICE.cinder"; return matching filenames only, respecting letter case.
- Which files anywhere under "cinder-journal-tree" contain the literal text "NOTICE.cinder", respecting letter case? Print their paths only.
- List paths of files containing literal "NOTICE.cinder" throughout "cinder-journal-tree" and its subdirectories, respecting letter case.
- I need filenames, not matching lines, for literal "NOTICE.cinder" anywhere in "cinder-journal-tree", respecting letter case.
- Find files by their contents: literal "NOTICE.cinder", recursively in "cinder-journal-tree", respecting letter case. Output paths only.
- Look inside every file below "cinder-journal-tree" for literal "NOTICE.cinder" and show matching file paths, respecting letter case.
### coverage-v2-grep-0188 (train)

```json
{"op": "grep", "pattern": "NOTICE.ember", "source": "ember-journal-tree", "recursive": true}
```

```bash
grep -Frl -- NOTICE.ember ember-journal-tree
```

- Search "ember-journal-tree" recursively for literal text "NOTICE.ember"; return matching filenames only, respecting letter case.
- Which files anywhere under "ember-journal-tree" contain the literal text "NOTICE.ember", respecting letter case? Print their paths only.
- List paths of files containing literal "NOTICE.ember" throughout "ember-journal-tree" and its subdirectories, respecting letter case.
- I need filenames, not matching lines, for literal "NOTICE.ember" anywhere in "ember-journal-tree", respecting letter case.
- Find files by their contents: literal "NOTICE.ember", recursively in "ember-journal-tree", respecting letter case. Output paths only.
- Look inside every file below "ember-journal-tree" for literal "NOTICE.ember" and show matching file paths, respecting letter case.
### coverage-v2-grep-0368 (validation)

```json
{"op": "grep", "pattern": "NOTICE.verdigris", "source": "verdigris-journal-tree", "recursive": true}
```

```bash
grep -Frl -- NOTICE.verdigris verdigris-journal-tree
```

- Return only file paths from a recursive content search for literal "NOTICE.verdigris" in "verdigris-journal-tree", respecting letter case.
- Walk all of "verdigris-journal-tree" and list the files whose text contains literal "NOTICE.verdigris", respecting letter case.
- Check file contents below "verdigris-journal-tree" for literal "NOTICE.verdigris", respecting letter case; report matching paths.
- Give me filenames containing literal "NOTICE.verdigris" in the entire "verdigris-journal-tree" tree, respecting letter case.
- Locate literal "NOTICE.verdigris" inside files under "verdigris-journal-tree", respecting letter case, including nested files; print only filenames.
- Inspect "verdigris-journal-tree" recursively and name files containing literal "NOTICE.verdigris", respecting letter case.
### coverage-v2-grep-0413 (validation)

```json
{"op": "grep", "pattern": "STATE:tundralake", "source": "tundralake;archive-tree", "recursive": true}
```

```bash
grep -Frl -- STATE:tundralake 'tundralake;archive-tree'
```

- Return only file paths from a recursive content search for literal "STATE:tundralake" in "tundralake;archive-tree", respecting letter case.
- Walk all of "tundralake;archive-tree" and list the files whose text contains literal "STATE:tundralake", respecting letter case.
- Check file contents below "tundralake;archive-tree" for literal "STATE:tundralake", respecting letter case; report matching paths.
- Give me filenames containing literal "STATE:tundralake" in the entire "tundralake;archive-tree" tree, respecting letter case.
- Locate literal "STATE:tundralake" inside files under "tundralake;archive-tree", respecting letter case, including nested files; print only filenames.
- Inspect "tundralake;archive-tree" recursively and name files containing literal "STATE:tundralake", respecting letter case.

## copy-move-destination

### coverage-v2-cp-0001 (train)

```json
{"op": "cp", "sources": ["cinder-journal.txt"], "destination": "cinder-journal-joined.txt"}
```

```bash
cp cinder-journal.txt cinder-journal-joined.txt
```

- Duplicate the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt", keeping the original.
- Copy the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt".
- Keep the file "cinder-journal.txt" where it is and put a copy to the file path "cinder-journal-joined.txt".
- I need another copy of the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt".
- Make a duplicate of the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt".
- Can you copy the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt" without moving it?
### coverage-v2-mv-0001 (train)

```json
{"op": "mv", "sources": ["cinder-journal.txt"], "destination": "cinder-journal-joined.txt"}
```

```bash
mv cinder-journal.txt cinder-journal-joined.txt
```

- Move the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt".
- Relocate the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt"; don't keep a copy at the old location.
- Transfer the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt", removing the source location.
- I want the file "cinder-journal.txt" moved to the file path "cinder-journal-joined.txt".
- Put the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt" instead of where it is now.
- Can you move the file "cinder-journal.txt" to the file path "cinder-journal-joined.txt" without leaving the original behind?
### coverage-v2-cp-0161 (validation)

```json
{"op": "cp", "sources": ["verdigris-journal.txt"], "destination": "verdigris-journal-joined.txt"}
```

```bash
cp verdigris-journal.txt verdigris-journal-joined.txt
```

- Place a duplicate of the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt" and preserve the source.
- Replicate the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt".
- Leave the original intact while copying the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt".
- Reproduce the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt" without deleting the source.
- Create a second copy of the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt".
- Save a copy of the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt"; retain the original.
### coverage-v2-mv-0161 (validation)

```json
{"op": "mv", "sources": ["verdigris-journal.txt"], "destination": "verdigris-journal-joined.txt"}
```

```bash
mv verdigris-journal.txt verdigris-journal-joined.txt
```

- Shift the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt" and remove the old entry.
- Change the location of the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt".
- Rehome the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt", leaving no copy at the source.
- Relocate the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt"; leave nothing at its former location.
- Carry the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt" rather than copying it.
- Take the file "verdigris-journal.txt" to the file path "verdigris-journal-joined.txt" and discard its former location.

## count-units

### coverage-v2-wc-0001 (train)

```json
{"op": "wc", "source": "cinder-journal.txt", "unit": "lines"}
```

```bash
wc -l cinder-journal.txt
```

- Count the lines in "cinder-journal.txt".
- How many lines does "cinder-journal.txt" contain?
- Give me the number of lines in "cinder-journal.txt".
- Measure "cinder-journal.txt" by its total lines.
- I need a count of lines for "cinder-journal.txt".
- Report the total number of lines in "cinder-journal.txt".
### coverage-v2-wc-0061 (train)

```json
{"op": "wc", "source": "ember-journal.txt", "unit": "lines"}
```

```bash
wc -l ember-journal.txt
```

- Count the lines in "ember-journal.txt".
- How many lines does "ember-journal.txt" contain?
- Give me the number of lines in "ember-journal.txt".
- Measure "ember-journal.txt" by its total lines.
- I need a count of lines for "ember-journal.txt".
- Report the total number of lines in "ember-journal.txt".
### coverage-v2-wc-0121 (validation)

```json
{"op": "wc", "source": "verdigris-journal.txt", "unit": "lines"}
```

```bash
wc -l verdigris-journal.txt
```

- What's the lines count for "verdigris-journal.txt"?
- Calculate how many lines are in "verdigris-journal.txt".
- Tell me "verdigris-journal.txt"'s total lines.
- Determine the number of lines contained in "verdigris-journal.txt".
- Return a tally of lines from "verdigris-journal.txt".
- Get the total lines in "verdigris-journal.txt".
### coverage-v2-wc-0136 (validation)

```json
{"op": "wc", "source": "tundralake;archive.txt", "unit": "lines"}
```

```bash
wc -l 'tundralake;archive.txt'
```

- What's the lines count for "tundralake;archive.txt"?
- Calculate how many lines are in "tundralake;archive.txt".
- Tell me "tundralake;archive.txt"'s total lines.
- Determine the number of lines contained in "tundralake;archive.txt".
- Return a tally of lines from "tundralake;archive.txt".
- Get the total lines in "tundralake;archive.txt".

## current-location-listing

### coverage-v2-ls-current-000 (train)

```json
{"op": "ls", "directory": ".", "all": false, "long": false, "one": false}
```

```bash
ls
```

- What's immediately inside here in the current directory? Show only non-hidden entries.
- List only non-hidden entries directly in here in the current directory.
- Give me only non-hidden entries from here in the current directory; don't descend into child folders.
- I'd like to see only non-hidden entries immediately under here in the current directory.
- Display the contents of here in the current directory, showing only non-hidden entries.
- Show a directory listing for here in the current directory: only non-hidden entries.
### coverage-v2-ls-current-100 (train)

```json
{"op": "ls", "directory": ".", "all": true, "long": false, "one": false}
```

```bash
ls -a
```

- What's immediately inside here in the current directory? Show all entries including hidden names.
- List all entries including hidden names directly in here in the current directory.
- Give me all entries including hidden names from here in the current directory; don't descend into child folders.
- I'd like to see all entries including hidden names immediately under here in the current directory.
- Display the contents of here in the current directory, showing all entries including hidden names.
- Show a directory listing for here in the current directory: all entries including hidden names.

## current-location-search

### coverage-v2-find-0551 (train)

```json
{"op": "find", "directory": ".", "type": "f", "pattern": "*.toml"}
```

```bash
find . -type f -name '*.toml'
```

- Find regular files with names ending in .toml here and in all folders below the current directory.
- List paths for regular files with names ending in .toml here and in all folders below the current directory.
- I need the paths of regular files with names ending in .toml here and in all folders below the current directory.
- Locate regular files with names ending in .toml here and in all folders below the current directory and print their paths.
- Which entries are regular files with names ending in .toml here and in all folders below the current directory? Show their paths.
- Search for regular files with names ending in .toml here and in all folders below the current directory; output paths only.
### coverage-v2-find-0566 (train)

```json
{"op": "find", "directory": ".", "type": "f", "pattern": "*.yaml"}
```

```bash
find . -type f -name '*.yaml'
```

- Find regular files with names ending in .yaml here and in all folders below the current directory.
- List paths for regular files with names ending in .yaml here and in all folders below the current directory.
- I need the paths of regular files with names ending in .yaml here and in all folders below the current directory.
- Locate regular files with names ending in .yaml here and in all folders below the current directory and print their paths.
- Which entries are regular files with names ending in .yaml here and in all folders below the current directory? Show their paths.
- Search for regular files with names ending in .yaml here and in all folders below the current directory; output paths only.

## directory-creation

### coverage-v2-mkdir-0001 (train)

```json
{"op": "mkdir", "targets": ["cinder-journal-folder"]}
```

```bash
mkdir cinder-journal-folder
```

- Create a directory named "cinder-journal-folder".
- I need a directory named "cinder-journal-folder" created.
- Make a directory named "cinder-journal-folder" so I can store things there.
- Set up a directory named "cinder-journal-folder".
- Could you create a directory named "cinder-journal-folder"?
- Add a directory named "cinder-journal-folder" to the filesystem.
### coverage-v2-mkdir-0101 (train)

```json
{"op": "mkdir", "targets": ["ember-journal-folder"]}
```

```bash
mkdir ember-journal-folder
```

- Create a directory named "ember-journal-folder".
- I need a directory named "ember-journal-folder" created.
- Make a directory named "ember-journal-folder" so I can store things there.
- Set up a directory named "ember-journal-folder".
- Could you create a directory named "ember-journal-folder"?
- Add a directory named "ember-journal-folder" to the filesystem.
### coverage-v2-mkdir-0201 (validation)

```json
{"op": "mkdir", "targets": ["verdigris-journal-folder"]}
```

```bash
mkdir verdigris-journal-folder
```

- Provision a directory named "verdigris-journal-folder".
- Establish a directory named "verdigris-journal-folder" for me.
- I'd like a directory named "verdigris-journal-folder" to exist.
- Prepare a directory named "verdigris-journal-folder".
- Give me a directory named "verdigris-journal-folder".
- Arrange for a directory named "verdigris-journal-folder" to be created.
### coverage-v2-mkdir-0226 (validation)

```json
{"op": "mkdir", "targets": ["tundralake;archive-folder"]}
```

```bash
mkdir 'tundralake;archive-folder'
```

- Provision a directory named "tundralake;archive-folder".
- Establish a directory named "tundralake;archive-folder" for me.
- I'd like a directory named "tundralake;archive-folder" to exist.
- Prepare a directory named "tundralake;archive-folder".
- Give me a directory named "tundralake;archive-folder".
- Arrange for a directory named "tundralake;archive-folder" to be created.

## directory-creation-composition

### coverage-v2-mkdir-0005 (train)

```json
{"op": "mkdir", "targets": ["cinder-journal/stage/final"], "parents": true, "mode": "750"}
```

```bash
mkdir -p -m 750 cinder-journal/stage/final
```

- Create a directory named "cinder-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- I need a directory named "cinder-journal/stage/final" created, creating any missing parent directories, with the final directory's permissions set to 750.
- Make a directory named "cinder-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750 so I can store things there.
- Set up a directory named "cinder-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Could you create a directory named "cinder-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750?
- Add a directory named "cinder-journal/stage/final" to the filesystem, creating any missing parent directories, with the final directory's permissions set to 750.
### coverage-v2-mkdir-0105 (train)

```json
{"op": "mkdir", "targets": ["ember-journal/stage/final"], "parents": true, "mode": "750"}
```

```bash
mkdir -p -m 750 ember-journal/stage/final
```

- Create a directory named "ember-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- I need a directory named "ember-journal/stage/final" created, creating any missing parent directories, with the final directory's permissions set to 750.
- Make a directory named "ember-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750 so I can store things there.
- Set up a directory named "ember-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Could you create a directory named "ember-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750?
- Add a directory named "ember-journal/stage/final" to the filesystem, creating any missing parent directories, with the final directory's permissions set to 750.
### coverage-v2-mkdir-0205 (validation)

```json
{"op": "mkdir", "targets": ["verdigris-journal/stage/final"], "parents": true, "mode": "750"}
```

```bash
mkdir -p -m 750 verdigris-journal/stage/final
```

- Provision a directory named "verdigris-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Establish a directory named "verdigris-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750 for me.
- I'd like a directory named "verdigris-journal/stage/final" to exist, creating any missing parent directories, with the final directory's permissions set to 750.
- Prepare a directory named "verdigris-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Give me a directory named "verdigris-journal/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Arrange for a directory named "verdigris-journal/stage/final" to be created, creating any missing parent directories, with the final directory's permissions set to 750.
### coverage-v2-mkdir-0230 (validation)

```json
{"op": "mkdir", "targets": ["tundralake;archive/stage/final"], "parents": true, "mode": "750"}
```

```bash
mkdir -p -m 750 'tundralake;archive/stage/final'
```

- Provision a directory named "tundralake;archive/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Establish a directory named "tundralake;archive/stage/final", creating any missing parent directories, with the final directory's permissions set to 750 for me.
- I'd like a directory named "tundralake;archive/stage/final" to exist, creating any missing parent directories, with the final directory's permissions set to 750.
- Prepare a directory named "tundralake;archive/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Give me a directory named "tundralake;archive/stage/final", creating any missing parent directories, with the final directory's permissions set to 750.
- Arrange for a directory named "tundralake;archive/stage/final" to be created, creating any missing parent directories, with the final directory's permissions set to 750.

## explicit-removal

### coverage-v2-rm-0001 (train)

```json
{"op": "rm", "targets": ["cinder-journal.txt", "cinder-journal-second.txt"], "recursive": false}
```

```bash
rm cinder-journal.txt cinder-journal-second.txt
```

- Delete the files "cinder-journal.txt" and "cinder-journal-second.txt".
- Remove the files "cinder-journal.txt" and "cinder-journal-second.txt" from disk.
- I don't need the files "cinder-journal.txt" and "cinder-journal-second.txt"; erase it.
- Get rid of the files "cinder-journal.txt" and "cinder-journal-second.txt".
- Can you delete the files "cinder-journal.txt" and "cinder-journal-second.txt" for me?
- Erase the files "cinder-journal.txt" and "cinder-journal-second.txt" completely.
### coverage-v2-rm-0041 (train)

```json
{"op": "rm", "targets": ["ember-journal.txt", "ember-journal-second.txt"], "recursive": false}
```

```bash
rm ember-journal.txt ember-journal-second.txt
```

- Delete the files "ember-journal.txt" and "ember-journal-second.txt".
- Remove the files "ember-journal.txt" and "ember-journal-second.txt" from disk.
- I don't need the files "ember-journal.txt" and "ember-journal-second.txt"; erase it.
- Get rid of the files "ember-journal.txt" and "ember-journal-second.txt".
- Can you delete the files "ember-journal.txt" and "ember-journal-second.txt" for me?
- Erase the files "ember-journal.txt" and "ember-journal-second.txt" completely.
### coverage-v2-rm-0081 (validation)

```json
{"op": "rm", "targets": ["verdigris-journal.txt", "verdigris-journal-second.txt"], "recursive": false}
```

```bash
rm verdigris-journal.txt verdigris-journal-second.txt
```

- Discard the files "verdigris-journal.txt" and "verdigris-journal-second.txt" from the filesystem.
- Please remove the files "verdigris-journal.txt" and "verdigris-journal-second.txt" permanently.
- Clear out the files "verdigris-journal.txt" and "verdigris-journal-second.txt".
- I want the files "verdigris-journal.txt" and "verdigris-journal-second.txt" gone from disk.
- Wipe away the files "verdigris-journal.txt" and "verdigris-journal-second.txt".
- Delete the filesystem entries for the files "verdigris-journal.txt" and "verdigris-journal-second.txt".
### coverage-v2-rm-0091 (validation)

```json
{"op": "rm", "targets": ["tundralake;archive.txt", "tundralake;archive-second.txt"], "recursive": false}
```

```bash
rm 'tundralake;archive.txt' 'tundralake;archive-second.txt'
```

- Discard the files "tundralake;archive.txt" and "tundralake;archive-second.txt" from the filesystem.
- Please remove the files "tundralake;archive.txt" and "tundralake;archive-second.txt" permanently.
- Clear out the files "tundralake;archive.txt" and "tundralake;archive-second.txt".
- I want the files "tundralake;archive.txt" and "tundralake;archive-second.txt" gone from disk.
- Wipe away the files "tundralake;archive.txt" and "tundralake;archive-second.txt".
- Delete the filesystem entries for the files "tundralake;archive.txt" and "tundralake;archive-second.txt".

## filename-directory-composition

### coverage-v2-touch-0003 (train)

```json
{"op": "touch", "targets": ["cinder-journal-tree/cinder-journal.txt"]}
```

```bash
touch cinder-journal-tree/cinder-journal.txt
```

- Create an empty file called "cinder-journal.txt" inside the existing folder "cinder-journal-tree".
- Put a new blank file named "cinder-journal.txt" in "cinder-journal-tree".
- I need an empty "cinder-journal.txt" file under "cinder-journal-tree".
- Inside "cinder-journal-tree", create a file named "cinder-journal.txt" with no contents.
- Make a zero-byte file named "cinder-journal.txt" in the directory "cinder-journal-tree".
- Add an empty placeholder named "cinder-journal.txt" to "cinder-journal-tree".
### coverage-v2-touch-0063 (train)

```json
{"op": "touch", "targets": ["ember-journal-tree/ember-journal.txt"]}
```

```bash
touch ember-journal-tree/ember-journal.txt
```

- Create an empty file called "ember-journal.txt" inside the existing folder "ember-journal-tree".
- Put a new blank file named "ember-journal.txt" in "ember-journal-tree".
- I need an empty "ember-journal.txt" file under "ember-journal-tree".
- Inside "ember-journal-tree", create a file named "ember-journal.txt" with no contents.
- Make a zero-byte file named "ember-journal.txt" in the directory "ember-journal-tree".
- Add an empty placeholder named "ember-journal.txt" to "ember-journal-tree".
### coverage-v2-touch-0123 (validation)

```json
{"op": "touch", "targets": ["verdigris-journal-tree/verdigris-journal.txt"]}
```

```bash
touch verdigris-journal-tree/verdigris-journal.txt
```

- Initialize a blank file called "verdigris-journal.txt" within "verdigris-journal-tree".
- Under the folder "verdigris-journal-tree", set up the empty file "verdigris-journal.txt".
- Give me a new zero-length "verdigris-journal.txt" file inside "verdigris-journal-tree".
- The existing directory "verdigris-journal-tree" needs a new empty file called "verdigris-journal.txt".
- Place a blank placeholder named "verdigris-journal.txt" within "verdigris-journal-tree".
- Prepare "verdigris-journal.txt" as an empty new file in the folder "verdigris-journal-tree".
### coverage-v2-touch-0138 (validation)

```json
{"op": "touch", "targets": ["tundralake;archive-tree/tundralake;archive.txt"]}
```

```bash
touch 'tundralake;archive-tree/tundralake;archive.txt'
```

- Initialize a blank file called "tundralake;archive.txt" within "tundralake;archive-tree".
- Under the folder "tundralake;archive-tree", set up the empty file "tundralake;archive.txt".
- Give me a new zero-length "tundralake;archive.txt" file inside "tundralake;archive-tree".
- The existing directory "tundralake;archive-tree" needs a new empty file called "tundralake;archive.txt".
- Place a blank placeholder named "tundralake;archive.txt" within "tundralake;archive-tree".
- Prepare "tundralake;archive.txt" as an empty new file in the folder "tundralake;archive-tree".

## filesystem-filter-composition

### coverage-v2-find-0004 (train)

```json
{"op": "find", "directory": "cinder-journal-tree", "type": "f", "pattern": "*.toml", "size_gt": 64}
```

```bash
find cinder-journal-tree -type f -name '*.toml' -size +64c
```

- Find regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree".
- List paths for regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree".
- I need the paths of regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree".
- Locate regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree" and print their paths.
- Which entries are regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree"? Show their paths.
- Search for regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "cinder-journal-tree"; output paths only.
### coverage-v2-find-0224 (train)

```json
{"op": "find", "directory": "ember-journal-tree", "type": "f", "pattern": "*.toml", "size_gt": 64}
```

```bash
find ember-journal-tree -type f -name '*.toml' -size +64c
```

- Find regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree".
- List paths for regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree".
- I need the paths of regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree".
- Locate regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree" and print their paths.
- Which entries are regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree"? Show their paths.
- Search for regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "ember-journal-tree"; output paths only.
### coverage-v2-find-0444 (validation)

```json
{"op": "find", "directory": "verdigris-journal-tree", "type": "f", "pattern": "*.toml", "size_gt": 64}
```

```bash
find verdigris-journal-tree -type f -name '*.toml' -size +64c
```

- Return pathnames for regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "verdigris-journal-tree".
- Identify regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "verdigris-journal-tree" by pathname.
- Collect the paths of regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "verdigris-journal-tree".
- Enumerate regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "verdigris-journal-tree", showing each path.
- I want a path list of regular files whose names end in .toml and whose size is strictly greater than 64 bytes recursively below "verdigris-journal-tree".
- Report where regular files whose names end in .toml and whose size is strictly greater than 64 bytes are recursively below "verdigris-journal-tree".
### coverage-v2-find-0499 (validation)

```json
{"op": "find", "directory": "tundralake;archive-tree", "type": "f", "pattern": "*.yaml", "size_gt": 64}
```

```bash
find 'tundralake;archive-tree' -type f -name '*.yaml' -size +64c
```

- Return pathnames for regular files whose names end in .yaml and whose size is strictly greater than 64 bytes recursively below "tundralake;archive-tree".
- Identify regular files whose names end in .yaml and whose size is strictly greater than 64 bytes recursively below "tundralake;archive-tree" by pathname.
- Collect the paths of regular files whose names end in .yaml and whose size is strictly greater than 64 bytes recursively below "tundralake;archive-tree".
- Enumerate regular files whose names end in .yaml and whose size is strictly greater than 64 bytes recursively below "tundralake;archive-tree", showing each path.
- I want a path list of regular files whose names end in .yaml and whose size is strictly greater than 64 bytes recursively below "tundralake;archive-tree".
- Report where regular files whose names end in .yaml and whose size is strictly greater than 64 bytes are recursively below "tundralake;archive-tree".

## filesystem-filters

### coverage-v2-find-0001 (train)

```json
{"op": "find", "directory": "cinder-journal-tree", "type": "f"}
```

```bash
find cinder-journal-tree -type f
```

- Find regular files recursively below "cinder-journal-tree".
- List paths for regular files recursively below "cinder-journal-tree".
- I need the paths of regular files recursively below "cinder-journal-tree".
- Locate regular files recursively below "cinder-journal-tree" and print their paths.
- Which entries are regular files recursively below "cinder-journal-tree"? Show their paths.
- Search for regular files recursively below "cinder-journal-tree"; output paths only.
### coverage-v2-find-0221 (train)

```json
{"op": "find", "directory": "ember-journal-tree", "type": "f"}
```

```bash
find ember-journal-tree -type f
```

- Find regular files recursively below "ember-journal-tree".
- List paths for regular files recursively below "ember-journal-tree".
- I need the paths of regular files recursively below "ember-journal-tree".
- Locate regular files recursively below "ember-journal-tree" and print their paths.
- Which entries are regular files recursively below "ember-journal-tree"? Show their paths.
- Search for regular files recursively below "ember-journal-tree"; output paths only.
### coverage-v2-find-0441 (validation)

```json
{"op": "find", "directory": "verdigris-journal-tree", "type": "f"}
```

```bash
find verdigris-journal-tree -type f
```

- Return pathnames for regular files recursively below "verdigris-journal-tree".
- Identify regular files recursively below "verdigris-journal-tree" by pathname.
- Collect the paths of regular files recursively below "verdigris-journal-tree".
- Enumerate regular files recursively below "verdigris-journal-tree", showing each path.
- I want a path list of regular files recursively below "verdigris-journal-tree".
- Report where regular files are recursively below "verdigris-journal-tree".
### coverage-v2-find-0496 (validation)

```json
{"op": "find", "directory": "tundralake;archive-tree", "type": "f"}
```

```bash
find 'tundralake;archive-tree' -type f
```

- Return pathnames for regular files recursively below "tundralake;archive-tree".
- Identify regular files recursively below "tundralake;archive-tree" by pathname.
- Collect the paths of regular files recursively below "tundralake;archive-tree".
- Enumerate regular files recursively below "tundralake;archive-tree", showing each path.
- I want a path list of regular files recursively below "tundralake;archive-tree".
- Report where regular files are recursively below "tundralake;archive-tree".

## listing-options

### coverage-v2-ls-0001 (train)

```json
{"op": "ls", "directory": "cinder-journal", "all": false, "long": false, "one": false}
```

```bash
ls cinder-journal
```

- What's immediately inside the directory "cinder-journal"? Show non-hidden entries.
- List non-hidden entries directly in the directory "cinder-journal".
- Give me non-hidden entries from the directory "cinder-journal"; don't descend into child folders.
- I'd like to see non-hidden entries immediately under the directory "cinder-journal".
- Display the contents of the directory "cinder-journal", showing non-hidden entries.
- Show a directory listing for the directory "cinder-journal": non-hidden entries.
### coverage-v2-ls-0121 (train)

```json
{"op": "ls", "directory": "ember-journal", "all": false, "long": false, "one": false}
```

```bash
ls ember-journal
```

- What's immediately inside the directory "ember-journal"? Show non-hidden entries.
- List non-hidden entries directly in the directory "ember-journal".
- Give me non-hidden entries from the directory "ember-journal"; don't descend into child folders.
- I'd like to see non-hidden entries immediately under the directory "ember-journal".
- Display the contents of the directory "ember-journal", showing non-hidden entries.
- Show a directory listing for the directory "ember-journal": non-hidden entries.
### coverage-v2-ls-0241 (validation)

```json
{"op": "ls", "directory": "verdigris-journal", "all": false, "long": false, "one": false}
```

```bash
ls verdigris-journal
```

- For the directory "verdigris-journal", report non-hidden entries at the top level only.
- Let me inspect non-hidden entries directly inside the directory "verdigris-journal".
- Return non-hidden entries from the immediate contents of the directory "verdigris-journal".
- Present a listing of the directory "verdigris-journal", limited to non-hidden entries.
- I need the immediate entries of the directory "verdigris-journal": non-hidden entries.
- Reveal non-hidden entries in the directory "verdigris-journal", without walking the tree.
### coverage-v2-ls-0271 (validation)

```json
{"op": "ls", "directory": "tundralake;archive", "all": false, "long": false, "one": false}
```

```bash
ls 'tundralake;archive'
```

- For the directory "tundralake;archive", report non-hidden entries at the top level only.
- Let me inspect non-hidden entries directly inside the directory "tundralake;archive".
- Return non-hidden entries from the immediate contents of the directory "tundralake;archive".
- Present a listing of the directory "tundralake;archive", limited to non-hidden entries.
- I need the immediate entries of the directory "tundralake;archive": non-hidden entries.
- Reveal non-hidden entries in the directory "tundralake;archive", without walking the tree.

## literal-empty-files

### coverage-v2-touch-0001 (train)

```json
{"op": "touch", "targets": ["cinder-journal.txt"]}
```

```bash
touch cinder-journal.txt
```

- Create a file named "cinder-journal.txt"; they don't exist yet.
- I need a file named "cinder-journal.txt" with no contents yet.
- Make a file named "cinder-journal.txt", leaving them empty.
- Add a file named "cinder-journal.txt" as empty placeholders.
- Can you create a file named "cinder-journal.txt" without writing any text?
- Start with a file named "cinder-journal.txt" containing zero bytes.
### coverage-v2-touch-0061 (train)

```json
{"op": "touch", "targets": ["ember-journal.txt"]}
```

```bash
touch ember-journal.txt
```

- Create a file named "ember-journal.txt"; they don't exist yet.
- I need a file named "ember-journal.txt" with no contents yet.
- Make a file named "ember-journal.txt", leaving them empty.
- Add a file named "ember-journal.txt" as empty placeholders.
- Can you create a file named "ember-journal.txt" without writing any text?
- Start with a file named "ember-journal.txt" containing zero bytes.
### coverage-v2-touch-0121 (validation)

```json
{"op": "touch", "targets": ["verdigris-journal.txt"]}
```

```bash
touch verdigris-journal.txt
```

- Put a file named "verdigris-journal.txt" on disk as empty new files.
- Initialize a file named "verdigris-journal.txt" with no data in them.
- Set up a file named "verdigris-journal.txt" as zero-length files.
- I'd like blank placeholders at a file named "verdigris-journal.txt".
- Produce a file named "verdigris-journal.txt", but leave their contents blank.
- Prepare a file named "verdigris-journal.txt" as new empty files.
### coverage-v2-touch-0136 (validation)

```json
{"op": "touch", "targets": ["tundralake;archive.txt"]}
```

```bash
touch 'tundralake;archive.txt'
```

- Put a file named "tundralake;archive.txt" on disk as empty new files.
- Initialize a file named "tundralake;archive.txt" with no data in them.
- Set up a file named "tundralake;archive.txt" as zero-length files.
- I'd like blank placeholders at a file named "tundralake;archive.txt".
- Produce a file named "tundralake;archive.txt", but leave their contents blank.
- Prepare a file named "tundralake;archive.txt" as new empty files.

## literal-search-options

### coverage-v2-grep-0001 (train)

```json
{"op": "grep", "pattern": "NOTICE.cinder", "source": "cinder-journal.txt"}
```

```bash
grep -F -- NOTICE.cinder cinder-journal.txt
```

- In "cinder-journal.txt", print lines containing the literal text "NOTICE.cinder", respecting letter case.
- Print lines containing the literal text "NOTICE.cinder" from "cinder-journal.txt", respecting letter case.
- I need you to print lines containing the literal text "NOTICE.cinder" in "cinder-journal.txt", respecting letter case.
- For "cinder-journal.txt", print only lines containing the literal text "NOTICE.cinder", respecting letter case.
- Could you print lines containing the literal text "NOTICE.cinder" from "cinder-journal.txt", respecting letter case?
- Read "cinder-journal.txt" and print lines containing the literal text "NOTICE.cinder", respecting letter case.
### coverage-v2-grep-0181 (train)

```json
{"op": "grep", "pattern": "NOTICE.ember", "source": "ember-journal.txt"}
```

```bash
grep -F -- NOTICE.ember ember-journal.txt
```

- In "ember-journal.txt", print lines containing the literal text "NOTICE.ember", respecting letter case.
- Print lines containing the literal text "NOTICE.ember" from "ember-journal.txt", respecting letter case.
- I need you to print lines containing the literal text "NOTICE.ember" in "ember-journal.txt", respecting letter case.
- For "ember-journal.txt", print only lines containing the literal text "NOTICE.ember", respecting letter case.
- Could you print lines containing the literal text "NOTICE.ember" from "ember-journal.txt", respecting letter case?
- Read "ember-journal.txt" and print lines containing the literal text "NOTICE.ember", respecting letter case.
### coverage-v2-grep-0361 (validation)

```json
{"op": "grep", "pattern": "NOTICE.verdigris", "source": "verdigris-journal.txt"}
```

```bash
grep -F -- NOTICE.verdigris verdigris-journal.txt
```

- Looking through "verdigris-journal.txt", print lines containing the literal text "NOTICE.verdigris", respecting letter case.
- From the text in "verdigris-journal.txt", print lines containing the literal text "NOTICE.verdigris", respecting letter case.
- Please print lines containing the literal text "NOTICE.verdigris", respecting letter case, using "verdigris-journal.txt" as input.
- Examine "verdigris-journal.txt" to print lines containing the literal text "NOTICE.verdigris", respecting letter case.
- For my input file "verdigris-journal.txt", I want to print lines containing the literal text "NOTICE.verdigris", respecting letter case.
- Go through "verdigris-journal.txt"; print lines containing the literal text "NOTICE.verdigris", respecting letter case.
### coverage-v2-grep-0406 (validation)

```json
{"op": "grep", "pattern": "STATE:tundralake", "source": "tundralake;archive.txt"}
```

```bash
grep -F -- STATE:tundralake 'tundralake;archive.txt'
```

- Looking through "tundralake;archive.txt", print lines containing the literal text "STATE:tundralake", respecting letter case.
- From the text in "tundralake;archive.txt", print lines containing the literal text "STATE:tundralake", respecting letter case.
- Please print lines containing the literal text "STATE:tundralake", respecting letter case, using "tundralake;archive.txt" as input.
- Examine "tundralake;archive.txt" to print lines containing the literal text "STATE:tundralake", respecting letter case.
- For my input file "tundralake;archive.txt", I want to print lines containing the literal text "STATE:tundralake", respecting letter case.
- Go through "tundralake;archive.txt"; print lines containing the literal text "STATE:tundralake", respecting letter case.

## ordered-file-reading

### coverage-v2-cat-0001 (train)

```json
{"op": "cat", "sources": ["cinder-journal.txt"]}
```

```bash
cat cinder-journal.txt
```

- Print "cinder-journal.txt" in full, in that order.
- Show the complete contents of "cinder-journal.txt" in order.
- Display all the text from "cinder-journal.txt", one after the other.
- Read "cinder-journal.txt" to the terminal without modifying them, in the listed order.
- I want all of "cinder-journal.txt" printed in order.
- Output "cinder-journal.txt" completely, following their stated order.
### coverage-v2-cat-0081 (train)

```json
{"op": "cat", "sources": ["ember-journal.txt"]}
```

```bash
cat ember-journal.txt
```

- Print "ember-journal.txt" in full, in that order.
- Show the complete contents of "ember-journal.txt" in order.
- Display all the text from "ember-journal.txt", one after the other.
- Read "ember-journal.txt" to the terminal without modifying them, in the listed order.
- I want all of "ember-journal.txt" printed in order.
- Output "ember-journal.txt" completely, following their stated order.
### coverage-v2-cat-0161 (validation)

```json
{"op": "cat", "sources": ["verdigris-journal.txt"]}
```

```bash
cat verdigris-journal.txt
```

- Emit the entire contents of "verdigris-journal.txt" sequentially.
- Let me read all of "verdigris-journal.txt" in the order given.
- Write "verdigris-journal.txt" to standard output in order, leaving the files unchanged.
- Return every byte of "verdigris-journal.txt", concatenated in the specified order.
- Present the whole text of "verdigris-journal.txt" in sequence.
- Send the contents of "verdigris-journal.txt" to my terminal in order.
### coverage-v2-cat-0181 (validation)

```json
{"op": "cat", "sources": ["tundralake;archive.txt"]}
```

```bash
cat 'tundralake;archive.txt'
```

- Emit the entire contents of "tundralake;archive.txt" sequentially.
- Let me read all of "tundralake;archive.txt" in the order given.
- Write "tundralake;archive.txt" to standard output in order, leaving the files unchanged.
- Return every byte of "tundralake;archive.txt", concatenated in the specified order.
- Present the whole text of "tundralake;archive.txt" in sequence.
- Send the contents of "tundralake;archive.txt" to my terminal in order.

## path-resolution

### coverage-v2-cd-0001 (train)

```json
{"op": "cd", "destination": "cinder-journal"}
```

```bash
cd cinder-journal
```

- Take my terminal into the relative directory path "cinder-journal".
- I want this shell to work from the relative directory path "cinder-journal".
- Make the relative directory path "cinder-journal" the active working directory.
- Switch the terminal's location to the relative directory path "cinder-journal".
- Can I start working inside the relative directory path "cinder-journal"?
- Go to the relative directory path "cinder-journal" in this shell session.
### coverage-v2-cd-0081 (train)

```json
{"op": "cd", "destination": "ember-journal"}
```

```bash
cd ember-journal
```

- Take my terminal into the relative directory path "ember-journal".
- I want this shell to work from the relative directory path "ember-journal".
- Make the relative directory path "ember-journal" the active working directory.
- Switch the terminal's location to the relative directory path "ember-journal".
- Can I start working inside the relative directory path "ember-journal"?
- Go to the relative directory path "ember-journal" in this shell session.
### coverage-v2-cd-0161 (validation)

```json
{"op": "cd", "destination": "verdigris-journal"}
```

```bash
cd verdigris-journal
```

- Set the session's working location to the relative directory path "verdigris-journal".
- From now on, operate in the relative directory path "verdigris-journal".
- Move the shell's current location into the relative directory path "verdigris-journal".
- Use the relative directory path "verdigris-journal" as my current directory.
- The terminal should be positioned at the relative directory path "verdigris-journal".
- Change where this session is working: the relative directory path "verdigris-journal".
### coverage-v2-cd-0181 (validation)

```json
{"op": "cd", "destination": "tundralake;archive"}
```

```bash
cd 'tundralake;archive'
```

- Set the session's working location to the relative directory path "tundralake;archive".
- From now on, operate in the relative directory path "tundralake;archive".
- Move the shell's current location into the relative directory path "tundralake;archive".
- Use the relative directory path "tundralake;archive" as my current directory.
- The terminal should be positioned at the relative directory path "tundralake;archive".
- Change where this session is working: the relative directory path "tundralake;archive".

## permission-scope

### coverage-v2-chmod-0001 (train)

```json
{"op": "chmod", "targets": ["cinder-journal.txt"], "mode": "600"}
```

```bash
chmod 600 cinder-journal.txt
```

- Set the permissions of "cinder-journal.txt" to 600.
- Give "cinder-journal.txt" octal permissions 600.
- I need "cinder-journal.txt" to have mode 600.
- Change the access mode on "cinder-journal.txt" to 600.
- Apply permission bits 600 to "cinder-journal.txt".
- Make the mode of "cinder-journal.txt" exactly 600.
### coverage-v2-chmod-0081 (train)

```json
{"op": "chmod", "targets": ["ember-journal.txt"], "mode": "600"}
```

```bash
chmod 600 ember-journal.txt
```

- Set the permissions of "ember-journal.txt" to 600.
- Give "ember-journal.txt" octal permissions 600.
- I need "ember-journal.txt" to have mode 600.
- Change the access mode on "ember-journal.txt" to 600.
- Apply permission bits 600 to "ember-journal.txt".
- Make the mode of "ember-journal.txt" exactly 600.
### coverage-v2-chmod-0161 (validation)

```json
{"op": "chmod", "targets": ["verdigris-journal.txt"], "mode": "600"}
```

```bash
chmod 600 verdigris-journal.txt
```

- Assign octal mode 600 to "verdigris-journal.txt".
- Use permission value 600 for "verdigris-journal.txt".
- The access bits for "verdigris-journal.txt" should be 600.
- Update "verdigris-journal.txt" so their permissions are 600.
- Replace the permission bits on "verdigris-journal.txt" with 600.
- Configure "verdigris-journal.txt" with octal permissions 600.
### coverage-v2-chmod-0181 (validation)

```json
{"op": "chmod", "targets": ["tundralake;archive.txt"], "mode": "600"}
```

```bash
chmod 600 'tundralake;archive.txt'
```

- Assign octal mode 600 to "tundralake;archive.txt".
- Use permission value 600 for "tundralake;archive.txt".
- The access bits for "tundralake;archive.txt" should be 600.
- Update "tundralake;archive.txt" so their permissions are 600.
- Replace the permission bits on "tundralake;archive.txt" with 600.
- Configure "tundralake;archive.txt" with octal permissions 600.

## read-overwrite-append

### coverage-v2-cat-0003 (train)

```json
{"op": "cat", "sources": ["cinder-journal.txt", "cinder-journal-second.txt"], "output": "cinder-journal-joined.txt"}
```

```bash
cat cinder-journal.txt cinder-journal-second.txt > cinder-journal-joined.txt
```

- Combine "cinder-journal.txt" and "cinder-journal-second.txt", in that order, into "cinder-journal-joined.txt"; replace its existing contents.
- Write all of "cinder-journal.txt" and "cinder-journal-second.txt" in sequence to "cinder-journal-joined.txt", overwriting that file.
- I need "cinder-journal-joined.txt" replaced by the concatenation of "cinder-journal.txt" and "cinder-journal-second.txt" in the stated order.
- Join "cinder-journal.txt" and "cinder-journal-second.txt" in order and save the result in "cinder-journal-joined.txt", replacing old data.
- Copy the contents of "cinder-journal.txt" and "cinder-journal-second.txt" sequentially into "cinder-journal-joined.txt"; overwrite the destination.
- Create the combined text of "cinder-journal.txt" and "cinder-journal-second.txt" in "cinder-journal-joined.txt", in order, discarding its previous contents.
### coverage-v2-cat-0083 (train)

```json
{"op": "cat", "sources": ["ember-journal.txt", "ember-journal-second.txt"], "output": "ember-journal-joined.txt"}
```

```bash
cat ember-journal.txt ember-journal-second.txt > ember-journal-joined.txt
```

- Combine "ember-journal.txt" and "ember-journal-second.txt", in that order, into "ember-journal-joined.txt"; replace its existing contents.
- Write all of "ember-journal.txt" and "ember-journal-second.txt" in sequence to "ember-journal-joined.txt", overwriting that file.
- I need "ember-journal-joined.txt" replaced by the concatenation of "ember-journal.txt" and "ember-journal-second.txt" in the stated order.
- Join "ember-journal.txt" and "ember-journal-second.txt" in order and save the result in "ember-journal-joined.txt", replacing old data.
- Copy the contents of "ember-journal.txt" and "ember-journal-second.txt" sequentially into "ember-journal-joined.txt"; overwrite the destination.
- Create the combined text of "ember-journal.txt" and "ember-journal-second.txt" in "ember-journal-joined.txt", in order, discarding its previous contents.
### coverage-v2-cat-0163 (validation)

```json
{"op": "cat", "sources": ["verdigris-journal.txt", "verdigris-journal-second.txt"], "output": "verdigris-journal-joined.txt"}
```

```bash
cat verdigris-journal.txt verdigris-journal-second.txt > verdigris-journal-joined.txt
```

- Replace the data in "verdigris-journal-joined.txt" with all of "verdigris-journal.txt" and "verdigris-journal-second.txt", concatenated in order.
- Save "verdigris-journal.txt" and "verdigris-journal-second.txt" sequentially as the new contents of "verdigris-journal-joined.txt".
- Overwrite "verdigris-journal-joined.txt" with the joined contents of "verdigris-journal.txt" and "verdigris-journal-second.txt", in the given order.
- Put the concatenation of "verdigris-journal.txt" and "verdigris-journal-second.txt" into "verdigris-journal-joined.txt"; replace the destination's text.
- Rebuild "verdigris-journal-joined.txt" from the full contents of "verdigris-journal.txt" and "verdigris-journal-second.txt" in sequence.
- Store "verdigris-journal.txt" and "verdigris-journal-second.txt", joined in order, in "verdigris-journal-joined.txt" instead of its old contents.
### coverage-v2-cat-0183 (validation)

```json
{"op": "cat", "sources": ["tundralake;archive.txt", "tundralake;archive-second.txt"], "output": "tundralake;archive-joined.txt"}
```

```bash
cat 'tundralake;archive.txt' 'tundralake;archive-second.txt' > 'tundralake;archive-joined.txt'
```

- Replace the data in "tundralake;archive-joined.txt" with all of "tundralake;archive.txt" and "tundralake;archive-second.txt", concatenated in order.
- Save "tundralake;archive.txt" and "tundralake;archive-second.txt" sequentially as the new contents of "tundralake;archive-joined.txt".
- Overwrite "tundralake;archive-joined.txt" with the joined contents of "tundralake;archive.txt" and "tundralake;archive-second.txt", in the given order.
- Put the concatenation of "tundralake;archive.txt" and "tundralake;archive-second.txt" into "tundralake;archive-joined.txt"; replace the destination's text.
- Rebuild "tundralake;archive-joined.txt" from the full contents of "tundralake;archive.txt" and "tundralake;archive-second.txt" in sequence.
- Store "tundralake;archive.txt" and "tundralake;archive-second.txt", joined in order, in "tundralake;archive-joined.txt" instead of its old contents.

## recursive-directory-transfer

### coverage-v2-cp-0004 (train)

```json
{"op": "cp", "sources": ["cinder-journal-tree"], "destination": "cinder-journal-tree-saved", "directory_source": true}
```

```bash
cp -r cinder-journal-tree cinder-journal-tree-saved
```

- Duplicate the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved", keeping the original.
- Copy the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved".
- Keep the directory "cinder-journal-tree" with all its nested contents where it is and put a copy to the new directory path "cinder-journal-tree-saved".
- I need another copy of the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved".
- Make a duplicate of the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved".
- Can you copy the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved" without moving it?
### coverage-v2-mv-0004 (train)

```json
{"op": "mv", "sources": ["cinder-journal-tree"], "destination": "cinder-journal-tree-saved", "directory_source": true}
```

```bash
mv cinder-journal-tree cinder-journal-tree-saved
```

- Move the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved".
- Relocate the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved"; don't keep a copy at the old location.
- Transfer the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved", removing the source location.
- I want the directory "cinder-journal-tree" with all its nested contents moved to the new directory path "cinder-journal-tree-saved".
- Put the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved" instead of where it is now.
- Can you move the directory "cinder-journal-tree" with all its nested contents to the new directory path "cinder-journal-tree-saved" without leaving the original behind?
### coverage-v2-cp-0164 (validation)

```json
{"op": "cp", "sources": ["verdigris-journal-tree"], "destination": "verdigris-journal-tree-saved", "directory_source": true}
```

```bash
cp -r verdigris-journal-tree verdigris-journal-tree-saved
```

- Place a duplicate of the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved" and preserve the source.
- Replicate the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved".
- Leave the original intact while copying the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved".
- Reproduce the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved" without deleting the source.
- Create a second copy of the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved".
- Save a copy of the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved"; retain the original.
### coverage-v2-mv-0164 (validation)

```json
{"op": "mv", "sources": ["verdigris-journal-tree"], "destination": "verdigris-journal-tree-saved", "directory_source": true}
```

```bash
mv verdigris-journal-tree verdigris-journal-tree-saved
```

- Shift the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved" and remove the old entry.
- Change the location of the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved".
- Rehome the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved", leaving no copy at the source.
- Relocate the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved"; leave nothing at its former location.
- Carry the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved" rather than copying it.
- Take the directory "verdigris-journal-tree" with all its nested contents to the new directory path "verdigris-journal-tree-saved" and discard its former location.

## root-home-parent-current

### coverage-v2-cd-primitive-0 (train)

```json
{"op": "cd", "destination": "/"}
```

```bash
cd /
```

- Put the terminal at the filesystem root.
- Go all the way to the top of the filesystem.
- I want to work in the root of the Linux directory tree.
- Take this session to the slash directory.
- Switch into the filesystem's root folder.
- Set my shell's directory to the topmost filesystem location.
### coverage-v2-cd-primitive-2 (train)

```json
{"op": "cd", "destination": ".."}
```

```bash
cd ..
```

- Move this terminal up one directory level.
- Go to the folder containing the current one.
- I want to work in this folder's parent.
- Take the shell one level higher in the directory tree.
- Switch from this directory to its immediate parent.
- Set the current location to the enclosing directory.

## start-end-lines-bytes

### coverage-v2-head-0001 (train)

```json
{"op": "head", "source": "cinder-journal.txt", "count": 1, "bytes": false}
```

```bash
head -n 1 cinder-journal.txt
```

- Show the first 1 line of "cinder-journal.txt".
- Print 1 line from the start of "cinder-journal.txt".
- I only want the opening 1 line from "cinder-journal.txt".
- Display "cinder-journal.txt" up to its first 1 line.
- Read the beginning of "cinder-journal.txt", limited to 1 line.
- Give me 1 line from the beginning of "cinder-journal.txt".
### coverage-v2-tail-0001 (train)

```json
{"op": "tail", "source": "cinder-journal.txt", "count": 1, "bytes": false}
```

```bash
tail -n 1 cinder-journal.txt
```

- Show the last 1 line of "cinder-journal.txt".
- Print 1 line from the end of "cinder-journal.txt".
- I only want the final 1 line from "cinder-journal.txt".
- Display the end of "cinder-journal.txt", limited to 1 line.
- Read the closing 1 line of "cinder-journal.txt".
- Give me 1 line from the bottom of "cinder-journal.txt".
### coverage-v2-head-0161 (validation)

```json
{"op": "head", "source": "verdigris-journal.txt", "count": 1, "bytes": false}
```

```bash
head -n 1 verdigris-journal.txt
```

- Return the initial 1 line of "verdigris-journal.txt".
- Take 1 line off the front of "verdigris-journal.txt" and print them.
- Present just the leading 1 line from "verdigris-journal.txt".
- Emit a 1-line prefix of "verdigris-journal.txt".
- Output only the first 1 line from "verdigris-journal.txt".
- Let me inspect the beginning of "verdigris-journal.txt": 1 line.
### coverage-v2-tail-0161 (validation)

```json
{"op": "tail", "source": "verdigris-journal.txt", "count": 1, "bytes": false}
```

```bash
tail -n 1 verdigris-journal.txt
```

- Return the terminal 1 line of "verdigris-journal.txt".
- Take 1 line off the back of "verdigris-journal.txt" and print them.
- Present just the trailing 1 line from "verdigris-journal.txt".
- Emit a 1-line suffix of "verdigris-journal.txt".
- Output only the last 1 line from "verdigris-journal.txt".
- Let me inspect the ending of "verdigris-journal.txt": 1 line.
