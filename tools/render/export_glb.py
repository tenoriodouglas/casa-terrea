"""Export the house model (GLB) and tour metadata (JSON) from index.html with headless Chromium.

Usage: python export_glb.py INDEX_HTML OUT_GLB OUT_JSON
Set THREE_DIR to a local three@0.128.0 package to avoid the CDN (offline environments).
"""
import asyncio
import base64
import json
import os
import pathlib
import sys

from playwright.async_api import async_playwright

EXPORTER_CDN = 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/exporters/GLTFExporter.js'
GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


async def main(index, out_glb, out_json):
    three_dir = os.environ.get('THREE_DIR')
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get('CHROME') or None, args=GL_ARGS)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        if three_dir:
            lib = pathlib.Path(three_dir, 'build/three.min.js').read_text()
            await page.route('**/three.min.js', lambda r: r.fulfill(body=lib, content_type='application/javascript'))
        await page.goto(pathlib.Path(index).resolve().as_uri())
        await page.wait_for_function('window.HOUSE !== undefined', timeout=60000)
        if errors:
            raise SystemExit(f'Page errors: {errors}')
        if three_dir:
            await page.add_script_tag(content=pathlib.Path(three_dir, 'examples/js/exporters/GLTFExporter.js').read_text())
        else:
            await page.add_script_tag(url=EXPORTER_CDN)
        b64 = await page.evaluate("""() => new Promise(res => {
            HOUSE.roof.visible = true;
            new THREE.GLTFExporter().parse([HOUSE.world, HOUSE.roof], glb => {
                const u = new Uint8Array(glb); let s = '';
                for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
                res(btoa(s));
            }, {binary: true});
        })""")
        meta = await page.evaluate('() => ({panos: HOUSE.PANOS, renders: HOUSE.RENDERS})')
        await browser.close()
    pathlib.Path(out_glb).write_bytes(base64.b64decode(b64))
    pathlib.Path(out_json).write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print('exported', out_glb, len(meta['panos']), 'panoramas,', len(meta['renders']), 'stills')


if __name__ == '__main__':
    asyncio.run(main(*sys.argv[1:4]))
