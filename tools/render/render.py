"""Ray-traced stills and 360 panoramas of the house (Blender Cycles via bpy).

Usage: python render.py HOUSE.glb HOUSE.json OUTDIR [shot ...] [--preview]
Shots are still names (see CAMS) or 'p:<pano>'; default renders every still listed
in the site's RENDERS plus every panorama in the site's PANOS.
"""
import json
import math
import os
import sys

import bpy
import bmesh  # must follow bpy
from mathutils import Vector

H = 3.0
args = [a for a in sys.argv[1:] if not a.startswith('--')]
GLB, META, OUT, SHOTS = args[0], args[1], args[2], args[3:]
SITE = json.load(open(META))
PREVIEW = '--preview' in sys.argv


def b(x, y, z):
    """Three.js (y-up) -> Blender (z-up)."""
    return Vector((x, -z, y))


# name: (camera pos, target, focal mm, interior)
CAMS = {
    'fachada':    ((0.8, 1.7, -7.5), (6.5, 1.7, 7.0), 22, False),
    'aerea':      ((-10, 22, -4), (6, 0, 20), 24, False),
    'fundos':     ((2.0, 1.7, 39.0), (7.0, 1.5, 28.0), 18, False),
    'sala':       ((5.5, 1.45, 8.9), (2.2, 1.0, 5.6), 15, True),
    'jantar':     ((5.6, 1.5, 13.2), (2.0, 1.0, 10.0), 15, True),
    'cozinha':    ((6.3, 1.5, 7.2), (10.0, 1.0, 12.5), 15, True),
    'gourmet':    ((7.0, 1.6, 31.6), (10.0, 1.1, 28.5), 16, False),
    'banho':      ((7.0, 1.5, 16.3), (10.2, 1.0, 17.8), 14, True),
    'master':     ((2.0, 1.5, 22.6), (5.3, 0.8, 24.5), 15, True),
    'escritorio': ((7.0, 1.5, 23.4), (10.2, 1.0, 24.6), 14, True),
    'closet':     ((6.85, 1.55, 25.15), (10.3, 0.9, 26.5), 14, True),
}
# Panorama spots come from the site itself (PANOS in index.html): name -> (x, z)
PANOS = {k: (v['x'], v['z']) for k, v in SITE['panos'].items()}
EXTERIOR = {'rua', 'gourmet', 'quintal', 'horta'}


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    fix_materials()
    refine_objects()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.use_denoising = True
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces = 8, 4, 3, 8
    cy.caustics_reflective = cy.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = (640, 360) if PREVIEW else (1600, 900)
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    setup_world(sc)
    setup_lights()


def principled(mat):
    return next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if mat.use_nodes else None


def setv(node, name, value):
    if node and name in node.inputs:
        node.inputs[name].default_value = value


def fix_materials():
    for mat in bpy.data.materials:
        key = mat.name.split('.')[0]
        p = principled(mat)
        if p is None:
            continue
        setv(p, 'Alpha', 1.0)
        if key == 'glass':
            setv(p, 'Base Color', (0.92, 0.96, 0.97, 1))
            setv(p, 'Transmission Weight', 1.0)
            setv(p, 'Roughness', 0.0)
            setv(p, 'IOR', 1.45)
        elif key == 'lamp':
            setv(p, 'Emission Color', (1.0, 0.86, 0.68, 1))
            setv(p, 'Emission Strength', 25.0)
        elif key == 'mirror':
            setv(p, 'Metallic', 1.0); setv(p, 'Roughness', 0.02)
        elif key == 'steel':
            setv(p, 'Metallic', 0.95); setv(p, 'Roughness', 0.18)
        elif key in ('porc', 'bath', 'counter', 'white'):
            setv(p, 'Roughness', 0.12 if key != 'white' else 0.2)
        elif key in ('wall', 'slab', 'muro'):
            setv(p, 'Roughness', 0.9)
        elif key == 'wood':
            setv(p, 'Roughness', 0.35)
        elif key.startswith('leaf') or key == 'grass':
            setv(p, 'Roughness', 0.7)
            setv(p, 'Subsurface Weight', 0.15)
        elif key == 'carBody':
            setv(p, 'Coat Weight', 1.0); setv(p, 'Roughness', 0.3)


def refine_objects():
    """Drop the placeholder car, round off box edges and make tree canopies organic."""
    tex = bpy.data.textures.new('canopy', 'CLOUDS'); tex.noise_scale = 0.35
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH':
            continue
        c = ob.matrix_world.translation
        keys = {m.name.split('.')[0] for m in ob.data.materials if m}
        if 9.4 < c.x < 11.7 and -5.2 < c.y < -0.3 and c.z < 1.7 and keys & {'carBody', 'tire', 'glass'}:
            bpy.data.objects.remove(ob); continue
        if keys & {'leaf', 'leaf2'} and max(ob.dimensions) > 0.35 and len(ob.data.vertices) < 400:
            bm = bmesh.new(); bm.from_mesh(ob.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(ob.data); bm.free()
            for poly in ob.data.polygons:
                poly.use_smooth = True
            ob.modifiers.new('sub', 'SUBSURF').levels = 2
            ob.modifiers['sub'].render_levels = 3
            d = ob.modifiers.new('disp', 'DISPLACE'); d.texture = tex; d.strength = 0.18 * max(ob.dimensions)
            continue
        if len(ob.data.vertices) <= 24 and min(ob.dimensions) > 0.02:
            bv = ob.modifiers.new('bevel', 'BEVEL'); bv.width = min(0.008, min(ob.dimensions) / 4); bv.segments = 2
            bv.harden_normals = False


def setup_world(sc):
    w = bpy.data.worlds.new('sky'); sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE', 'PREETHAM'):
        try:
            sky.sky_type = t
            break
        except TypeError:
            continue
    if hasattr(sky, 'sun_disc'):
        sky.sun_disc = False
    if hasattr(sky, 'sun_elevation'):
        sky.sun_elevation = math.radians(52)
        sky.sun_rotation = math.radians(-45)
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.35


def setup_lights():
    sun_dir = Vector((-14, 14, 32)).normalized()
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 4.5
    sun.data.angle = math.radians(1.0)
    sun.data.color = (1.0, 0.95, 0.88)
    sun.rotation_euler = sun_dir.to_track_quat('Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(sun)
    # One warm point light under every ceiling lamp disc of the model
    lamps = [ob for ob in bpy.data.objects if ob.type == 'MESH' and ob.dimensions.z < 0.05
             and any(m and m.name.split('.')[0] == 'lamp' for m in ob.data.materials)]
    for i, src in enumerate(lamps):
        lt = bpy.data.lights.new(f'lamp{i}', 'POINT')
        lt.energy, lt.shadow_soft_size, lt.color = 60, 0.12, (1.0, 0.82, 0.62)
        ob = bpy.data.objects.new(f'lamp{i}', lt)
        p = src.matrix_world.translation
        ob.location = (p.x, p.y, p.z - 0.25)
        bpy.context.scene.collection.objects.link(ob)


def render(name):
    pos, tgt, lens, interior = CAMS[name]
    sc = bpy.context.scene
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.lens, cam.data.sensor_width, cam.data.clip_start = lens, 36, 0.05
    cam.location = b(*pos)
    cam.rotation_euler = (b(*tgt) - b(*pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.view_settings.exposure = 1.2 if interior else 0.0
    sc.cycles.samples = 32 if PREVIEW else (80 if interior else 48)
    sc.render.filepath = f'{OUT}/{name}.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name, flush=True)


def render_pano(name):
    x, z = PANOS[name]
    sc = bpy.context.scene
    cam = bpy.data.objects.get('pcam') or bpy.data.objects.new('pcam', bpy.data.cameras.new('pcam'))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = 'PANO'
    if hasattr(cam.data, 'panorama_type'):
        cam.data.panorama_type = 'EQUIRECTANGULAR'
    else:
        cam.data.cycles.panorama_type = 'EQUIRECTANGULAR'
    cam.data.clip_start = 0.05
    cam.location = b(x, 1.55, z)
    cam.rotation_euler = (math.radians(90), 0, 0)  # looks along Three.js -z (toward the street)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = (512, 256) if PREVIEW else (2048, 1024)
    sc.view_settings.exposure = 0.0 if name in EXTERIOR else 1.1
    sc.cycles.samples = 8 if PREVIEW else 32
    sc.render.filepath = f'{OUT}/pano/{name}.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name, flush=True)


def default_shots():
    stills = [os.path.splitext(os.path.basename(src))[0] for src, _ in SITE['renders']]
    missing = [n for n in stills if n not in CAMS]
    if missing:
        sys.exit(f'No camera defined for renders: {missing}')
    return stills + [f'p:{p}' for p in PANOS]


os.makedirs(OUT, exist_ok=True)
setup_scene()
for s in SHOTS or default_shots():
    if s.startswith('p:'):
        render_pano(s[2:])
    else:
        render(s)
