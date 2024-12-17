import colorsys

import bpy
import rna_keymap_ui
from bl_ui.utils import PresetPanel
from bl_operators.presets import AddPresetBase

from bpy.types import Panel, AddonPreferences, Context, Menu
from bpy.props import (
    BoolProperty,
    FloatProperty,
    PointerProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
    CollectionProperty
)

from .constants import MAX_OUTLINER_ITEM_MSG


##################################
# Keymapping
##################################


class COLORPLUS_addon_keymaps:
    _addon_keymaps = []
    _keymaps = {}

    @classmethod
    def new_keymap(cls, name, kmi_name, kmi_value=None, km_name='3D View',
                   space_type="VIEW_3D", region_type="WINDOW",
                   event_type=None, event_value=None, ctrl=False, shift=False,
                   alt=False, key_modifier="NONE"):

        cls._keymaps.update({name: [kmi_name, kmi_value, km_name, space_type,
                                    region_type, event_type, event_value,
                                    ctrl, shift, alt, key_modifier]
                             })

    @classmethod
    def add_hotkey(cls, kc, keymap_name):

        items = cls._keymaps.get(keymap_name)
        if not items:
            return

        kmi_name, kmi_value, km_name, space_type, region_type = items[:5]
        event_type, event_value, ctrl, shift, alt, key_modifier = items[5:]
        km = kc.keymaps.new(name=km_name, space_type=space_type,
                            region_type=region_type)

        kmi = km.keymap_items.new(kmi_name, event_type, event_value,
                                  ctrl=ctrl,
                                  shift=shift, alt=alt,
                                  key_modifier=key_modifier
                                  )
        if kmi_value:
            kmi.properties.name = kmi_value

        kmi.active = True

        cls._addon_keymaps.append((km, kmi))

    @staticmethod
    def register_keymaps():
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        # In background mode, there's no such thing has keyconfigs.user,
        # because headless mode doesn't need key combos.
        # So, to avoid error message in background mode, we need to check if
        # keyconfigs is loaded.
        if not kc:
            return

        for keymap_name in COLORPLUS_addon_keymaps._keymaps:
            COLORPLUS_addon_keymaps.add_hotkey(kc, keymap_name)

    @classmethod
    def unregister_keymaps(cls):
        kmi_values = [item[1] for item in cls._keymaps.values() if item]
        kmi_names = [item[0] for item in cls._keymaps.values() if
                     item not in ['wm.call_menu', 'wm.call_menu_pie']]

        for km, kmi in cls._addon_keymaps:
            # remove addon keymap for menu and pie menu
            if hasattr(kmi.properties, 'name'):
                if kmi_values:
                    if kmi.properties.name in kmi_values:
                        km.keymap_items.remove(kmi)

            # remove addon_keymap for operators
            else:
                if kmi_names:
                    if kmi.idname in kmi_names:
                        km.keymap_items.remove(kmi)

        cls._addon_keymaps.clear()

    @staticmethod
    def get_hotkey_entry_item(name, kc, km, kmi_name, kmi_value, col):

        # for menus and pie_menu
        if kmi_value:
            for km_item in km.keymap_items:
                if km_item.idname == kmi_name and km_item.properties.name == kmi_value:
                    col.context_pointer_set('keymap', km)
                    rna_keymap_ui.draw_kmi([], kc, km, km_item, col, 0)
                    return

            col.label(text=f"No hotkey entry found for {name}")
            col.operator(COLORPLUS_OT_restore_hotkey.bl_idname,
                         text="Restore keymap",
                         icon='ADD').km_name = km.name

        # for operators
        else:
            if km.keymap_items.get(kmi_name):
                col.context_pointer_set('keymap', km)
                rna_keymap_ui.draw_kmi([], kc, km, km.keymap_items[kmi_name],
                                       col, 0)

            else:
                col.label(text=f"No hotkey entry found for {name}")
                col.operator(COLORPLUS_OT_restore_hotkey.bl_idname,
                             text="Restore keymap",
                             icon='ADD').km_name = km.name

    @staticmethod
    def draw_keymap_items(wm, layout):
        kc = wm.keyconfigs.user

        for name, items in COLORPLUS_addon_keymaps._keymaps.items():
            kmi_name, kmi_value, km_name = items[:3]
            box = layout.box()
            split = box.split()
            col = split.column()
            col.label(text=name)
            col.separator()
            km = kc.keymaps[km_name]
            COLORPLUS_addon_keymaps.get_hotkey_entry_item(name, kc, km,
                                                           kmi_name, kmi_value, col)


class COLORPLUS_OT_restore_hotkey(bpy.types.Operator):
    bl_idname = "template.restore_hotkey"
    bl_label = "Restore hotkeys"
    bl_options = {'REGISTER', 'INTERNAL'}

    km_name: StringProperty()

    def execute(self, context: Context):
        context.preferences.active_section = 'KEYMAP'
        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps.get(self.km_name)
        if km:
            km.restore_to_default()
            context.preferences.is_dirty = True
        context.preferences.active_section = 'ADDONS'
        return {'FINISHED'}


class COLORPLUS_OT_add_hotkey(bpy.types.Operator):
    bl_idname = "color_plus.add_hotkey"
    bl_label = "Add Hotkeys"
    bl_options = {'REGISTER', 'INTERNAL'}

    km_name: StringProperty()

    def execute(self, context: Context):
        context.preferences.active_section = 'KEYMAP'
        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps.get(self.km_name)
        if km:
            km.restore_to_default()
            context.preferences.is_dirty = True
        context.preferences.active_section = 'ADDONS'
        return {'FINISHED'}


############################################################
# PROPERTY GROUP
############################################################


class COLORPLUS_property_group(bpy.types.PropertyGroup):
    def update_color_wheel(self, context: Context):
        # Update selected vertices if live color tweak is on
        if self.live_color_tweak \
        and context.mode in ('EDIT_MESH', 'PAINT_VERTEX'):
            bpy.ops.color_plus.edit_color(
                edit_type='apply',
                variation_value='color_wheel'
            )

        # Update draw brush in vertex color mode
        bpy.data.brushes["Draw"].color = (
            self.color_wheel[0], self.color_wheel[1], self.color_wheel[2]
        )

        # Convert the RGB value to HSV for easy tweaking
        color_wheel_hsv = colorsys.rgb_to_hsv(
            self.color_wheel[0], self.color_wheel[1], self.color_wheel[2]
        )

        # Set value/alpha variation preview
        self.value_var = colorsys.hsv_to_rgb(
            color_wheel_hsv[0], color_wheel_hsv[1], self.value_var_slider
        )
        self.alpha_var = (
            *(colorsys.hsv_to_rgb(color_wheel_hsv[0],
                                  color_wheel_hsv[1],
                                  color_wheel_hsv[2])),
            self.alpha_var_slider
        )

    def update_color_variation(self, context: Context):
        """Extension of `update_color_wheel`
        for color variation value."""
        self.update_color_wheel(context)

        # Update selected vertices if live color tweak is on
        if self.live_color_tweak \
        and context.mode in ('EDIT_MESH', 'PAINT_VERTEX'):
            bpy.ops.color_plus.edit_color(
                edit_type='apply',
                variation_value='value_var'
            )

    def update_alpha_variation(self, context: Context):
        """Extension of `update_color_wheel`
        for alpha variation value."""
        self.update_color_wheel(context)

        # Update selected vertices if live color tweak is on
        if self.live_color_tweak \
        and context.mode in ('EDIT_MESH', 'PAINT_VERTEX'):
            bpy.ops.color_plus.edit_color(
                edit_type='apply',
                variation_value='alpha_var'
            )

    def palette_update(self, _context: Context):
        bpy.ops.color_plus.refresh_palette_outliner()

    live_color_tweak: BoolProperty(
        name="Live Edit",
        description=\
            "If changing the Active Color will update the current selection"
    )

    interp_type: EnumProperty(
        items=(
            ('smooth', "Smooth", ""),
            ('hard', "Hard", "")
        )
    )

    custom_apply_option: EnumProperty(
        items=(
            ('apply_to_sel', "RGBA", ""),
            ('apply_to_sel_rgb', "RGB", ""),
            ('apply_to_sel_alpha', "Alpha", ""),
            ('apply_to_col', "Set Color", "")
        )
    )

    rgb_hsv_convert_options: EnumProperty(
        items=(
            ('colors_hsv', "HSV", ""),
            ('rgb', "RGB", "")
        ),
        update=palette_update
    )

    generate: EnumProperty(
        items=(
            ('per_uv_shell', "Per UV Shell  (Random Color)", ""),
            ('per_uv_border', "Per UV Border", ""),
            ('per_face', "Per Face", ""),
            ('per_vertex', "Per Vertex", ""),
            ('per_point', "Per Point (Face Corner)", ""),
            ('dirty_color', "Dirty Vertex Colors", "")
        ),
        name='Generation Type'
    )

    generate_per_uv_border: EnumProperty(
        items=(
            ('random_col', "Random Color", ""),
            ('active_col', "Active Color", "")
        )
    )

    color_wheel: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, 1],
        size=4,
        min=0,
        max=1,
        update=update_color_wheel
    )

    alt_color_wheel: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[1, 1, 1, 1],
        size=4,
        min=0,
        max=1
    )

    overlay_color_placeholder: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, 0],
        size=4,
        min=0,
        max=1
    )

    last_color_type: StringProperty()

    value_var_slider: FloatProperty(
        name="",
        description="Applies value variation to the selection without the need to change the Active Color (WARNING: This works with Live Tweak)",
        default=.5, min=0, max=1,
        subtype='FACTOR',
        update=update_color_variation
    )

    value_var: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.5, .5, .5], min=0, max=1
    )

    alpha_var_slider: FloatProperty(
        name="",
        description='Applies alpha variation to the selection without the need to change the Active Color (WARNING: This works with Live Tweak)',
        default=0, min=0, max=1,
        subtype='FACTOR',
        update=update_alpha_variation
    )

    alpha_var: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, .5], size=4,
        min=0, max=1
    )

    material_visibility: EnumProperty(
        items=(
            ('none', "None",       ""),
            ('.125', "0 (R=.125)", ""),
            ('.25',  "1 (R=.25)",  ""),
            ('.375', "2 (R=.375)", ""),
            ('.5',   "3 (R=.5)",   ""),
            ('.625', "4 (R=.625)", ""),
            ('.75',  "5 (R=.75)",  ""),
            ('.875', "6 (R=.875)", ""),
            ('1',    "7 (R=1)",    ""),
        ),
        name="Visibility Color",
        description="Alteration visibility color value to assign"
    )

    color_custom_1: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[1, 0, 0, 1], size=4,
        min=0, max=1
    )

    color_custom_2: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 1, 0, 1], size=4,
        min=0, max=1
    )

    color_custom_3: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 1, 1], size=4,
        min=0, max=1
    )

    color_custom_4: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.75, .75, .75, 1], size=4,
        min=0, max=1
    )

    color_custom_5: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.75, .75, 0, 1], size=4,
        min=0, max=1
    )

    color_custom_6: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, .75, .75, 1], size=4,
        min=0, max=1
    )

    color_custom_7: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.75, 0, .75, 1], size=4,
        min=0, max=1
    )

    color_custom_8: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.5, .5, .5, 1], size=4,
        min=0, max=1
    )

    color_custom_9: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.5, .75, 0, 1], size=4,
        min=0, max=1
    )

    color_custom_10: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, .5, .75, 1], size=4,
        min=0, max=1
    )

    color_custom_11: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.75, 0, .5, 1], size=4,
        min=0, max=1
    )

    color_custom_12: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.25, .25, .25, 1], size=4,
        min=0, max=1
    )

    color_custom_13: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.25, .5, 0, 1], size=4,
        min=0, max=1
    )

    color_custom_14: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, .5, .25, 1], size=4,
        min=0, max=1
    )

    color_custom_15: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[.25, 0, .5, 1], size=4,
        min=0, max=1
    )

    color_custom_16: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, 1], size=4,
        min=0, max=1
    )


class COLORPLUS_collection_property(bpy.types.PropertyGroup):
    def update_palette_color(self, _context: Context):
        if [*self.color] == [*self.saved_color]:
            return
        bpy.ops.color_plus.change_outliner_color(saved_active_idx=self.id)

        # This only somewhat fixes the
        # clearing [1,1,1,1] val colors
        if [*self.color[:3]] != [1, 1, 1] \
        and [*self.saved_color[:3]] != [1, 1, 1]:
            bpy.ops.color_plus.refresh_palette_outliner(
                saved_active_idx=self.id
            )

    id: IntProperty()
    color: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, 1],
        size=4,
        min=0,
        max=1,
        update=update_palette_color,
        description=\
            "Click to change the current color for this layer (WARNING: If the set color matches another color or is pure white it will be merged/removed!)"
    )
    saved_color: FloatVectorProperty(
        name="",
        subtype='COLOR_GAMMA',
        default=[0, 0, 0, 1],
        size=4,
        min=0,
        max=1
    )


#########################################
# PRESETS
#########################################


class COLORPLUS_MT_presets(Menu):
    bl_label = ""
    preset_subdir = "color_plus"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class COLORPLUS_PT_presets(PresetPanel, Panel):
    bl_label = "Color Presets"
    preset_subdir = 'color_plus'
    preset_operator = 'script.execute_preset'
    preset_add_operator = 'color_plus.preset_add'


class COLORPLUS_OT_add_preset(AddPresetBase, bpy.types.Operator):
    bl_idname = "color_plus.preset_add"
    bl_label = "Add a new preset"
    preset_menu = "COLORPLUS_MT_presets"

    # Variable used for all preset values
    preset_defines = ["color_plus=bpy.context.scene.color_plus"]

    # Properties to store in the preset
    preset_values = [
        "color_plus.color_custom_1",
        "color_plus.color_custom_2",
        "color_plus.color_custom_3",
        "color_plus.color_custom_4",
        "color_plus.color_custom_5",
        "color_plus.color_custom_6",
        "color_plus.color_custom_7",
        "color_plus.color_custom_8",
        "color_plus.color_custom_9",
        "color_plus.color_custom_10",
        "color_plus.color_custom_11",
        "color_plus.color_custom_12",
        "color_plus.color_custom_13",
        "color_plus.color_custom_14",
        "color_plus.color_custom_15",
        "color_plus.color_custom_16"
    ]

    # Where to store the preset
    preset_subdir = "color_plus"


############################################################
# USER PREFERENCES
############################################################


class COLORPLUS_MT_addon_prefs(AddonPreferences):
    bl_idname=__package__

    tabs: EnumProperty(
        items=(
            ('general', "General", "Information & Settings"),
            ('keymaps', "Keymaps", "Keymap Customization")
        )
    )

    auto_palette_refresh: BoolProperty(
        name="Auto Palette Refresh",
        description=
        '''If disabled, will stop updating the entire palette outliner whenever you run an operator.

Useful if your scene is slowing down.

Certain items may still be changed if the code interacts with the outliner directly''',
        default=True
    )

    max_outliner_items: IntProperty(
        name="Max Outliner Items",
        description='The maximum amount of items allowed in the Palette Outliner per object',
        default=25,
        min=1,
        max=100
    )

    def draw(self, context: Context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "tabs", expand=True)

        if self.tabs == 'general':
            col = layout.column()

            box = col.box()
            split = box.split()
            split.label(text='Automatically Refresh Palette Outliner')
            split.prop(self, 'auto_palette_refresh')

            col.separator(factor=.5)

            box = col.box()
            split = box.split()
            split.label(
                text=MAX_OUTLINER_ITEM_MSG + str(self.max_outliner_items)
            )
            split.prop(self, 'max_outliner_items')
        else: # Keymaps
            COLORPLUS_addon_keymaps.draw_keymap_items(
                context.window_manager, layout
            )


##################################
# REGISTRATION
##################################


classes = (
    COLORPLUS_MT_presets,
    COLORPLUS_PT_presets,
    COLORPLUS_OT_add_preset,
    COLORPLUS_MT_addon_prefs,
    COLORPLUS_property_group,
    COLORPLUS_collection_property,
    COLORPLUS_OT_add_hotkey
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.color_plus = PointerProperty(type=COLORPLUS_property_group)
    bpy.types.Object.color_palette = \
        CollectionProperty(type=COLORPLUS_collection_property)
    bpy.types.Object.color_palette_active = \
        IntProperty(
            name='R G B A values for the layer (Renaming does not work)'
        )

    # Assign keymaps & register
    COLORPLUS_addon_keymaps.new_keymap('Vertex Colors Pie',
                                       'wm.call_menu_pie',
                                       'COLORPLUS_MT_pie_menu',
                                       'Mesh', 'EMPTY', 'WINDOW', 'C',
                                       'PRESS', False, True, False)

    COLORPLUS_addon_keymaps.new_keymap('Fill Selection',
                                       'color_plus.edit_color',
                                       None,
                                       'Mesh', 'EMPTY', 'WINDOW', 'F',
                                       'PRESS', True, True, False, 'NONE')

    COLORPLUS_addon_keymaps.new_keymap('Clear Selection',
                                       'color_plus.edit_color_clear',
                                       None,
                                       'Mesh', 'EMPTY', 'WINDOW', 'F',
                                       'PRESS', False, True, True, 'NONE')

    COLORPLUS_addon_keymaps.register_keymaps()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    COLORPLUS_addon_keymaps.unregister_keymaps()

    del bpy.types.Scene.color_plus
    del bpy.types.Object.color_palette
    del bpy.types.Object.color_palette_active


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
