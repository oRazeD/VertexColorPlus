"""All ui for vertex colors plus.
"""


import bpy
from bpy.types import Panel, UIList, Menu

from .preferences import COLORPLUS_PT_presets
from .functions import get_active_color
from .constants import MAX_OUTLINER_ITEM_MSG


######################################
# UI
######################################


class PanelInfo:
    bl_category = 'Vertex Color'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


class COLORPLUS_PT_ui(PanelInfo, Panel):
    bl_label = 'Vertex Colors Plus'

    def draw(self, context):
        color_plus = context.scene.color_plus
        layout = self.layout

        col = layout.column()
        col.scale_y = 1.3
        switch_mode = "Editing"
        in_edit_mode = context.mode == 'EDIT_MESH'
        if in_edit_mode:
            switch_mode = "Painting"
        col.operator(
            'color_plus.toggle_vertex_paint_mode',
            text=f"Switch to {switch_mode}",
            icon='VPAINT_HLT' if context.mode == 'EDIT_MESH' else 'EDITMODE_HLT'
        )

        col.separator(factor=.25)

        self.draw_color_sets(context)

        col = layout.column(align=True)
        split = col.split(factor=.75, align=True)
        split.scale_y = 1.3
        split.enabled = in_edit_mode
        edit_color_op = split.operator(
            "color_plus.edit_color",
            text='Paint Selection', icon='BRUSH_DATA'
        )
        edit_color_op.edit_type = 'apply'
        edit_color_op.variation_value = 'color_wheel'
        split.operator(
            "color_plus.edit_color",
            text='', icon='X'
        ).edit_type = 'clear'

        box = col.box()
        col2 = box.column(align=True)

        split = col2.split(factor=.4)
        split.scale_y = 1.3
        split.label(text='Color', icon='COLOR')

        row = split.row(align=True)
        row.prop(color_plus, 'color_wheel')
        row.operator("color_plus.active_color_switch", icon='LOOP_FORWARDS')

        split = col2.split(factor=.4)
        split.scale_y = 1.3
        split.separator()

        split_row = split.split(factor=.7)
        split_row.prop(color_plus, 'live_color_tweak')
        split_row.prop(color_plus, 'alt_color_wheel')

        col = box.column(align=True)
        split = col.split(factor=.4)
        split.label(text='Interpolation')
        row = split.row()
        row.enabled = in_edit_mode
        if context.object and context.object.type == 'MESH':
            active_color = get_active_color(context.object.data)
            if active_color is not None \
            and active_color.domain != 'CORNER':
                row.enabled = False
        row.prop(color_plus, 'interp_type', expand=True)
        if color_plus.interp_type == 'hard':
            box = col.box()
            box.scale_y = .8
            box.label(text='Face selections only!', icon='INFO')

    def draw_color_sets(self, context):
        layout = self.layout

        if not context.object:
            layout.label(text='No Active Object is selected', icon='INFO')
            return

        row = layout.row()
        col = row.column()

        if not context.object \
        or context.object.type != 'MESH':
            return

        data = context.object.data
        if bpy.app.version < (3, 2, 0):
            col.template_list(
                "MESH_UL_vcols",
                "vcols",
                data,
                "vertex_colors",
                data.vertex_colors,
                "active_index",
                rows=3
            )
            col = row.column(align=True)
            col.operator("mesh.vertex_color_add", icon='ADD', text="")
            col.operator("mesh.vertex_color_remove", icon='REMOVE', text="")
        else:
            col.template_list(
                "MESH_UL_color_attributes",
                "color_attributes",
                data,
                "color_attributes",
                data.color_attributes,
                "active_color_index",
                rows=3,
            )
            col = row.column(align=True)
            col.operator("geometry.color_attribute_add",
                         icon='ADD', text="")
            col.operator("geometry.color_attribute_remove",
                         icon='REMOVE', text="")
            col.separator()
            col.menu("MESH_MT_color_attribute_context_menu",
                     icon='DOWNARROW_HLT', text="")

            # TODO:
            # self.draw_attribute_warnings(context, layout)


class COLORPLUS_PT_apply(PanelInfo, Panel):
    bl_label = 'Apply'
    bl_parent_id = 'COLORPLUS_PT_ui'

    def draw(self, context):
        color_plus = context.scene.color_plus

        layout = self.layout

        col = layout.column(align=True)
        col.operator("color_plus.apply_attribute_shading",
                     icon='SHADING_TEXTURE')
        col.operator("color_plus.remove_all_vertex_color",
                     icon='TRASH')

        if context.mode not in ('EDIT_MESH', 'PAINT_VERTEX'):
            return

        col.operator("color_plus.set_color_from_active",
                     icon='RESTRICT_COLOR_ON')

        col = layout.column(align=True)
        col.scale_y = 1.1
        edit_color_op = col.operator(
            "color_plus.edit_color",
            text='Fill All', icon='CHECKMARK'
        )
        edit_color_op.edit_type = 'apply_all'
        edit_color_op.variation_value = 'color_wheel'
        col.operator(
            "color_plus.edit_color",
            text='Clear All', icon='X'
        ).edit_type = 'clear_all'

        row = col.row(align=True)
        edit_color_op = row.operator(
            "color_plus.edit_color",
            text='Fill Only Color'
        )
        edit_color_op.edit_type = 'apply'
        edit_color_op.variation_value = 'color_only'

        edit_alpha_op = row.operator(
            "color_plus.edit_color",
            text='Fill Only Alpha'
        )
        edit_alpha_op.edit_type = 'apply'
        edit_alpha_op.variation_value = 'alpha_only'

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Selection Border")

        row = col.row(align=True)
        row.operator(
            'color_plus.apply_color_to_border',
            text='Inner', icon='CLIPUV_HLT'
        ).border_type = 'inner'
        row.operator(
            'color_plus.apply_color_to_border',
            text='Outer', icon='CLIPUV_DEHLT'
        ).border_type = 'outer'

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Variation")

        row = col.row(align=True)
        row.enabled = context.mode == 'EDIT_MESH'

        edit_value = row.operator(
            'color_plus.edit_color',
            text='', icon='CHECKMARK'
        )
        edit_value.edit_type = 'apply'
        edit_value.variation_value = 'value_var'

        split = row.split(factor=.75, align=True)
        split.prop(color_plus, 'value_var_slider', text='Value')
        split.prop(color_plus, 'value_var')

        row = col.row(align=True)
        row.enabled = not context.mode != 'EDIT_MESH'

        edit_alpha = row.operator(
            'color_plus.edit_color',
            text='', icon='CHECKMARK'
        )
        edit_alpha.edit_type = 'apply'
        edit_alpha.variation_value = 'alpha_var'

        split = row.split(factor=.75, align=True)
        split.prop(color_plus, 'alpha_var_slider', text='Alpha')
        split.prop(color_plus, 'alpha_var')


class COLORPLUS_UL_items(UIList):
    def draw_item(self, _context, layout, _data, item, _icon,
                  _active_data, _active_propname, _index=0, _flt_flag=0):
        row = layout.row()
        row.scale_x = 0.325
        row.prop(item, 'color')

        split = layout.split(factor=.025)
        split.label(text="")
        split.label(text=item.name)


class COLORPLUS_PT_palette_outliner(PanelInfo, Panel):
    bl_label = 'Palette Outliner'
    bl_parent_id = 'COLORPLUS_PT_ui'

    @classmethod
    def poll(cls, context):
        return context.mode in ('EDIT_MESH', 'PAINT_VERTEX')

    def draw(self, context):
        layout = self.layout

        ob = context.object
        preferences = context.preferences.addons[__package__].preferences

        disable_ui = False
        if not ob.color_palette:
            disable_ui = True
        else:
            try:
                _ = ob.color_palette[ob.color_palette_active]
            except (IndexError, ValueError):
                disable_ui = True

        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("color_plus.refresh_palette_outliner",
                     text='Refresh Palette', icon='FILE_REFRESH')

        row = layout.row()
        col = row.column(align=True)
        col.template_list("COLORPLUS_UL_items",
                          "",
                          ob,
                          "color_palette",
                          ob,
                          "color_palette_active",
                          rows=4)

        max_outliner_items = preferences.max_outliner_items
        if len(ob.color_palette) >= max_outliner_items:
            box = col.box()
            box.scale_y = .8
            box.label(text=MAX_OUTLINER_ITEM_MSG + f" ({max_outliner_items})",
                      icon='ERROR')

        if len(context.selected_objects) > 1:
            box = col.box()
            box.scale_y = .8
            box.label(text="Only uses Active Object", icon='INFO')

        row2 = col.row(align=True)
        row2.scale_y = .95
        row2.enabled = not disable_ui
        row2.prop(context.scene.color_plus,
                  'rgb_hsv_convert_options',
                  expand=True)

        col = row.column(align=True)
        col.enabled = not disable_ui
        col.operator(
            "color_plus.apply_outliner_color",
            icon='CHECKMARK', text=""
        )
        col.operator(
            "color_plus.get_active_outliner_color",
            icon='RESTRICT_COLOR_ON', text=""
        )
        col.operator(
            "color_plus.select_outliner_color",
            icon='RESTRICT_SELECT_OFF', text=""
        )
        col.operator(
            "color_plus.delete_outliner_color",
            icon='TRASH', text=""
        )
        col.operator(
            "color_plus.convert_to_vertex_group",
            icon='GROUP_VERTEX', text=""
        )


class COLORPLUS_PT_custom_palette(PanelInfo, Panel):
    bl_label = 'Customizable Palette'
    bl_parent_id = 'COLORPLUS_PT_ui'

    @classmethod
    def poll(cls, context):
        return context.mode in {'EDIT_MESH', 'PAINT_VERTEX'}

    def draw(self, context):
        color_plus = context.scene.color_plus
        layout = self.layout

        col = layout.column()
        COLORPLUS_PT_presets.draw_menu( # pylint: disable=E1120
            col, text="Custom Palette Presets"
        )

        # TODO: Custom palette I/O handling
        #row = col.row(align=True)
        #row.enabled = False
        #row.operator(
        #   "color_plus.apply_attribute_shading",
        #   text='Import', icon='IMPORT'
        #)
        #row.operator(
        #    "color_plus.apply_attribute_shading",
        #    text='Export', icon='EXPORT'
        #)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(color_plus, 'custom_apply_option', expand=True)

        col.separator(factor=.2)

        split = col.split(align=True)
        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_1')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_1'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_2')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_2'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_3')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_3'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_4')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_4'

        col = layout.column(align=True)

        split = col.split(align=True)
        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_5')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_5'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_6')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_6'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_7')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_7'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_8')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_8'

        col = layout.column(align=True)

        split = col.split(align=True)
        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_9')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_9'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_10')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_10'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_11')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_11'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_12')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_12'

        col = layout.column(align=True)

        split = col.split(align=True)
        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_13')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_13'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_14')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_14'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_15')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_15'

        row = split.row(align=True)
        row.prop(color_plus, 'color_custom_16')
        split.operator("color_plus.custom_color_apply",
                       icon='CHECKMARK').custom_color_name = 'color_custom_16'


class COLORPLUS_PT_bake_to_vertex_color(PanelInfo, Panel):
    bl_label = 'Bake to Vertex Color'
    bl_parent_id = 'COLORPLUS_PT_ui'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # TODO: Validate latest build
        if not 'bakeToVertexColor_1_0_8' in context.preferences.addons:
            box = layout.box()
            box.operator(
                "wm.url_open",
                text="Bake to Vertex Color on Gumroad"
            ).url = "https://3dbystedt.gumroad.com/l/zdgxg"
            box.label(text='You do not have Bake to', icon='ERROR')
            box.label(text='Vertex Color installed & enabled')
            box.label(text='or you do not have the latest version')
            return

        row = layout.row()
        row.label(text="Bake Type")
        row.prop(scene.bake_to_vertex_color_props, "bake_pass", text="")

        row = layout.row()
        row.label(text="Bake UV")
        row.prop(scene.bake_to_vertex_color_props, "bake_uv_type", text="")

        row = layout.row()
        row.label(text="Lightmap Resolution")
        row.prop(scene.bake_to_vertex_color_props, "resolution", text="")

        row = layout.row()
        row.label(text="Samples")
        row.prop(scene.bake_to_vertex_color_props, "samples", text="")

        row = layout.row()
        row.label(text="Smooth VColors")
        row.prop(scene.bake_to_vertex_color_props,
        "smooth_vertex_colors", text="")

        row = layout.row()
        row.label(text="Delete Bake Image")
        row.prop(scene.bake_to_vertex_color_props,
                    "delete_bake_image", text="")

        row = layout.row()
        row.label(text="VColor Name")
        row.prop(scene.bake_to_vertex_color_props,
                    "vertex_color_name", text="")

        row = layout.row()
        row.scale_y = 1.5
        row.separator(factor=.25)

        row = layout.row()
        row.scale_y = 1.5
        bake_to_vcolor_op = row.operator('object.bake_to_vertex_col',
                                            text='Bake Pass to Vertex Color',
                                            icon='RENDER_STILL')
        bake_to_vcolor_op.resolution = \
            int(scene.bake_to_vertex_color_props.resolution)
        bake_to_vcolor_op.samples = \
            scene.bake_to_vertex_color_props.samples
        bake_to_vcolor_op.vertex_color_name = \
            scene.bake_to_vertex_color_props.vertex_color_name
        bake_to_vcolor_op.smooth_vertex_colors = \
            scene.bake_to_vertex_color_props.smooth_vertex_colors
        bake_to_vcolor_op.bake_uv_type = \
            scene.bake_to_vertex_color_props.bake_uv_type
        bake_to_vcolor_op.delete_bake_image = \
            scene.bake_to_vertex_color_props.delete_bake_image
        bake_to_vcolor_op.bake_pass = \
            scene.bake_to_vertex_color_props.bake_pass


class COLORPLUS_PT_color_generation(PanelInfo, Panel):
    bl_label = 'Generate Vertex Color'
    bl_parent_id = 'COLORPLUS_PT_ui'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        color_plus = context.scene.color_plus

        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = 1.3

        if color_plus.generate != 'dirty_color':
            col.operator('color_plus.generate_color', icon='GROUP_VCOL')
        else:
            col.operator('color_plus.dirty_vertex_color', icon='GROUP_VCOL')

        row = col.row(align=True)
        row.scale_y = .8
        row.prop(color_plus, 'generate', text='')

        if color_plus.generate =='per_uv_border':
            col.separator()

            row = col.row()
            row.scale_y = .8
            row.prop(color_plus, 'generate_per_uv_border', expand=True)


class COLORPLUS_MT_pie_menu(Menu):
    bl_idname = "COLORPLUS_MT_pie_menu"
    bl_label = "Vertex Colors Plus"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        color_plus = context.scene.color_plus

        #4 - LEFT
        col = pie.column()

        col.scale_x = .8
        col.separator(factor=12)

        box = col.box().column(align=True)

        box2 = box.box()
        col2 = box2.column(align=True)

        split = col2.split(align=True)
        split.scale_y = 1.3
        split.label(text='Active Color', icon='COLOR')

        row = split.row(align=True)
        row.prop(color_plus, 'color_wheel')
        row.prop(color_plus, 'alt_color_wheel')

        split = col2.split()
        split.separator()
        split.prop(color_plus, 'live_color_tweak')

        col3 = box.column()

        col3.separator(factor=.5)

        split = col3.split(align=True)
        split.scale_y = 1.25
        split.label(text=' Interpolation')
        split.prop(color_plus, 'interp_type', expand=True)

        col3.separator(factor=.5)

        col3 = box.column()
        col3.scale_y = 1.25
        col3.operator("color_plus.set_color_from_active",
                      icon='RESTRICT_COLOR_ON')
        col3.operator("color_plus.apply_attribute_shading",
                      icon='SHADING_TEXTURE')
        #6 - RIGHT
        col = pie.column()

        col.scale_x = .9
        col.separator(factor=12)

        box = col.box().column(align=True)

        col = box.column()

        row = col.row(align=True)
        row.scale_y = 1.25

        edit_color_op = row.operator("color_plus.edit_color",
                                     text='Fill All', icon='CHECKMARK')
        edit_color_op.edit_type = 'apply_all'
        edit_color_op.variation_value = 'color_wheel'
        row.operator("color_plus.edit_color",
                     text='Clear All',
                     icon='PANEL_CLOSE').edit_type = 'clear_all'

        col.separator(factor=.5)

        box = col.box()
        col2 = box.column(align=True)
        col2.label(text='Selection Border')

        row = col2.row(align=True)
        row.operator('color_plus.apply_color_to_border',
                     text='Inner', icon='CLIPUV_HLT').border_type = 'inner'
        row.operator('color_plus.apply_color_to_border',
                     text='Outer', icon='CLIPUV_DEHLT').border_type = 'outer'

        col.separator(factor=.5)

        box2 = col.box()
        col = box2.column(align=True)
        col.label(text="Variation")

        row = col.row(align=True)
        edit_color = row.operator('color_plus.edit_color',
                                  text='', icon='CHECKMARK')
        edit_color.edit_type = 'apply'
        edit_color.variation_value = 'value_var'

        split = row.split(factor=.8, align=True)
        split.prop(color_plus, 'value_var_slider')
        split.prop(color_plus, 'value_var')
        #2 - BOTTOM
        pie.operator("color_plus.edit_color",
                     text='Clear Selection',
                     icon='PANEL_CLOSE').edit_type = 'clear'
        #8 - TOP
        edit_color_op = pie.operator("color_plus.edit_color",
                                     text='Paint Selection',
                                     icon='CHECKMARK')
        edit_color_op.edit_type = 'apply'
        edit_color_op.variation_value = 'color_wheel'
        #7 - TOP - LEFT
        pie.operator("color_plus.active_color_switch",
                     text='Quick Color Switch',
                     icon='LOOP_FORWARDS')
        #9 - TOP - RIGHT
        pie.operator("color_plus.interpolation_switch",
                     text='Smooth/Hard Switch',
                     icon='MATSHADERBALL')
        # 1 - BOTTOM - LEFT
        pie.separator()
        # 3 - BOTTOM - RIGHT
        pie.separator()


########################################
# REGISTRATION
########################################


classes = (
    COLORPLUS_PT_ui,
    COLORPLUS_PT_apply,
    COLORPLUS_UL_items,
    COLORPLUS_PT_palette_outliner,
    COLORPLUS_PT_custom_palette,
    COLORPLUS_PT_color_generation,
    COLORPLUS_PT_bake_to_vertex_color,
    COLORPLUS_MT_pie_menu
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
