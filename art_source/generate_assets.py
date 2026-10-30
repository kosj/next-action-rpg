"""Original RUNEFALL blockout art. Run: blender -b --python art_source/generate_assets.py

Hierarchy pivots intentionally remain editable: Godot animates the same named joints.
No external models, textures or motions are used. This is prototype art, not final art.
"""
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "game/assets/models"
OUT.mkdir(parents=True, exist_ok=True)


def material(name, color, metal=0.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = 0.38 if metal else 0.7
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = emission
    return mat


def joint(name, location, parent=None):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.location = location
    ob.parent = parent
    return ob


def sphere(name, location, scale, mat, parent, segments=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=8)
    ob = bpy.context.object
    ob.name = name
    ob.parent = parent
    ob.location = location
    ob.scale = scale
    ob.data.materials.append(mat)
    for polygon in ob.data.polygons:
        polygon.use_smooth = True
    return ob


def cube(name, location, scale, mat, parent, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.parent = parent
    ob.location = location
    ob.scale = scale
    ob.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = ob.modifiers.new("Forged edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def character(kind):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    hero = kind in ("hero", "keeper")
    skin = material("Warm porcelain", (0.61, 0.42, 0.32))
    dark = material("Obsidian leather", (0.035, 0.07, 0.085))
    plate = material("Moonsteel" if hero else "Ruined bronze", (0.28, 0.38, 0.41) if hero else (0.25, 0.16, 0.12), 0.65)
    gold = material("Antique gold", (0.58, 0.36, 0.13), 0.75)
    cloth = material("Teal silk" if hero else "Ash cloth", (0.035, 0.26, 0.27) if hero else (0.19, 0.045, 0.04))
    hair = material("Silver hair", (0.55, 0.64, 0.66))
    rune = material("Living rune", (0.14, 0.85, 0.74) if hero else (1.0, 0.22, 0.075), 0.35, 2.0)
    root = joint("Character", (0, 0, 0))
    torso = joint("Torso", (0, 0, 1.12), root)
    sphere("Breastplate", (0, 0, 0.22), (0.29, 0.16, 0.37), plate, torso)
    sphere("Cuirass", (0, 0, -0.03), (0.22, 0.14, 0.21), dark, torso)
    cube("Belt", (0, 0, -0.09), (0.48, 0.29, 0.065), gold, torso)
    cube("Buckle", (0, -0.165, -0.09), (0.09, 0.035, 0.09), rune, torso)
    for side in (-1, 1):
        cube("Tabard", (side * 0.16, -0.01, -0.32), (0.19, 0.25, 0.48), cloth, torso)
        sphere("Hip guard", (side * 0.24, 0, -0.13), (0.14, 0.17, 0.23), plate, torso)
        cube("Gold seam", (side * 0.14, -0.165, 0.2), (0.02, 0.02, 0.38), gold, torso)
    head = joint("Head", (0, 0, 0.52), torso)
    sphere("Neck", (0, 0, 0), (0.07, 0.07, 0.11), skin if hero else dark, head)
    sphere("Face", (0, -0.01, 0.18), (0.145, 0.125, 0.19), skin if hero else plate, head, 16)
    if hero:
        sphere("Hair cap", (0, 0.025, 0.26), (0.155, 0.13, 0.16), hair, head)
        for side in (-1, 1):
            sphere("Long hair", (side * 0.14, 0.085, -0.07), (0.075, 0.08, 0.34), hair, head)
            sphere("Eye", (side * 0.055, -0.127, 0.2), (0.025, 0.012, 0.011), dark, head)
        sphere("Nose", (0, -0.137, 0.15), (0.025, 0.03, 0.035), skin, head)
        cube("Circlet", (0, -0.117, 0.3), (0.27, 0.025, 0.03), gold, head)
        cube("Crown rune", (0, -0.14, 0.3), (0.028, 0.02, 0.07), rune, head)
    else:
        cube("Visor", (0, -0.128, 0.21), (0.22, 0.03, 0.025), rune, head)
        for side in (-1, 1):
            horn = cube("Crown spike", (side * 0.145, 0, 0.36), (0.045, 0.055, 0.32), gold, head)
            horn.rotation_euler[1] = side * 0.38
    for suffix, side in (("L", -1), ("R", 1)):
        shoulder = joint("Arm" + suffix, (side * 0.34, 0, 0.4), torso)
        sphere("Pauldron", (0, 0, -0.025), (0.16, 0.19, 0.14), plate, shoulder)
        sphere("Upper arm", (0, 0, -0.18), (0.085, 0.085, 0.18), dark, shoulder)
        elbow = joint("Elbow" + suffix, (0, 0, -0.31), shoulder)
        sphere("Bracer", (0, 0, -0.13), (0.075, 0.085, 0.16), plate, elbow)
        cube("Bracer inlay", (0, -0.08, -0.12), (0.025, 0.018, 0.17), gold, elbow)
        hand = joint("Hand" + suffix, (0, 0, -0.28), elbow)
        sphere("Hand", (0, 0, -0.045), (0.065, 0.055, 0.095), skin if hero else dark, hand)
        leg = joint("Leg" + suffix, (side * 0.14, 0, 0.95), root)
        sphere("Thigh", (0, 0, -0.2), (0.115, 0.12, 0.25), dark, leg)
        knee = joint("Knee" + suffix, (0, 0, -0.43), leg)
        sphere("Kneecap", (0, -0.04, 0), (0.105, 0.11, 0.1), plate, knee)
        sphere("Greave", (0, 0, -0.19), (0.09, 0.095, 0.21), plate, knee)
        sphere("Boot", (0, -0.07, -0.39), (0.095, 0.18, 0.085), dark, knee)
    hand = bpy.data.objects["HandR"]
    sword = joint("Sword", (0, -0.04, -0.08), hand)
    sword.rotation_euler[0] = math.radians(-55)
    # Point down and forward from hand in neutral pose.
    cube("Hilt", (0, 0, 0), (0.055, 0.055, 0.21), dark, sword)
    cube("Guard", (0, 0, -0.15), (0.32, 0.07, 0.045), gold, sword)
    blade = cube("Blade", (0, 0, -0.73), (0.11, 0.035, 1.1), plate, sword)
    cube("Blade light", (0, -0.02, -0.73), (0.027, 0.012, 1.04), rune, sword)
    if kind == "boss":
        root.scale = (1.8, 1.8, 1.8)
        for side in (-1, 1):
            spike = cube("Royal spike", (side * 0.4, 0.08, 0.58), (0.09, 0.1, 0.45), gold, torso)
            spike.rotation_euler[1] = side * 0.4
    if kind == "keeper":
        bpy.data.objects["Sword"].hide_render = True
        for child in bpy.data.objects["Sword"].children_recursive:
            child.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art_source" / (kind + ".blend")))
    bpy.ops.export_scene.gltf(filepath=str(OUT / (kind + ".glb")), export_format="GLB", export_yup=True,
                              export_animations=False, use_renderable=True)


for model in ("hero", "sentinel", "boss", "keeper"):
    character(model)
print("Exported original RUNEFALL models to", OUT)
