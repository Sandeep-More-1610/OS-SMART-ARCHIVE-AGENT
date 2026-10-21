# Smart Archive Agent — Usage Guide

Run every command from the repository root on Linux (Ubuntu, Debian or WSL 2).

## Check the machine

```bash
python3 -m smart_archive_agent --doctor
```

Lists Python and `tar`, `gzip`, `bzip2`, `xz`, `gpg`, `file`, and prints the `sudo apt install ...` line for anything missing.

## Interactive shell

```bash
python3 -m smart_archive_agent
```

Type requests in plain English. Plans that write files are shown first and need `y`. Encryption asks for the passphrase twice with hidden input. Type `exit` to quit.

## One request

```bash
python3 -m smart_archive_agent "archive ./src with maximum compression"
python3 -m smart_archive_agent --yes "create a zip file of ./src"     # skip the confirmation
```

The exit code is 0 on success and 1 on failure.

## Request examples

| Request | Plan |
| :--- | :--- |
| `Zip up my project folder, compress it heavily, and encrypt it.` | tar.xz (xz -9e) → GPG AES-256 → delete the plaintext archive |
| `back up ./src quickly` | `src.tar.gz` at gzip -1 |
| `archive ./src to ../src.tar.bz2` | bzip2 tar archive at that path |
| `create a zip file of ./photos` | `photos.zip` |
| `compress ./data.csv as small as possible` | `data.csv.xz` at xz -9e |
| `what is inside ./photos.zip` | list entries |
| `inspect archive ./src.tar.xz` | type, entry count, preview |
| `extract ./src.tar.xz into ./restored` | safe extraction |
| `decompress ./data.csv.xz` | `data.csv` |
| `encrypt ./notes.txt` | `notes.txt.gpg` |
| `decrypt ./src.tar.xz.gpg and extract it` | decrypt → extract → delete the temporary archive |

Phrases such as "my project folder", "this folder" or "the current directory" mean the folder you are in.

## Requests that are refused

* Out of scope, e.g. `what is the weather` or `kill the process on port 8080`: these belong to other agents.
* Destructive, e.g. `rm -rf /`, `Delete everything on my drive`, `archive ./src; rm -rf ~`: blocked by the guardrail.
* Writing into system folders such as `/etc` or `/usr/bin`, overwriting an existing file, or extracting an archive whose entries escape the destination.
