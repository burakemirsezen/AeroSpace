# AeroSpace with native macOS tab fixes

This is an unofficial personal fork of [AeroSpace](https://github.com/nikitabobko/AeroSpace).
It carries [PR #2225](https://github.com/nikitabobko/AeroSpace/pull/2225), including
the refresh, retired-ID and cancellation fixes through `9cac62305ac405c42d7c9969a5d8b3715846fe7a`.
The patch authors retain credit in the original Git history. AeroSpace's MIT license is unchanged.

Finder and other apps expose native tabs as separate accessibility windows. This patch
replaces the previously selected tab in its existing tiling slot, so background tabs
do not consume extra space when switching tabs.

## Build

Install Swift 6.3.2, Bash 5 and macOS Command Line Tools (or Xcode), then run:

```sh
./build-native-tabs.sh
```

The script builds an optimized app and CLI for the current machine's architecture,
using SwiftPM. Output is `.release/AeroSpace-v<VERSION>-<ARCH>.zip` and the unpacked
directory alongside it. `--arch arm64` and `--arch x86_64` build a specific architecture.
Full Xcode is needed for the XCTest suite, but not for this packaging path.

Generated version/hash files are restored after compilation. The binary records
the fork version and exact Git commit. A project-local copy of SwiftPM's public
manifest interfaces handles mismatched Command Line Tools without editing system files.

## Install

Quit all AeroSpace instances. Back up `/Applications/AeroSpace.app` and
`~/.aerospace.toml`, then place the packaged `AeroSpace.app` in `/Applications`
and its `bin/aerospace` on your PATH. The app retains the ordinary bundle ID
`bobko.aerospace`, name, socket and config location, so it replaces the standard app.

The included `aerospace.toml` preserves the maintainer's keybindings and preferences,
including tiled Finder windows and `start-at-login = true`. Copy it to
`~/.aerospace.toml` if you want those settings; otherwise keep your own config.

These builds are ad-hoc signed, rather than Developer ID signed or notarized.
macOS may require renewing the AeroSpace Accessibility grant after installation
or an update. Login startup uses AeroSpace's regular `SMAppService` registration.

## Verification and limits

The patched debug app was tested on macOS 26.4.1 with two existing Finder tabs:
six native tab-control clicks retained one tiling slot, the same workspace, and
unchanged position and size. Eight small checks against the compiled production
module also passed. The full upstream XCTest gate was not run locally because only
Command Line Tools are installed. This fork intentionally has GitHub Actions disabled.

The patch still infers a handover from the previous ID disappearing from `AXWindows`.
An unrelated real window can also disappear from that list, particularly across
native macOS Spaces. Independent tab groups, detaching/closing tabs and all other
apps have not been fully verified locally. Report fork-specific issues here;
the upstream issue remains [#68](https://github.com/nikitabobko/AeroSpace/issues/68).

## Updates

Use this fork's releases or rebuild its `native-tabs` branch. Installing an upstream
Homebrew cask or upstream download over this app will replace the fork.
For development builds, `./local-build.sh` produces a separate debug app.
