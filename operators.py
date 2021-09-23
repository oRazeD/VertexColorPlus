
import bpy, bmesh, colorsys, bpy_extras
from bpy.types import Operator
from random import random


################################################################################################################
# FUNCTIONS & OPERATORS
################################################################################################################


class OpInfo: # Mix-in class
    bl_options = {'REGISTER', 'UNDO'}


# Convert custom datatypes to plain 4-size arrays
def convert_to_plain_array(array_object):
    converted_array = [array_object[0], array_object[1], array_object[2], array_object[3]]
    return converted_array


# Get VColor Set/Layer or generate one if it doesn't already exist
def find_or_create_vcolor_set(bm, active_ob):
    if not active_ob.data.vertex_colors:
        color_layer = bm.loops.layers.color.new("Col")

        layer = bm.loops.layers.color[color_layer.name]
    else:
        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]
    return layer


class VCOLORPLUS_OT_edit_color(OpInfo, Operator):
    """Edits the active vertex color set based on the selected operator"""
    bl_idname = "vcolor_plus.edit_color"
    bl_label = "Fill Selection"

    edit_type: bpy.props.EnumProperty(
        items=(
            ('apply', "Apply", ""),
            ('apply_all', "Apply All", ""),
            ('clear', "Clear", ""),
            ('clear_all', "Clear All", "")
        ),
        options={'HIDDEN'}
    )

    variation_value: bpy.props.StringProperty(options={'HIDDEN'})
    
    def change_vcolor(self, context, layer, loop, rgb_value):
        if self.edit_type == 'apply' and loop.vert.select or self.edit_type == 'apply_all':
            loop[layer] = rgb_value

        elif self.edit_type == 'clear' and loop.vert.select or self.edit_type == 'clear_all':
            loop[layer] = [1,1,1,1]

    def execute(self, context):
        vcolor_plus = context.scene.vcolor_plus
        saved_context_mode = context.object.mode

        bpy.ops.object.mode_set(mode = 'OBJECT')

        for ob in context.selected_objects:
            if ob.type == 'MESH':
                bm = bmesh.new()
                bm.from_mesh(ob.data)

                # Get the RGB value based on the property string given
                if self.variation_value:
                    if self.variation_value.startswith('color_var'):
                        variation_prop = getattr(vcolor_plus, self.variation_value)

                        rgb_value = (variation_prop[0], variation_prop[1], variation_prop[2], vcolor_plus.color_wheel[3])
                    else:
                        rgb_value = getattr(vcolor_plus, self.variation_value)
                else:
                    rgb_value = [1,1,1,1]

                layer = find_or_create_vcolor_set(bm, ob)

                # Get application type (smooth/hard) and then apply to the corresponding geometry
                if vcolor_plus.interpolation_type == 'hard':
                    for face in bm.faces:
                        if face.select or self.edit_type == 'clear_all':
                            for loop in face.loops:
                                self.change_vcolor(context, layer=layer, loop=loop, rgb_value=rgb_value)
                else: # Smooth
                    for face in bm.faces:
                        for loop in face.loops:
                            self.change_vcolor(context, layer=layer, loop=loop, rgb_value=rgb_value)

                bm.to_mesh(ob.data)

        bpy.ops.object.mode_set(mode = saved_context_mode)

        bpy.ops.vcolor_plus.refresh_palette_outliner()
        return {'FINISHED'}


class VCOLORPLUS_OT_edit_color_keymap_placeholder(OpInfo, Operator):
    bl_idname = "vcolor_plus.edit_color_clear"
    bl_label = "Clear Selection"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.ops.vcolor_plus.edit_color(edit_type='clear')
        return {'FINISHED'}


class VCOLORPLUS_OT_quick_color_switch(OpInfo, Operator):
    """Switch between your main and alternate color"""
    bl_idname = "vcolor_plus.quick_color_switch"
    bl_label = ""

    def execute(self, context):
        vcolor_plus = context.scene.vcolor_plus

        saved_color_tweak = vcolor_plus.live_color_tweak
        vcolor_plus.live_color_tweak = False

        saved_main_color = convert_to_plain_array(array_object=vcolor_plus.color_wheel)
        saved_alt_color = convert_to_plain_array(array_object=vcolor_plus.alt_color_wheel)

        vcolor_plus.color_wheel = saved_alt_color
        vcolor_plus.alt_color_wheel = saved_main_color

        vcolor_plus.live_color_tweak = saved_color_tweak

        if vcolor_plus.live_color_tweak:
            bpy.ops.vcolor_plus.edit_color(edit_type='apply', variation_value='color_wheel')
        return {'FINISHED'}


class VCOLORPLUS_OT_quick_interpolation_switch(OpInfo, Operator):
    """Switch the shading interpolation between smooth and hard"""
    bl_idname = "vcolor_plus.quick_interpolation_switch"
    bl_label = "Smooth/Hard Switch"

    def execute(self, context):
        vcolor_plus = context.scene.vcolor_plus

        if vcolor_plus.interpolation_type == 'smooth':
            vcolor_plus.interpolation_type = 'hard'
        else:
            vcolor_plus.interpolation_type = 'smooth'
        return {'FINISHED'}


class VCOLORPLUS_OT_get_active_color(OpInfo, Operator):
    """Set the Active Color based on the actively selected vertex color on the mesh"""
    bl_idname = "vcolor_plus.get_active_color"
    bl_label = "Color from Active Vertex"

    def execute(self, context):
        active_ob = context.object

        if not active_ob.data.vertex_colors:
            context.scene.vcolor_plus.color_wheel = (1, 1, 1, 1)
            return {'FINISHED'}

        bm = bmesh.from_edit_mesh(active_ob.data)

        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]

        # Search select_history for the active vertex
        try:
            active_selection = bm.select_history[-1]
        except IndexError:
            self.report({'ERROR'}, "There is no Active Vertex selected")
            return{'CANCELLED'}

        # Haven't actually tested what this is for, maybe instancing?
        if not isinstance(active_selection, bmesh.types.BMVert):
            self.report({'ERROR'}, "There is more than one Active Vertex selected, please select only one active vertex")
            return{'CANCELLED'}

        # Get active vertex's color
        for face in bm.faces:
            for loop in face.loops:
                # TODO Make a list of the vert colors in this list, choose the first one that isn't pure white?

                if loop.vert.select and loop.vert == active_selection:
                    context.scene.vcolor_plus.color_wheel = loop[layer]
        return {'FINISHED'}


class VCOLORPLUS_OT_vcolor_shading(OpInfo, Operator):
    """Sets the current viewport shading to something more suitable for vertex painting (WARNING: This operation is destructive and won't save existing shading settings)"""
    bl_idname = "vcolor_plus.vcolor_shading"
    bl_label = "Apply VColor Shading"

    def execute(self, context):
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'VERTEX'
        return {'FINISHED'}


class VCOLORPLUS_OT_value_variation(OpInfo, Operator):
    """Applies value variation to the selection without the need to change the Active Color"""
    bl_idname = "vcolor_plus.value_variation"
    bl_label = ""

    variation_value: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        bpy.ops.vcolor_plus.edit_color(edit_type='apply', variation_value=self.variation_value)
        return {'FINISHED'}


class VCOLORPLUS_OT_refresh_palette_outliner(OpInfo, Operator):
    """Refresh the palette outliner of the Active Object"""
    bl_idname = "vcolor_plus.refresh_palette_outliner"
    bl_label = "Refresh Palette"

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type == 'MESH':
                # Clear palette outliner list
                ob.vcolor_plus_palette_coll.clear()

                bm = bmesh.from_edit_mesh(ob.data)

                layer = find_or_create_vcolor_set(bm, ob)

                # Preserve the original index color value
                if len(ob.vcolor_plus_palette_coll):
                    saved_color = convert_to_plain_array(array_object=ob.vcolor_plus_palette_coll[ob.vcolor_plus_custom_index].color)

                vcolor_list = []

                for face in bm.faces:
                    for loop in face.loops:
                        reconstructed_loop = convert_to_plain_array(array_object=loop[layer])

                        if reconstructed_loop not in vcolor_list and reconstructed_loop != [1,1,1,1]:
                            vcolor_list.append(reconstructed_loop)

                # TODO Order vcolor_list based on hue, and then value
                #vcolor_list_hsv = [colorsys.rgb_to_hsv(vcolor[0], vcolor[1], vcolor[2]) for vcolor in vcolor_list]

                # Generate palette outliner properties
                for vcolor in vcolor_list:
                    item = ob.vcolor_plus_palette_coll.add()
                    item.id = len(ob.vcolor_plus_palette_coll) - 1
                    item.saved_color = vcolor
                    item.color = vcolor

                    if context.scene.vcolor_plus.rgb_hsv_convert_options == 'rgb':
                        item.name = f'({round(vcolor[0] * 255)}, {round(vcolor[1] * 255)}, {round(vcolor[2] * 255)}, {round(vcolor[3], 2)})'
                    else:
                        vcolor_hsv = colorsys.rgb_to_hsv(vcolor[0], vcolor[1], vcolor[2])

                        item.name = f'({round(vcolor_hsv[0], 2)}, {round(vcolor_hsv[1], 2)}, {round(vcolor_hsv[2], 2)}, {round(vcolor[3], 2)})'

                # Reconfigure the active color palette based on previously saved color info
                if ob.vcolor_plus_custom_index != 0:
                    ob.vcolor_plus_custom_index += -1

                if 'saved_color' in locals():
                    for vcolor in ob.vcolor_plus_palette_coll:
                        converted_vcolor = convert_to_plain_array(array_object=vcolor.color)

                        if converted_vcolor == saved_color:
                            ob.vcolor_plus_custom_index = vcolor.id
                            break
        return {'FINISHED'}


class VCOLORPLUS_OT_change_outliner_color(OpInfo, Operator):
    bl_idname = "vcolor_plus.change_outliner_color"
    bl_label = ""
    bl_options = {'INTERNAL'}

    id: bpy.props.IntProperty()

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[self.id]

        bm = bmesh.from_edit_mesh(active_ob.data)

        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]

        palette_saved_color = convert_to_plain_array(array_object=active_palette.saved_color)
        palette_color = convert_to_plain_array(array_object=active_palette.color)

        for face in bm.faces:
            for loop in face.loops:
                reconstructed_loop = convert_to_plain_array(array_object=loop[layer])

                if reconstructed_loop == palette_saved_color:
                    loop[layer] = palette_color

        active_palette.name = f'({round(palette_color[0] * 255)}, {round(palette_color[1] * 255)}, {round(palette_color[2] * 255)}, {round(palette_color[3], 2)})'

        bmesh.update_edit_mesh(active_ob.data)
        return {'FINISHED'}


class VCOLORPLUS_OT_get_active_outliner_color(OpInfo, Operator):
    """Apply the Outliner Color to the Active Color"""
    bl_idname = "vcolor_plus.get_active_outliner_color"
    bl_label = "Set as Active Color"

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[active_ob.vcolor_plus_custom_index].color

        context.scene.vcolor_plus.color_wheel = active_palette
        return {'FINISHED'}


class VCOLORPLUS_OT_apply_outliner_color(OpInfo, Operator):
    """Apply the Outliner Color to the selected geometry"""
    bl_idname = "vcolor_plus.apply_outliner_color"
    bl_label = "Apply Outliner Color"

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[active_ob.vcolor_plus_custom_index].color

        # Set the temporary property
        context.scene.vcolor_plus.overlay_color_placeholder = active_palette

        bpy.ops.vcolor_plus.edit_color(edit_type='apply', variation_value='overlay_color_placeholder') # TODO This still uses selected_objects
        return {'FINISHED'}


class VCOLORPLUS_OT_select_outliner_color(OpInfo, Operator):
    """Select vertices based on the Outliner Color (WARNING: This does not remove your existing selection)"""
    bl_idname = "vcolor_plus.select_outliner_color"
    bl_label = "Select Geometry from Outliner Color"

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[active_ob.vcolor_plus_custom_index]
        saved_context_mode = active_ob.mode

        bpy.ops.object.mode_set(mode = 'OBJECT')

        # Object mode BMesh correct mesh update
        bm = bmesh.new()
        bm.from_mesh(active_ob.data)

        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]
        
        context.tool_settings.mesh_select_mode = (True, False, False)

        reconstructed_palette_loop = convert_to_plain_array(array_object=active_palette.color)

        for face in bm.faces:
            for loop in face.loops:
                reconstructed_loop = convert_to_plain_array(array_object=loop[layer])

                if reconstructed_loop == reconstructed_palette_loop:
                    loop.vert.select_set(True)

        bm.to_mesh(active_ob.data)

        bpy.ops.object.mode_set(mode = saved_context_mode)
        return {'FINISHED'}


class VCOLORPLUS_OT_delete_outliner_color(OpInfo, Operator):
    """Remove the Outliner Color from the Palette Outliner and geometry"""
    bl_idname = "vcolor_plus.delete_outliner_color"
    bl_label = "Delete Outliner Color"

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[active_ob.vcolor_plus_custom_index]

        bm = bmesh.from_edit_mesh(active_ob.data)

        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]

        reconstructed_palette_loop = convert_to_plain_array(array_object=active_palette.color)

        for face in bm.faces:
            for loop in face.loops:
                reconstructed_loop = convert_to_plain_array(array_object=loop[layer])

                if reconstructed_loop == reconstructed_palette_loop:
                    loop[layer] = [1, 1, 1, 1]

        bmesh.update_edit_mesh(active_ob.data)

        bpy.ops.vcolor_plus.refresh_palette_outliner()
        return {'FINISHED'}


class VCOLORPLUS_OT_convert_to_vgroup(OpInfo, Operator):
    """Convert the Outliner Color to a single Vertex Group"""
    bl_idname = "vcolor_plus.convert_to_vgroup"
    bl_label = "Convert to Vertex Group"

    def execute(self, context):
        active_ob = context.object
        active_palette = active_ob.vcolor_plus_palette_coll[active_ob.vcolor_plus_custom_index]
        saved_context_mode = active_ob.mode

        bpy.ops.object.mode_set(mode = 'OBJECT')

        # Object mode BMesh for vgroup add (only works in ob mode)
        bm = bmesh.new()
        bm.from_mesh(active_ob.data)

        layer = bm.loops.layers.color[active_ob.data.vertex_colors.active.name]

        vertex_list = []

        reconstructed_palette_loop = convert_to_plain_array(array_object=active_palette.color)

        # Get vertices with the corresponding color value
        for face in bm.faces:
            for loop in face.loops:
                if loop.vert.index not in vertex_list:
                    reconstructed_loop = convert_to_plain_array(array_object=loop[layer])

                    if reconstructed_loop == reconstructed_palette_loop:
                        vertex_list.append(loop.vert.index)

        converted_vgroup = active_ob.vertex_groups.new(name=active_palette.name)
        converted_vgroup.add(vertex_list, 1.0, 'ADD')

        bpy.ops.object.mode_set(mode = saved_context_mode)
        return {'FINISHED'}


class VCOLORPLUS_OT_custom_color_apply(OpInfo, Operator):
    """Apply the color to your current selection/Active Color"""
    bl_idname = "vcolor_plus.custom_color_apply"
    bl_label = ""

    custom_color_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        vcolor_plus = context.scene.vcolor_plus

        if vcolor_plus.custom_palette_apply_options == 'apply_to_sel':
            bpy.ops.vcolor_plus.edit_color(edit_type='apply', variation_value=self.custom_color_name)
        else: # Apply to Active Color
            vcolor_plus.color_wheel = getattr(vcolor_plus, self.custom_color_name)

            bpy.ops.vcolor_plus.refresh_palette_outliner()
        return {'FINISHED'}


class VCOLORPLUS_OT_apply_color_to_border(OpInfo, Operator):
    """Apply a VColor to the border or bounds of your current selection"""
    bl_idname = "vcolor_plus.apply_color_to_border"
    bl_label = "Apply to Selection Border"

    border_type: bpy.props.EnumProperty(
        items=(
            ('inner', "Inner", ""),
            ('outer', "Outer", "")
        )
    )

    def execute(self, context):
        saved_context_mode = context.object.mode

        bpy.ops.object.mode_set(mode = 'OBJECT')

        for ob in context.selected_objects:
            if ob.type == 'MESH':
                bm = bmesh.new()
                bm.from_mesh(ob.data)

                layer = find_or_create_vcolor_set(bm, ob)

                # Get border vertices & linked faces
                border_vertices = []
                linked_faces = []

                for edge in bm.edges:
                    if edge.select:
                        if edge.is_boundary or edge.link_faces[0].select != edge.link_faces[1].select:
                            border_vertices.append(list(edge.verts))

                            linked_faces.extend(list(edge.link_faces))

                #border_vertices = [list(edge.verts) for edge in bm.edges if edge.link_faces[0].select != edge.link_faces[1].select]
                #                  ^^ can also use [*edge.verts] for unpacking every item into an iterable

                # Remove duplicate verts from the list
                border_vertices_no_dups = []

                for vertices in border_vertices:
                    for vert in vertices:
                        if vert not in border_vertices_no_dups:
                            border_vertices_no_dups.append(vert.index)

                # Search linked faces for loops on the correct sides of the vertices
                if self.border_type == 'inner':
                    for face in linked_faces:
                        if face.select:
                            for loop in face.loops:
                                if loop.vert.index in border_vertices_no_dups:
                                    loop[layer] = context.scene.vcolor_plus.color_wheel
                else:
                    for face in linked_faces:
                        if not face.select:
                            for loop in face.loops:
                                if loop.vert.index in border_vertices_no_dups:
                                    loop[layer] = context.scene.vcolor_plus.color_wheel

                bm.to_mesh(ob.data)

        bpy.ops.object.mode_set(mode = saved_context_mode)

        bpy.ops.vcolor_plus.refresh_palette_outliner()
        return {'FINISHED'}


class VCOLORPLUS_OT_generate_vcolor(OpInfo, Operator):
    """Generate a VColor mask based on the settings below"""
    bl_idname = "vcolor_plus.generate_vcolor"
    bl_label = ""

    def execute(self, context):
        vcolor_plus = context.scene.vcolor_plus
        saved_context_mode = context.object.mode

        bpy.ops.object.mode_set(mode = 'OBJECT')

        no_uv_obs = []

        for ob in context.selected_objects:
            if ob.type == 'MESH':
                try:
                    uv_islands = bpy_extras.mesh_utils.mesh_linked_uv_islands(ob.data)
                except AttributeError:
                    no_uv_obs.append(ob.name)
                    continue

                bm = bmesh.new()
                bm.from_mesh(ob.data)
                bm.faces.ensure_lookup_table()

                layer = find_or_create_vcolor_set(bm, ob)

                if vcolor_plus.generation_type == 'per_uv_shell':
                    for island_idx in uv_islands:
                        random_color = [random(), random(), random(), 1]

                        for face_idx in island_idx:
                            face = bm.faces[face_idx]

                            for loop in face.loops:
                                loop[layer] = random_color

                elif vcolor_plus.generation_type == 'per_uv_border':
                    for island_idx in uv_islands:
                        random_color = [random(), random(), random(), 1]
                            
                        # Get border vertices & linked faces
                        border_vertices = []
                        linked_faces = []

                        for edge in bm.edges:
                            if (
                                edge.is_boundary
                                or (edge.link_faces[0].index == island_idx and edge.link_faces[1].index != island_idx)
                                or (edge.link_faces[0].index != island_idx and edge.link_faces[1].index == island_idx)
                            ):
                                border_vertices.append(list(edge.verts))

                                linked_faces.extend(list(edge.link_faces))

                        border_vertices_no_dups = []

                        for vertices in border_vertices:
                            for vert in vertices:
                                if vert not in border_vertices_no_dups:
                                    border_vertices_no_dups.append(vert.index)

                        for face in linked_faces:
                            if face.index in island_idx:
                                for loop in face.loops:
                                    if loop.vert.index in border_vertices_no_dups:
                                        if vcolor_plus.generation_per_uv_border_options == 'random_col':
                                            loop[layer] = random_color
                                        else: # Active color
                                            loop[layer] = context.scene.vcolor_plus.color_wheel

                bm.to_mesh(ob.data)

        if len(no_uv_obs):
            self.report({'INFO'}, f"UVs not found for: {no_uv_obs}")

        bpy.ops.object.mode_set(mode = saved_context_mode)

        bpy.ops.vcolor_plus.refresh_palette_outliner()
        return {'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    VCOLORPLUS_OT_edit_color,
    VCOLORPLUS_OT_edit_color_keymap_placeholder,
    VCOLORPLUS_OT_quick_color_switch,
    VCOLORPLUS_OT_quick_interpolation_switch,
    VCOLORPLUS_OT_get_active_color,
    VCOLORPLUS_OT_vcolor_shading,
    VCOLORPLUS_OT_value_variation,
    VCOLORPLUS_OT_refresh_palette_outliner,
    VCOLORPLUS_OT_change_outliner_color,
    VCOLORPLUS_OT_get_active_outliner_color,
    VCOLORPLUS_OT_apply_outliner_color,
    VCOLORPLUS_OT_select_outliner_color,
    VCOLORPLUS_OT_delete_outliner_color,
    VCOLORPLUS_OT_convert_to_vgroup,
    VCOLORPLUS_OT_custom_color_apply,
    VCOLORPLUS_OT_apply_color_to_border,
    VCOLORPLUS_OT_generate_vcolor
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
