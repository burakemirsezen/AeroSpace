"""Build and package the native-tab fork with SwiftPM and standard macOS tools."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def manifest_libraries():
    compiler_command = ['swiftly', 'run', '/usr/bin/which', 'swiftc'] if shutil.which('swiftly') else ['xcrun', '--find', 'swiftc']
    swiftc = Path(subprocess.check_output(compiler_command, text=True).strip())
    source = swiftc.parent.parent / 'lib/swift/pm/ManifestAPI'
    target = ROOT / '.local/swiftpm/ManifestAPI'
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
    return target.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=(ROOT / 'FORK_VERSION').read_text().strip())
    parser.add_argument('--arch', choices=['arm64', 'x86_64'])
    options = parser.parse_args()
    architecture = options.arch or subprocess.check_output(['uname', '-m'], text=True).strip()
    version = options.version
    if not version or any(char not in '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-' for char in version):
        parser.error('Version must contain only letters, numbers, dots and hyphens')

    env = os.environ.copy()
    env['SWIFTPM_CUSTOM_LIBS_DIR'] = str(manifest_libraries())
    generated = [ROOT / 'Sources/Common/versionGenerated.swift', ROOT / 'Sources/Common/gitHashGenerated.swift',
                 ROOT / 'Sources/Cli/subcommandDescriptionsGenerated.swift']
    originals = {path: path.read_bytes() for path in generated}
    swift = ['swiftly', 'run', 'swift'] if shutil.which('swiftly') else ['swift']
    try:
        run(['./generate.sh', '--ignore-xcodeproj', '--ignore-cmd-help',
             '--build-version', version, '--generate-git-hash'], env=env)
        command = [*swift, 'build', '-c', 'release', '-Xswiftc', '-warnings-as-errors']
        if options.arch:
            command += ['--arch', architecture]
        run(command, env=env)
        location_command = [*swift, 'build', '-c', 'release', '--show-bin-path']
        if options.arch:
            location_command += ['--arch', architecture]
        binary_dir = Path(subprocess.check_output(location_command, cwd=ROOT, env=env, text=True).strip())
    finally:
        for path, contents in originals.items():
            path.write_bytes(contents)

    release = ROOT / '.release'
    package = release / f'AeroSpace-v{version}-{architecture}'
    if package.exists():
        shutil.rmtree(package)
    app = package / 'AeroSpace.app/Contents'
    (app / 'MacOS').mkdir(parents=True)
    (app / 'Resources').mkdir()
    (package / 'bin').mkdir()
    shutil.copy2(binary_dir / 'AeroSpaceApp', app / 'MacOS/AeroSpace')
    shutil.copy2(binary_dir / 'aerospace', package / 'bin/aerospace')
    shutil.copy2(ROOT / 'docs/config-examples/default-config.toml', app / 'Resources/default-config.toml')
    shutil.copy2(ROOT / 'config/aerospace.toml', package / 'aerospace.toml')
    shutil.copy2(ROOT / 'LICENSE.txt', package / 'LICENSE.txt')
    shutil.copy2(ROOT / 'FORK.md', package / 'FORK.md')
    shutil.copytree(ROOT / 'legal', package / 'legal')

    # Generate a normal application icon from the original upstream asset.
    with tempfile.TemporaryDirectory(prefix='aerospace-tabs-icon-') as temporary:
        iconset = Path(temporary) / 'AppIcon.iconset'
        iconset.mkdir()
        source_icon = ROOT / 'resources/Assets.xcassets/AppIcon.appiconset/icon.png'
        for size in [16, 32, 128, 256, 512]:
            for scale in [1, 2]:
                name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
                run(['sips', '-z', str(size * scale), str(size * scale), str(source_icon),
                     '--out', str(iconset / name)], stdout=subprocess.DEVNULL)
        run(['iconutil', '-c', 'icns', str(iconset), '-o', str(app / 'Resources/AppIcon.icns')])

    with (app / 'Info.plist').open('wb') as handle:
        plistlib.dump({
            'CFBundleIdentifier': 'bobko.aerospace',
            'CFBundleExecutable': 'AeroSpace',
            'CFBundleName': 'AeroSpace',
            'CFBundleDisplayName': 'AeroSpace',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': version.split('-')[0],
            'CFBundleVersion': '2225.1',
            'CFBundleIconFile': 'AppIcon.icns',
            'LSMinimumSystemVersion': '13.0',
            'LSUIElement': True,
            'NSHighResolutionCapable': True,
        }, handle)
    (app / 'PkgInfo').write_bytes(b'APPL????')
    run(['codesign', '--force', '--sign', '-', str(package / 'AeroSpace.app')])
    run(['codesign', '--force', '--sign', '-', '--identifier', 'bobko.aerospace.cli', str(package / 'bin/aerospace')])
    run(['codesign', '--verify', '--strict', str(package / 'AeroSpace.app')])
    run(['codesign', '--verify', '--strict', str(package / 'bin/aerospace')])
    archive = release / f'{package.name}.zip'
    if archive.exists():
        archive.unlink()
    run(['ditto', '-c', '-k', '--keepParent', str(package), str(archive)])
    print(f'Packaged {archive}')


if __name__ == '__main__':
    main()
