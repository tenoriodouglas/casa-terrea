"""Render a complete new set of images and swap it into the site only when every image succeeded.

Usage: python build.py [--blender-python PATH] [--preview]
Steps: export model from index.html -> render stills + panoramas into a staging folder ->
verify the set is complete -> replace renders/ and model/casa.glb atomically -> write renders/version.json.
The site keeps showing the previous set until the swap, so visitors always see the latest finished version.
"""
import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent


def run(cmd):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blender-python', default=sys.executable, help='Python interpreter that has bpy installed')
    ap.add_argument('--preview', action='store_true', help='Low resolution and samples (pipeline test)')
    ap.add_argument('--work', default=None, help='Staging folder (default: temporary)')
    a = ap.parse_args()

    work = pathlib.Path(a.work or tempfile.mkdtemp(prefix='render-'))
    work.mkdir(parents=True, exist_ok=True)
    glb, meta, out = work / 'house.glb', work / 'house.json', work / 'png'
    commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()

    run([sys.executable, HERE / 'export_glb.py', ROOT / 'index.html', glb, meta])
    run([a.blender_python, HERE / 'render.py', glb, meta, out] + (['--preview'] if a.preview else []))

    site = json.loads(meta.read_text())
    stills = [pathlib.Path(src).stem for src, _ in site['renders']]
    expected = [out / f'{n}.png' for n in stills] + [out / 'pano' / f'{n}.png' for n in site['panos']]
    missing = [str(p.relative_to(out)) for p in expected if not p.exists()]
    if missing:
        sys.exit(f'Incomplete render set, site left unchanged. Missing: {missing}')

    # Stage JPEGs, then swap the whole folder in one step
    staged = work / 'renders'
    (staged / 'pano').mkdir(parents=True, exist_ok=True)
    for n in stills:
        Image.open(out / f'{n}.png').convert('RGB').save(staged / f'{n}.jpg', quality=88)
    for n in site['panos']:
        Image.open(out / 'pano' / f'{n}.png').convert('RGB').save(staged / 'pano' / f'{n}.jpg', quality=85)
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    (staged / 'version.json').write_text(json.dumps({'generated': stamp.isoformat(timespec='minutes'), 'source_commit': commit}, indent=1))

    target = ROOT / 'renders'
    old = ROOT / 'renders.old'
    shutil.rmtree(old, ignore_errors=True)
    if target.exists():
        target.rename(old)
    shutil.copytree(staged, target)
    shutil.rmtree(old, ignore_errors=True)
    (ROOT / 'model').mkdir(exist_ok=True)
    shutil.copy(glb, ROOT / 'model' / 'casa.glb')
    print(f'Render set swapped in: {len(stills)} stills, {len(site["panos"])} panoramas (source {commit})')


if __name__ == '__main__':
    main()
