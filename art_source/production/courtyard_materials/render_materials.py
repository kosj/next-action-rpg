"""Render the runtime PBR maps under neutral studio light in Blender 4.3+."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def pbr_material(root, entry):
    material = bpy.data.materials.new(entry["asset_id"])
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    maps = {}
    for source in entry["maps"]:
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(root / source["path"]), check_existing=True)
        if source["channel"] != "Diffuse":
            node.image.colorspace_settings.name = "Non-Color"
        node.label = source["channel"]
        maps[source["channel"]] = node
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(maps["arm"].outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    # Match the runtime nonmetallic surface and moderate crevice darkening.
    shader.inputs["Metallic"].default_value = 0.0
    ao = nodes.new("ShaderNodeMixRGB")
    ao.blend_type = "MULTIPLY"
    ao.inputs[0].default_value = 0.65
    links.new(maps["Diffuse"].outputs["Color"], ao.inputs[1])
    links.new(split.outputs["Red"], ao.inputs[2])
    links.new(ao.outputs["Color"], shader.inputs["Base Color"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.8 if entry["key"] == "wall" else 0.9
    links.new(maps["nor_gl"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return material


def slab(name, position, dimensions, material, tile_meters):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    uv = obj.data.uv_layers.active.data
    # Physical UV scale on each planar face, also used by the rounded sample.
    for face in obj.data.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        axes = (0, 1) if axis == 2 else ((0, 2) if axis == 1 else (1, 2))
        for loop_index in face.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv[loop_index].uv = (co[axes[0]] / tile_meters, co[axes[1]] / tile_meters)
    bevel = obj.modifiers.new("Small physical edge radius", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 3
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="build/art-review/courtyard-materials/material-review.png")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    # Debian's CPU Blender build may omit OpenImageDenoise.
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    world = bpy.data.worlds.new("Neutral studio world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.28, 0.31, 0.36, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.45

    neutral = bpy.data.materials.new("Review base")
    neutral.diffuse_color = (0.075, 0.085, 0.10, 1)
    slab("Neutral studio base", (0, 0, -0.22), (200, 200, 0.2), neutral, 1)
    labels = ["WEATHERED FLAGSTONE / 1.8 m", "PALE SANDSTONE / 2.0 m", "FOREST SOIL / 2.0 m"]
    for i, entry in enumerate(manifest["sets"]):
        x = (i - 1) * 3.6
        material = pbr_material(root, entry)
        slab(entry["key"] + " tile", (x, 0, -0.06), (3.2, 3.2, 0.18), material, entry["tile_meters"][0])
        slab(entry["key"] + " light response sample", (x, 0.65, 0.46), (1.35, 1.05, 0.85), material, entry["tile_meters"][0])
        bpy.ops.object.text_add(location=(x - 1.53, -1.86, 0.015))
        text = bpy.context.object
        text.name = labels[i]
        text.data.body = labels[i]
        text.data.size = 0.145
        text.data.extrude = 0.001
        text.rotation_euler = (0, 0, 0)
        label_mat = bpy.data.materials.new("Label " + str(i))
        label_mat.diffuse_color = (0.65, 0.70, 0.73, 1)
        text.data.materials.append(label_mat)

    for name, pos, power, size, color in [
        ("Large neutral key", (-3, -4, 7), 1500, 6.0, (1.0, 0.96, 0.89)),
        ("Sky fill", (4, 2, 5), 950, 5.0, (0.83, 0.9, 1.0)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = pos
        point_at(light, (0, 0, 0))

    data = bpy.data.cameras.new("Material review camera")
    camera = bpy.data.objects.new("Material review camera", data)
    scene.collection.objects.link(camera)
    camera.location = (5.5, -8.5, 7.0)
    point_at(camera, (0, 0, 0.1))
    data.type = "ORTHO"
    data.ortho_scale = 11.8
    scene.camera = camera
    bpy.ops.render.render(write_still=True)
    print("MATERIAL_REVIEW_RENDER", output)


if __name__ == "__main__":
    main()
