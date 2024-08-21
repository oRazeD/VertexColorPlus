import colorsys
from random import random

import bpy
import bpy_extras
import bmesh
from bpy.types import Operator, Object, Context
from bpy.props import FloatVectorProperty

from .functions import (
    iterable_to_list,
    create_color,
    get_active_color,
    get_bmesh_active_color,
    get_component_colors
)
from .constants import BLANK_ARRAY


# TODO:
# - Basic blend modes (Replace, multiply, subtract)
#   - https://stackoverflow.com/questions/726549/algorithm-for-additive-color-mixing-for-rgb-valuess
# - Vertex color set syncing
#   - This would be useful for forcing use of the active color set
#     when working with multiple objects, objects without a matching
#     color set should have a new set made with identical rendering
#     and stack priority (if possible)


#########################################
# OPERATORS
#########################################


class DefaultsOperator(Operator): # Mix-in class
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = ""


class COLORPLUS_OT_toggle_vertex_paint_mode(DefaultsOperator):
    """Toggle between vertex paint and edit mode. Syncs brush settings"""
    bl_idname = "color_plus.toggle_vertex_paint_mode"

    def execute(self, context: Context):
        color_plus = context.scene.color_plus

        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'VERTEX'

        # NOTE: Poor way to sync these values but is what it is
        if context.mode == 'PAINT_VERTEX':
            brush_color = bpy.data.brushes["Draw"].color
            color_plus.color_wheel = (
                brush_color[0], brush_color[1],
                brush_color[2], color_plus.color_wheel[3]
            )
            bpy.ops.object.mode_set(mode='EDIT')
        else:
            bpy.data.brushes["Draw"].color = (
                color_plus.color_wheel[0],
                color_plus.color_wheel[1],
                color_plus.color_wheel[2]
            )
            bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        return {'FINISHED'}


class COLORPLUS_OT_edit_color(DefaultsOperator):
    """Edits the active vertex color set based on the selected operator"""
    bl_idname = "color_plus.edit_color"
    bl_label = "Paint Selection"

    edit_type: bpy.props.EnumProperty(
        items=(
            ('apply', "Apply", ""),
            ('apply_all', "Apply All", ""),
            ('clear', "Clear", ""),
            ('clear_all', "Clear All", "")
        ),
        options={'HIDDEN'}
    ) # type: ignore

    variation_value: bpy.props.StringProperty(options={'HIDDEN'})

    def change_color(self, component, layer, rgba_value) -> None:
        """Change a vert/loop components color attribute."""
        if self.edit_type in ('clear', 'clear_all'):
            component[layer] = BLANK_ARRAY
            return

        for idx, value in enumerate(rgba_value):
            if value is None:
                rgba_value[idx] = component[layer][idx]

        if self.variation_value == 'alpha_only':
            component[layer] = (
                component[layer][0], component[layer][1],
                component[layer][2], rgba_value[3]
            )
        elif self.variation_value == 'color_only':
            component[layer] = (
                rgba_value[0], rgba_value[1],
                rgba_value[2], component[layer][3]
            )
        elif self.variation_value == 'visibility':
            color_plus = bpy.context.scene.color_plus
            vis_color = color_plus.material_visibility
            component[layer] = (float(vis_color), 0, 0, 1)
        else:
            component[layer] = rgba_value

    def execute(self, context: Context):
        color_plus = context.scene.color_plus

        saved_mode=context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        context.object.select_set(True)

        # Get the RGB value based on the property given
        rgba_value = BLANK_ARRAY
        if self.variation_value:
            try:
                rgba_value = getattr(color_plus, self.variation_value)
            except AttributeError:
                rgba_value = getattr(color_plus, 'color_wheel')
            if self.variation_value == 'value_var':
                rgba_value = \
                    [rgba_value[0], rgba_value[1], rgba_value[2], None]
            elif self.variation_value == 'alpha_var':
                rgba_value = [None, None, None, rgba_value[3]]

        use_selected = not "_all" in self.edit_type

        selected_mesh_objects = \
            [ob for ob in context.selected_objects if ob.type == 'MESH']
        for ob in selected_mesh_objects:
            active_color = get_active_color(ob.data)
            if active_color is None:
                active_color = create_color(ob.data)

            bm = bmesh.new()
            bm.from_mesh(ob.data)
            layer, layer_type = get_bmesh_active_color(bm, ob.data)
            components = \
                get_component_colors(bm, layer, layer_type, use_selected)
            for component, _color in components.items():
                # Smooth
                if color_plus.interp_type == "smooth" \
                        or active_color.domain != 'CORNER':
                    if layer_type == "loop":
                        for loop in component.vert.link_loops:
                            self.change_color(loop, layer, rgba_value)
                    else:  # Vert
                        self.change_color(component, layer, rgba_value)
                # Hard
                elif color_plus.interp_type == "hard":
                    if use_selected and component.face.select:
                        for loop in component.face.loops:
                            self.change_color(component, layer, rgba_value)
            bm.to_mesh(ob.data)

        bpy.ops.object.mode_set(mode=saved_mode)
        preferences = \
            context.preferences.addons[__package__].preferences
        if preferences.auto_palette_refresh:
            bpy.ops.color_plus.refresh_palette_outliner(color=rgba_value)
        return {'FINISHED'}


class COLORPLUS_OT_edit_color_keymap_placeholder(DefaultsOperator):
    bl_idname = "color_plus.edit_color_clear"
    bl_label = "Clear Selection"
    bl_options = {'INTERNAL'}

    def execute(self, context: Context):
        bpy.ops.color_plus.edit_color(edit_type='clear')
        return {'FINISHED'}


class COLORPLUS_OT_active_color_switch(DefaultsOperator):
    """Switch between your main and alternate color"""
    bl_idname = "color_plus.active_color_switch"

    def execute(self, context: Context):
        color_plus = context.scene.color_plus
        saved_color_tweak = color_plus.live_color_tweak
        color_plus.live_color_tweak = False
        color_wheel = iterable_to_list(color_plus.color_wheel)
        alt_color_wheel = iterable_to_list(color_plus.alt_color_wheel)
        color_plus.color_wheel = alt_color_wheel
        color_plus.alt_color_wheel = color_wheel
        color_plus.live_color_tweak = saved_color_tweak
        return {'FINISHED'}


class COLORPLUS_OT_interpolation_switch(DefaultsOperator):
    """Switch the shading interpolation between smooth and hard"""
    bl_idname = "color_plus.interpolation_switch"
    bl_label = "Smooth/Hard Switch"

    def execute(self, context: Context):
        color_plus = context.scene.color_plus
        if color_plus.interp_type == 'smooth':
            color_plus.interp_type = 'hard'
        else:
            color_plus.interp_type = 'smooth'
        return {'FINISHED'}


class COLORPLUS_OT_set_color_from_active(DefaultsOperator):
    """Set the Active Color based on the actively selected vertex color on the mesh"""
    bl_idname = "color_plus.set_color_from_active"
    bl_label = "Color from Active Vertex"

    @classmethod
    def poll(cls, context: Context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context: Context):
        ob = context.object
        saved_mode = ob.mode
        bpy.ops.object.mode_set(mode='EDIT')

        if not ob.data.color_attributes:
            self.report({'ERROR'}, "Could not find color data on active object")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(ob.data)

        try:
            active_selection = bm.select_history[-1]
        except IndexError:
            self.report({'ERROR'}, "There is no Active Vertex selected")
            return {'CANCELLED'}
        if not isinstance(active_selection, bmesh.types.BMVert):
            self.report({'ERROR'}, "Please select a vertex to get color from")
            return {'CANCELLED'}

        # Get active vertex color
        # TODO: Clean up all _layer_type variables
        # for full vertex & face corner domain support
        layer, layer_type = get_bmesh_active_color(bm, ob.data)
        components = get_component_colors(bm, layer, layer_type)
        for component, _color in components.items():
            if layer_type == "loop" \
            and component.vert.select \
            and component.vert == active_selection:
                if component.vert.select and component.vert == active_selection:
                    context.scene.color_plus.color_wheel = component[layer]
                    break
            # Vert
            if component.select \
            and component == active_selection:
                context.scene.color_plus.color_wheel = component[layer]
                break

        bpy.ops.object.mode_set(mode=saved_mode)
        return {'FINISHED'}


class COLORPLUS_OT_apply_attribute_shading(DefaultsOperator):
    """Sets the viewports shading to be more suitable for vertex editing"""
    bl_idname = "color_plus.apply_attribute_shading"
    bl_label = "Apply Attribute Shading"

    def execute(self, context: Context):
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'VERTEX'
        return {'FINISHED'}


class COLORPLUS_OT_remove_all_vertex_color(DefaultsOperator):
    """Remove all vertex color sets from all selected objects"""
    bl_idname = "color_plus.remove_all_vertex_color"
    bl_label = "Remove Color from Selection"

    def execute(self, context: Context):
        for ob in context.selected_objects:
            if not hasattr(ob.data, 'color_attributes'):
                continue
            while len(ob.data.color_attributes):
                try:
                    ob.data.color_attributes.remove(ob.data.color_attributes[0])
                except RuntimeError:
                    continue
        return {'FINISHED'}


class COLORPLUS_OT_refresh_palette_outliner(DefaultsOperator):
    """Manual refresh for the palette outliner of the Active Object as sometimes it doesn't update correctly on its own"""
    bl_idname = "color_plus.refresh_palette_outliner"
    bl_label = "Refresh Palette"

    saved_active_idx: bpy.props.IntProperty(default=-1)
    color: FloatVectorProperty(
        subtype='COLOR_GAMMA',
        default=[1, 1, 1, 1], size=4,
        options={'HIDDEN'}
    )

    # TODO Unused sorting method, currently breaks the
    # outliner in ways I haven't been able to solve
    #def sort_colors(self, colors: list) -> tuple[list, list]:
    #    # Convert to HSV, sort list by value
    #    colors_hsv = []
    #    for color in colors:
    #        colors_hsv.append([*colorsys.rgb_to_hsv(*color[:3]), color[3]])
    #
    #    # Separate and sort
    #    hsv_sep = [color for color in colors_hsv if color[0] == 0]
    #    hsv_values_sorted = sorted(hsv_sep, key=itemgetter(2))
    #    hsv_hues = [color for color in colors_hsv if color not in hsv_sep]
    #    hsv_hues_sorted = sorted(hsv_hues, key=itemgetter(0))
    #    colors_hsv = hsv_values_sorted + hsv_hues_sorted
    #
    #    # Convert back to RGB
    #    colors_rgb = []
    #    for color in colors_hsv:
    #        colors_rgb.append(
    #            [*colorsys.hsv_to_rgb(*color[:3]), color[3]]
    #        )
    #    return colors_hsv, colors_rgb

    def get_unique_colors(self, components: dict) -> list:
        preferences = \
            bpy.context.preferences.addons[__package__].preferences
        colors = []
        for color in components.values():
            if color in colors or color == list(BLANK_ARRAY):
                continue
            colors.append(color)
            if len(colors) > preferences.max_outliner_items:
                break
        return colors

    def format_palette_color_name(self, color) -> list:
        item_color = []
        if bpy.context.scene.color_plus.rgb_hsv_convert_options == 'rgb':
            for channel in color[:-1]:
                item_color.append(round(channel * 255))
        else: # HSV
            color_hsv = \
                colorsys.rgb_to_hsv(color[0], color[1], color[2])
            for channel in color_hsv:
                if channel.is_integer():
                    channel = round(channel)
                item_color.append(round(channel, 2))
        if color[3].is_integer():
            alpha_channel = round(color[3])
        else:
            alpha_channel = round(color[3], 3)
        item_color.append(alpha_channel)
        return item_color

    def generate_palette(self, ob: Object, colors: list) -> None:
        for idx, color in enumerate(colors):
            item = ob.color_palette.add()
            item.saved_color = color
            item.color = color
            #item.id = len(ob.color_palette) - 1
            if idx == self.saved_active_idx:
                item.id = self.saved_active_idx
            else:
                item.id = len(ob.color_palette) - 1
            item_color = self.format_palette_color_name(color)
            item.name = "({}, {}, {}, {})".format(
                item_color[0], item_color[1],
                item_color[2], item_color[3]
            )

    def check_existing_color(self, ob: Object) -> bool:
        """Check if the sent color already exists in the palette outliner.

        Useful for skipping unnecessary outliner refreshes."""
        rounded_color = []
        skip_refresh = False
        for channel in self.color:
            # NOTE: For whatever reason there is always
            # massive floating point errors here so we round
            rounded_color.append(round(channel, 2))
        palette_colors = \
            [[*palette.color] for palette in ob.color_palette]
        for color in palette_colors:
            for idx, channel in enumerate(color):
                color[idx] = round(channel, 2)
            if color == rounded_color:
                skip_refresh = True
                break
        if skip_refresh:
            return True
        return False

    def execute(self, context: Context):
        saved_mode=context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')

        duplicate_check = False
        if [*self.color] != list(BLANK_ARRAY):
            duplicate_check = True

        selected_mesh_objects = \
            [ob for ob in context.selected_objects if ob.type == 'MESH']
        for ob in selected_mesh_objects:
            # NOTE: Skip palette refresh if the sent color
            # already exists in the palette outliner
            if duplicate_check and self.check_existing_color(ob):
                continue
            ob.color_palette.clear()

            # Preserve the original index color value
            if len(ob.color_palette):
                palette = ob.color_palette[ob.color_palette_active]
                saved_color = iterable_to_list(palette.color)

            bm = bmesh.from_edit_mesh(ob.data)
            layer, layer_type = get_bmesh_active_color(bm, ob.data)
            components = get_component_colors(bm, layer, layer_type)
            colors = self.get_unique_colors(components)
            # TODO Unused sorting method, currently breaks the
            # outliner in ways I haven't been able to solve
            #colors = self.sort_colors(colors)

            self.generate_palette(ob, colors)

            if not 'saved_color' in locals():
                continue
            for color in ob.color_palette:
                converted_color = iterable_to_list(color.color)
                if converted_color == saved_color:
                    ob.color_palette_active = color.id
                    del saved_color
                    break
                del saved_color

        bpy.ops.object.mode_set(mode=saved_mode)
        self.color = list(BLANK_ARRAY)
        return {'FINISHED'}


class COLORPLUS_OT_change_outliner_color(DefaultsOperator):
    bl_idname = "color_plus.change_outliner_color"
    bl_options = {'INTERNAL'}

    saved_active_idx: bpy.props.IntProperty()

    def execute(self, context: Context):
        ob = context.object
        saved_mode = ob.mode
        bpy.ops.object.mode_set(mode='EDIT')

        palette = ob.color_palette[self.saved_active_idx]
        palette_saved_color = iterable_to_list(palette.saved_color)

        bm = bmesh.from_edit_mesh(ob.data)
        layer, layer_type = get_bmesh_active_color(bm, ob.data)
        components = get_component_colors(bm, layer, layer_type)
        for component, color in components.items():
            if color != palette_saved_color:
                continue
            component[layer] = palette.color
        bmesh.update_edit_mesh(ob.data)

        palette.name = \
            f'({round(palette.color[0] * 255)}, ' \
             f'{round(palette.color[1] * 255)}, ' \
             f'{round(palette.color[2] * 255)}, ' \
             f'{round(palette.color[3], 2)})'

        bpy.ops.object.mode_set(mode=saved_mode)
        return {'FINISHED'}


class COLORPLUS_OT_get_active_outliner_color(DefaultsOperator):
    """Apply the Outliner Color to the Active Color"""
    bl_idname = "color_plus.get_active_outliner_color"
    bl_label = "Set as Active Color"

    def execute(self, context: Context):
        ob = context.object
        context.scene.color_plus.color_wheel = \
            ob.color_palette[ob.color_palette_active].color
        return {'FINISHED'}


class COLORPLUS_OT_apply_outliner_color(DefaultsOperator):
    """Apply the Outliner Color to the selected geometry"""
    bl_idname = "color_plus.apply_outliner_color"
    bl_label = "Apply Outliner Color"

    def execute(self, context: Context):
        ob = context.object

        # Set the temporary property
        context.scene.color_plus.overlay_color_placeholder = \
            ob.color_palette[ob.color_palette_active].color

        # TODO: This still uses selected_objects
        bpy.ops.color_plus.edit_color(
            edit_type='apply',
            variation_value='overlay_color_placeholder'
        )
        return {'FINISHED'}


class COLORPLUS_OT_select_outliner_color(DefaultsOperator):
    """Select vertices based on the Outliner Color (WARNING: This does not remove your existing selection)"""
    bl_idname = "color_plus.select_outliner_color"
    bl_label = "Select Geometry from Outliner Color"

    def execute(self, context: Context):
        ob = context.object
        saved_mode = ob.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        context.tool_settings.mesh_select_mode = (True, False, False)

        palette = ob.color_palette[ob.color_palette_active]
        active_color = iterable_to_list(palette.color)

        # Object mode BMesh correct mesh update
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer, layer_type = get_bmesh_active_color(bm, ob.data)
        components = get_component_colors(bm, layer, layer_type)
        for component, color in components.items():
            if color != active_color:
                continue
            if layer_type == 'loop':
                component.vert.select_set(True)
            else: # Vert
                component.select_set(True)
        bm.to_mesh(ob.data)

        bpy.ops.object.mode_set(mode=saved_mode)
        return {'FINISHED'}


class COLORPLUS_OT_delete_outliner_color(DefaultsOperator):
    """Remove the Outliner Color from the Palette Outliner and geometry"""
    bl_idname = "color_plus.delete_outliner_color"
    bl_label = "Delete Outliner Color"

    def execute(self, context: Context):
        ob = context.object
        saved_mode = ob.mode
        bpy.ops.object.mode_set(mode='EDIT')

        palette = ob.color_palette[ob.color_palette_active]
        palette_color = iterable_to_list(palette.color)

        bm = bmesh.from_edit_mesh(ob.data)
        layer, layer_type = get_bmesh_active_color(bm, ob.data)
        component_colors = get_component_colors(bm, layer, layer_type)
        for component, color in component_colors.items():
            if color == palette_color:
                component[layer] = BLANK_ARRAY
        bmesh.update_edit_mesh(ob.data)

        bpy.ops.object.mode_set(mode=saved_mode)

        preferences = \
            context.preferences.addons[__package__].preferences
        if preferences.auto_palette_refresh:
            bpy.ops.color_plus.refresh_palette_outliner()
        return {'FINISHED'}


class COLORPLUS_OT_convert_to_vertex_group(DefaultsOperator):
    """Convert the Outliner Color to a single Vertex Group"""
    bl_idname = "color_plus.convert_to_vertex_group"
    bl_label = "Convert to Vertex Group"

    def execute(self, context: Context):
        ob = context.object
        saved_mode = ob.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        palette = ob.color_palette[ob.color_palette_active]
        palette_color = iterable_to_list(palette.color)

        # Object mode BMesh for vgroup add (only works in ob mode)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer, layer_type = get_bmesh_active_color(bm, ob.data)
        components = get_component_colors(bm, layer, layer_type)

        # Get vertices with the corresponding color value
        vert_indices = []
        for component, color in components.items():
            if layer_type == 'loop':
                index = component.vert.index
            else: # Vert
                index = component.index
            if index in vert_indices or color != palette_color:
                continue
            vert_indices.append(index)

        converted_vgroup = ob.vertex_groups.new(name=palette.name)
        converted_vgroup.add(vert_indices, 1.0, 'ADD')

        bpy.ops.object.mode_set(mode=saved_mode)
        return {'FINISHED'}


class COLORPLUS_OT_custom_color_apply(DefaultsOperator):
    """Apply the color to your current selection/Active Color"""
    bl_idname = "color_plus.custom_color_apply"
    bl_options = {'INTERNAL'}

    custom_color_name: bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context: Context):
        # NOTE: You can run this operator in any
        # mode if only setting the active color
        custom_apply_option = context.scene.color_plus.custom_apply_option
        return context.mode == 'EDIT_MESH' \
        or custom_apply_option == 'apply_to_col'

    def execute(self, context: Context):
        color_plus = context.scene.color_plus
        if color_plus.custom_apply_option == 'apply_to_sel':
            bpy.ops.color_plus.edit_color(
                edit_type='apply', variation_value=self.custom_color_name
            )
        else: # Set color
            color_plus.color_wheel = getattr(color_plus, self.custom_color_name)
        return {'FINISHED'}


class COLORPLUS_OT_apply_color_to_border(DefaultsOperator):
    """Apply a VColor to the border or bounds of your current selection"""
    bl_idname = "color_plus.apply_color_to_border"
    bl_label = "Apply to Selection Border"

    border_type: bpy.props.EnumProperty(
        items=(
            ('inner', "Inner", ""),
            ('outer', "Outer", "")
        )
    )

    @classmethod
    def poll(cls, context: Context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context: Context):
        color_plus = context.scene.color_plus
        saved_mode=context.object.mode

        bpy.ops.object.mode_set(mode='OBJECT')
        context.object.select_set(True)

        selected_mesh_objects = \
            [ob for ob in context.selected_objects if ob.type == 'MESH']
        for ob in selected_mesh_objects:
            if get_active_color(ob.data) is None:
                create_color(ob.data)

            bm = bmesh.new()
            bm.from_mesh(ob.data)
            layer, _layer_type = get_bmesh_active_color(bm, ob.data)

            # Get border vertices & linked faces
            border_vertices = set([])
            linked_faces = []
            for edge in [edge for edge in bm.edges if edge.select]:
                if edge.is_boundary \
                or edge.link_faces[0].select != edge.link_faces[1].select:
                    for vert in edge.verts:
                        if vert.index not in border_vertices:
                            border_vertices.add(vert.index)
                    linked_faces.extend(list(edge.link_faces))

            # Search linked faces for loops on
            # the correct sides of the vertices
            if self.border_type == 'inner':
                for face in linked_faces:
                    if not face.select:
                        continue
                    for loop in face.loops:
                        if loop.vert.index in border_vertices:
                            loop[layer] = color_plus.color_wheel
            else: # NOTE: Outer
                for face in linked_faces:
                    if face.select:
                        continue
                    for loop in face.loops:
                        if loop.vert.index in border_vertices:
                            loop[layer] = color_plus.color_wheel
            bm.to_mesh(ob.data)

        bpy.ops.object.mode_set(mode=saved_mode)

        preferences = \
            context.preferences.addons[__package__].preferences
        if preferences.auto_palette_refresh:
            bpy.ops.color_plus.refresh_palette_outliner(
                color=color_plus.color_wheel
            )
        return {'FINISHED'}


class COLORPLUS_OT_dirty_vertex_color(DefaultsOperator):
    """Generate dirty vertex color"""
    bl_idname = "color_plus.dirty_vertex_color"
    bl_label = "Generate VColor"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    blur_strength: bpy.props.FloatProperty(default=1.0, name='Blur Strength')
    blur_iterations: bpy.props.IntProperty(default=1, name='Blur Iterations')
    clean_angle: bpy.props.FloatProperty(default=3.14159, name='Clean Angle', subtype='ANGLE')
    dirt_angle: bpy.props.FloatProperty(default=0.0, name='Dirt Angle')
    dirt_only: bpy.props.BoolProperty(default=False, name='Dirt Only')
    normalize: bpy.props.BoolProperty(default=True, name='Normalize')
    selection_only: bpy.props.BoolProperty(default=False, name='Use Selection')

    def execute(self, context: Context):
        if not bpy.ops.paint.vertex_paint_toggle.poll():
            self.report({'ERROR'}, "Could not switch to Vertex Paint mode")
            return {'CANCELLED'}

        saved_mode=context.mode

        context.object.data.use_paint_mask = self.selection_only

        if context.mode != 'PAINT_VERTEX':
            bpy.ops.paint.vertex_paint_toggle()

        bpy.ops.paint.vertex_color_dirt(
            blur_strength=self.blur_strength,
            blur_iterations=self.blur_iterations,
            clean_angle=self.clean_angle,
            dirt_angle=self.dirt_angle,
            dirt_only=self.dirt_only,
            normalize=self.normalize
        )

        if saved_mode != 'PAINT_VERTEX':
            bpy.ops.object.editmode_toggle()
        return {'FINISHED'}


class COLORPLUS_OT_generate_color(DefaultsOperator):
    """Generate a VColor mask based on the settings below"""
    bl_idname = "color_plus.generate_color"
    bl_label = "Generate Vertex Color"

    bm = None
    layer = None
    uv_islands = None

    def uv_shell(self):
        for island_idxs in self.uv_islands:
            random_color = [random(), random(), random(), 1]
            for face_idx in island_idxs:
                face = self.bm.faces[face_idx]
                for loop in face.loops:
                    loop[self.layer] = random_color

    def uv_border(self):
        color_plus = bpy.context.scene.color_plus
        for island_idxs in self.uv_islands:
            if color_plus.generate_per_uv_border == 'random_col':
                random_color = [random(), random(), random(), 1]

            # Get border vertices & linked faces
            border_vertices = set([])
            linked_faces = set([])
            for edge in self.bm.edges:
                if edge.is_boundary \
                or (edge.link_faces[0].index in island_idxs \
                and edge.link_faces[1].index not in island_idxs) \
                or (edge.link_faces[0].index not in island_idxs \
                and edge.link_faces[1].index in island_idxs):
                    for vert in edge.verts:
                        if vert.index in border_vertices:
                            continue
                        border_vertices.add(vert.index)
                for vert in edge.verts:
                    if vert.index not in border_vertices:
                        continue
                    for face in edge.link_faces:
                        if face in linked_faces:
                            continue
                        linked_faces.add(face)

            # Assign a color to interior loops of linked faces
            for face in linked_faces:
                if face.index not in island_idxs:
                    continue
                for loop in face.loops:
                    if loop.vert.index not in border_vertices:
                        continue
                    if color_plus.generate_per_uv_border == 'random_col':
                        loop[self.layer] = random_color
                    else: # Apply active color
                        loop[self.layer] = color_plus.color_wheel

    def face(self):
        for face in self.bm.faces:
            random_color = [random(), random(), random(), 1]
            for loop in face.loops:
                loop[self.layer] = random_color

    def vertex(self):
        for face in self.bm.faces:
            random_color = [random(), random(), random(), 1]
            for loop in face.loops:
                loop[self.layer] = random_color

                for vert in self.bm.verts:
                    random_color = [random(), random(), random(), 1]
                    for loop in vert.link_loops:
                        loop[self.layer] = random_color

    def point(self):
        for face in self.bm.faces:
            for loop in face.loops:
                random_color = [random(), random(), random(), 1]
                loop[self.layer] = random_color

    def execute(self, context: Context):
        color_plus = context.scene.color_plus
        saved_mode=context.object.mode

        bpy.ops.object.mode_set(mode='OBJECT')
        context.object.select_set(True)

        no_uv_obs = []
        selected_mesh_objects = \
            [ob for ob in context.selected_objects if ob.type == 'MESH']
        for ob in selected_mesh_objects:
            if color_plus.generate in ('per_uv_shell', 'per_uv_border'):
                try:
                    self.uv_islands = \
                        bpy_extras.mesh_utils.mesh_linked_uv_islands(ob.data)
                except AttributeError:
                    no_uv_obs.append(ob.name)
                    continue

            if get_active_color(ob.data) is None:
                create_color(ob.data)

            self.bm = bmesh.new()
            self.bm.from_mesh(ob.data)
            self.bm.faces.ensure_lookup_table()
            self.layer, _layer_type = get_bmesh_active_color(self.bm, ob.data)
            if color_plus.generate == 'per_uv_shell':
                self.uv_shell()
            elif color_plus.generate == 'per_uv_border':
                self.uv_border()
            elif color_plus.generate == 'per_face':
                self.face()
            elif color_plus.generate == 'per_vertex':
                self.vertex()
            elif color_plus.generate == 'per_point':
                self.point()
            self.bm.to_mesh(ob.data)

        if color_plus.generate in ('per_uv_shell', 'per_uv_border') \
        and no_uv_obs:
            self.report({'INFO'}, f"UVs not found for: {no_uv_obs}")

        bpy.ops.object.mode_set(mode=saved_mode)

        preferences = \
            context.preferences.addons[__package__].preferences
        if preferences.auto_palette_refresh:
            bpy.ops.color_plus.refresh_palette_outliner()
        return {'FINISHED'}


#######################################
# REGISTRATION
#######################################


classes = (
    COLORPLUS_OT_toggle_vertex_paint_mode,
    COLORPLUS_OT_edit_color,
    COLORPLUS_OT_edit_color_keymap_placeholder,
    COLORPLUS_OT_active_color_switch,
    COLORPLUS_OT_interpolation_switch,
    COLORPLUS_OT_set_color_from_active,
    COLORPLUS_OT_apply_attribute_shading,
    COLORPLUS_OT_remove_all_vertex_color,
    COLORPLUS_OT_refresh_palette_outliner,
    COLORPLUS_OT_change_outliner_color,
    COLORPLUS_OT_get_active_outliner_color,
    COLORPLUS_OT_apply_outliner_color,
    COLORPLUS_OT_select_outliner_color,
    COLORPLUS_OT_delete_outliner_color,
    COLORPLUS_OT_convert_to_vertex_group,
    COLORPLUS_OT_custom_color_apply,
    COLORPLUS_OT_apply_color_to_border,
    COLORPLUS_OT_dirty_vertex_color,
    COLORPLUS_OT_generate_color
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
