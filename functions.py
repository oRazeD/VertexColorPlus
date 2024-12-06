from typing import Iterable

from bpy.types import Mesh, Attribute
from bmesh.types import BMesh, BMLayerItem, BMLoop, BMVert


def iterable_to_list(iterable: Iterable) -> list:
    """Convert 4-size iterable to a plain list."""
    converted_list = [iterable[0], iterable[1],
                      iterable[2], iterable[3]]
    return converted_list


def public_color_exists(data: Mesh) -> bool:
    """Check if any public color attributes exist.

    A private color attribute is classified as an
    attribute with a `_` name prefix."""
    public_attributes = []
    for attribute in data.color_attributes:
        if attribute.name.startswith("_"):
            continue
        public_attributes.append(attribute)
    if not public_attributes:
        return False
    return True


def create_color(data: Mesh, name: str="Attribute") -> Attribute:
    """Create color attribute from object mode."""
    color_attributes = data.color_attributes
    attribute = color_attributes.new(
        name, type='BYTE_COLOR', domain='CORNER'
    )
    color_attributes.active_color_index = \
    color_attributes.render_color_index = len(color_attributes)-1
    for idx in range(len(data.vertices)):
        attribute.data[idx].color = [1, 1, 1, 1]
    # NOTE: Alternatively, using foreach_set
    #cols = []
    #for idx in range(len(data.vertices)):
    #   cols += [1, 1, 1, 1]
    #attribute.data.foreach_set("color", cols)
    return attribute


def get_active_color(data: Mesh) -> Attribute | None:
    """Get the active color attribute from a given `Mesh`."""
    color_attributes = data.color_attributes
    if not color_attributes or not public_color_exists(data):
        return None

    idx = color_attributes.active_color_index
    if idx == -1:
        color_attributes.active_color_index = idx = 0

    try:
        return color_attributes[idx]
    except IndexError:
        return None


def get_bmesh_active_color(
        bm: BMesh, data: Mesh
    ) -> tuple[BMLayerItem, str] | None:
    """Get the active color attribute layer from `BMesh`.

    Returns `BMLayerItem` and the component type."""
    color_attributes = data.color_attributes
    if not color_attributes or not public_color_exists(data):
        return None, None

    idx = color_attributes.active_color_index
    if idx == -1:
        color_attributes.active_color_index = idx = 0

    try:
        attribute = color_attributes[idx]
    except IndexError:
        return None, None
    if attribute.domain == 'CORNER':
        if attribute.data_type == 'FLOAT_COLOR':
            return bm.loops.layers.float_color.get(attribute.name), "loop"
        return bm.loops.layers.color.get(attribute.name), "loop"
    if attribute.domain == 'POINT':
        if attribute.data_type == 'FLOAT_COLOR':
            return bm.verts.layers.float_color.get(attribute.name), "vert"
        return bm.verts.layers.color.get(attribute.name), "vert"
    return None, None


def get_component_colors(
        bm: BMesh, layer, layer_type: str, selected_only: bool=False
    ) -> dict[BMLoop | BMVert, list]:
    """Get all components (vert/edge/face) based on a given layer type.

    Returns a dict of `BMLoop` or `BMVert` and the color."""
    if layer_type == "loop":
        loops = []
        for face in bm.faces:
            for loop in face.loops:
                if not selected_only or loop.vert.select:
                    loops.append(loop)
        sequence = loops
    else: # Verts
        if selected_only:
            sequence = [vert for vert in bm.verts if vert.select]
        else:
            sequence = bm.verts

    components = {}
    for component in sequence:
        converted_color = iterable_to_list(component[layer])
        components[component] = converted_color
    return components


def component_select(component, layer_type) -> bool:
    if layer_type == "loop" and component.vert.select:
        return True
    if layer_type == "vert" and component.select:
        return True
    return False
