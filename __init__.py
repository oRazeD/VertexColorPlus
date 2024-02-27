bl_info = {
    "name":"Vertex Colors Plus",
    "author":"Ethan Simon-Law",
    "location": "3D View > Sidebar > Vertex Color",
    "version":(0, 3),
    "blender":(3, 6, 7),
    "tracker_url": "https://discord.com/invite/wHAyVZG",
    "category": "3D View"
}


import importlib


module_names = (
    "ui",
    "operators",
    "preferences"
)

modules = []
for module_name in module_names:
    if module_name in locals():
        modules.append(importlib.reload(locals()[module_name]))
    else:
        modules.append(importlib.import_module(f".{module_name}", __package__))

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in modules:
        mod.unregister()


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
