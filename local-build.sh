#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --test ) ]]; then
    echo 'Usage: ./local-build.sh [--test]' >&2
    exit 2
fi

# Keep the workaround for mismatched CLT manifest interfaces inside this checkout.
# Use the public interfaces that match libPackageDescription; do not modify CLT.
python3 - <<'PY'
from pathlib import Path
import shutil
import subprocess

swiftc = Path(subprocess.check_output(['xcrun', '--find', 'swiftc'], text=True).strip())
source = swiftc.parent.parent / 'lib/swift/pm/ManifestAPI'
target = Path('.local/swiftpm/ManifestAPI')
target.mkdir(parents=True, exist_ok=True)
for item in source.iterdir():
    dest = target / item.name
    if item.is_dir():
        shutil.copytree(item, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.private.swiftinterface'))
    elif item.name == 'libPackageDescription.dylib':
        if dest.is_symlink():
            dest.unlink()
        dest.symlink_to(item)
PY
export SWIFTPM_CUSTOM_LIBS_DIR="$PWD/.local/swiftpm"

./generate.sh --ignore-xcodeproj --ignore-cmd-help
swift build -Xswiftc -warnings-as-errors

python3 - <<'PY'
from pathlib import Path
import plistlib
import shutil

app = Path('.local/AeroSpace-Debug.app/Contents')
(app / 'MacOS').mkdir(parents=True, exist_ok=True)
(app / 'Resources').mkdir(parents=True, exist_ok=True)
Path('.local/bin').mkdir(parents=True, exist_ok=True)
shutil.copy2('.build/debug/AeroSpaceApp', app / 'MacOS/AeroSpace')
shutil.copy2('.build/debug/aerospace', '.local/bin/aerospace')
shutil.copy2('docs/config-examples/default-config.toml', app / 'Resources/default-config.toml')
with (app / 'Info.plist').open('wb') as handle:
    plistlib.dump({
        'CFBundleIdentifier': 'bobko.aerospace.debug',
        'CFBundleExecutable': 'AeroSpace',
        'CFBundleName': 'AeroSpace-Debug',
        'CFBundleDisplayName': 'AeroSpace Tabs (Debug)',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': '0.0.0',
        'CFBundleVersion': '2225',
        'LSMinimumSystemVersion': '13.0',
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    }, handle)
PY
codesign --force --sign - .local/AeroSpace-Debug.app
codesign --verify --strict .local/AeroSpace-Debug.app
echo "Built: $PWD/.local/AeroSpace-Debug.app"

if [[ "${1:-}" == --test ]]; then
    ./test.sh
fi
