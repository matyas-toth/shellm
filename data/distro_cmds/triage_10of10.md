# 10/10 command triage

Proposal, 2026-10-02. Source: `intersection_10of10.txt` (157 commands). Tier A has since been implemented with one example scenario per command; see `docs/utility-command-families.md`. Tiers B and C are not implemented.

| Tier | Meaning | Count |
| --- | --- | ---: |
| Done | Already a catalog family | 14 |
| A | Deterministic, fits the Docker file/text fixtures and stdout/filesystem oracle: build these | 61 |
| B | Nondeterministic or needs process, network, or richer fixtures: later | 49 |
| C | System, privileged, or destructive: skip | 32 |
| Alias | `[` is `test` | 1 |

## Tier A: suggested capabilities per command

Each command becomes one family file. Suggested capabilities are starting points for scenarios, ordered roughly by how often people ask for them.

| Command | Suggested capabilities |
| --- | --- |
| `awk` | print-field, filter-by-field-value, sum-column, custom-delimiter |
| `sed` | substitute-first, substitute-all, delete-matching-lines, print-line-range, in-place-edit |
| `sort` | default, reverse, numeric, unique, by-field-key |
| `uniq` | dedupe-adjacent, count-occurrences, duplicates-only, unique-only |
| `cut` | field-by-delimiter, character-range, multiple-fields |
| `tr` | translate-chars, delete-chars, squeeze-repeats, case-convert |
| `paste` | merge-columns, custom-delimiter, serial |
| `nl` | number-lines, number-nonempty |
| `tac` | reverse-line-order |
| `rev` | reverse-each-line |
| `fold` | wrap-at-width, break-at-spaces |
| `expand` | tabs-to-spaces, custom-tab-width |
| `unexpand` | spaces-to-tabs |
| `comm` | common-lines, only-in-first, only-in-second |
| `od` | octal-dump, hex-dump, characters |
| `split` | by-lines, by-bytes, custom-prefix |
| `tee` | write-and-print, append |
| `xargs` | run-per-line, batch-arguments, placeholder-replace |
| `iconv` | convert-encoding |
| `base64` | encode, decode |
| `md5sum` | hash-file, hash-multiple, verify-with-check |
| `sha1sum` | hash-file, verify-with-check |
| `sha256sum` | hash-file, hash-multiple, verify-with-check |
| `sha512sum` | hash-file, verify-with-check |
| `cksum` | checksum-file |
| `sum` | checksum-file |
| `ln` | symbolic-link, hard-link, force-overwrite |
| `link` | hard-link |
| `unlink` | remove-single-file |
| `rmdir` | remove-empty-directory, remove-with-parents |
| `readlink` | link-target, canonicalize |
| `realpath` | absolute-path, relative-to |
| `basename` | strip-directory, strip-suffix |
| `dirname` | parent-directory |
| `stat` | size, octal-permissions, file-type, custom-format |
| `du` | total-size, human-readable, per-subdirectory, summary-only |
| `truncate` | set-size, extend, shrink |
| `install` | copy-with-mode, create-directories |
| `mkfifo` | create-fifo |
| `shred` | overwrite-and-remove |
| `fallocate` | preallocate-size |
| `gzip` | compress, keep-original |
| `gunzip` | decompress, keep-compressed |
| `zcat` | print-compressed-file |
| `dd` | copy-with-block-size, count-limit, skip-offset |
| `echo` | print-text, no-newline, escape-sequences |
| `printf` | format-string, multiple-arguments |
| `seq` | range, step, zero-padded |
| `expr` | arithmetic, string-length, comparison |
| `factor` | prime-factorization |
| `true` | exit-status |
| `false` | exit-status |
| `test` | file-exists, string-compare, numeric-compare |
| `yes` | repeat-text-limited |
| `sleep` | delay-seconds |
| `timeout` | limit-command-runtime |
| `env` | run-with-variable |
| `printenv` | print-one-variable |
| `whoami` | current-user |
| `id` | user-and-group-ids |
| `groups` | current-groups |

## Tier B (later)

`shuf`, `mktemp`, `mknod`, `unxz`, `xzcat`, `df`, `uname`, `nproc`, `hostid`, `date`, `uptime`, `free`, `who`, `last`, `ps`, `pgrep`, `pkill`, `kill`, `pidof`, `pwdx`, `pmap`, `top`, `watch`, `nice`, `renice`, `ionice`, `nohup`, `setsid`, `ip`, `ping`, `ldd`, `ldconfig`, `ipcs`, `ipcrm`, `flock`, `logger`, `sysctl`, `dmesg`, `getent`, `getconf`, `getopt`, `stty`, `tty`, `chgrp`, `chown`, `mountpoint`, `egrep`, `fgrep`, `more`

## Tier C (skip)

`reboot`, `halt`, `poweroff`, `init`, `chroot`, `pivot_root`, `switch_root`, `mount`, `umount`, `swapon`, `swapoff`, `mkswap`, `fsck`, `findfs`, `blkid`, `blkdiscard`, `blockdev`, `fstrim`, `losetup`, `hwclock`, `nsenter`, `unshare`, `setpriv`, `su`, `login`, `nologin`, `passwd`, `chpasswd`, `sync`, `linux32`, `linux64`, `sh`

## Already done

`ls`, `mkdir`, `touch`, `cp`, `mv`, `rm`, `cat`, `head`, `tail`, `wc`, `grep`, `find`, `chmod`, `pwd`
