import bpy
import bmesh
from inspect import getmembers
from pprint import pprint

class SetupOperator(bpy.types.Operator):
    bl_idname = "blendertodayz.setup"
    bl_label = "Reset Scene"

    def remove_object(self, obj):

        if isinstance(obj, bpy.types.Collection):

            for child_col in obj.children:
                self.remove_object(child_col)

            for child in obj.all_objects:
                self.remove_object(child)

            bpy.data.collections.remove(obj)

        elif isinstance(obj, bpy.types.Object):
            #bpy.ops.object.select_all(action='DESELECT')
            #obj.select_set(True)
            #bpy.ops.object.delete() 
            bpy.data.objects.remove(obj, do_unlink=True)

    def unlink_all(self):

        context = bpy.context
        scene = context.scene

        for collection in scene.collection.children:
            self.remove_object(collection)


    def execute(self, context):

        self.unlink_all()
        self.main_collection = bpy.data.collections.new('p3d')
        bpy.context.scene.collection.children.link(self.main_collection)

        lod_count = 4

        self.lods = []

        for i in range(lod_count):
            new_lod = bpy.data.collections.new('lod_{}'.format(i + 1))
            self.lods.append(new_lod)
            self.main_collection.children.link(new_lod)

        self.geometry = bpy.data.collections.new('geometry')
        self.main_collection.children.link(self.geometry)

        self.view_geometry = bpy.data.collections.new('view_geometry')
        self.main_collection.children.link(self.view_geometry)

        self.memory = bpy.data.collections.new('memory')
        self.main_collection.children.link(self.memory)

        return {'FINISHED'}

class ExportOperator(bpy.types.Operator):
    bl_idname = "blendertodayz.export"
    bl_label = "Export To DayZ"
    current_collection = None

    def get_first_collection_by_name(self, master_collection, name):
        for collection in master_collection:
            if collection.name == name:
                return collection

        return None


    def process_vertex_groups(self, bobj, bm, file_pointer):

        grpIndex = 0

        mesh = bobj.data
 
        print(bobj.name)

        for v_group in bobj.vertex_groups:
            name = v_group.name
            
            file_pointer.write('\n:selection "{}"\n'.format(name))
            
            for vert in mesh.vertices:

                #print(len(vert.groups))

                for g in vert.groups:
                
                    if g.group == v_group.index:

                        file_pointer.write("{0} {1:.3f}\n".format(vert.index + 1, g.weight))

    def set_collection_objects_to_mode(self, new_mode):
        """
        scene = bpy.context.scene

        for obj in scene.objects:
            if obj.type == 'MESH' and not obj.hide_get():
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode=new_mode)
        """

        for obj in self.current_collection.all_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode=new_mode)

    def deselect_all(self):
        #bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

    def select_object(self, obj):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    def duplicate_objects(self, obj_list):

        self.deselect_all()

        for obj in obj_list:
            self.select_object(obj)

        bpy.ops.object.duplicate()

        duplicate_objects = bpy.context.selected_objects
        
        self.deselect_all()

        return duplicate_objects

    def process_lod(self, collection, lod_index, file_pointer):

        print("processing lod {}".format(lod_index))

        self.visual_lod = True
        # if false, skip materials, textures, etc...

        if isinstance(lod_index, str):
            file_pointer.write(':lod {}\n'.format(lod_index))
            self.geometry_lod = False
        else:
            file_pointer.write(':lod {}.0\n'.format(lod_index))

        self.set_collection_objects_to_mode('OBJECT')

        if len(collection.all_objects) > 0:

            objs_to_join = []

            for child in collection.all_objects:
                objs_to_join.append(child)

            duplicate_objects = self.duplicate_objects(objs_to_join)

            self.deselect_all()

            bpy.ops.object.add(type='MESH')
            temp_obj = bpy.context.active_object
            temp_obj.name = 'export_obj_'

            self.deselect_all()

            for obj in duplicate_objects:
                self.select_object(obj)

            self.select_object(temp_obj)


            bpy.ops.object.join()

            self.set_collection_objects_to_mode('EDIT')

            self.process_obj(temp_obj, file_pointer)
        else:
            file_pointer.write('\n:object\n')
            file_pointer.write(':points\n')

    def process_obj(self, obj, file_pointer):
        file_pointer.write('\n:object\n')
        file_pointer.write(':points\n')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.verify()

        for vert in bm.verts:

            vertex_pos = vert.co

            file_pointer.write('{} {} {}\n'.format(vertex_pos.x * 100, vertex_pos.y * 100, vertex_pos.z * 100))

        file_pointer.write('\n')

        print(len(bm.faces))

        for face in bm.faces:

            file_pointer.write(':face\n')

            f_vert_count = len(face.loops)

            file_pointer.write('index')

            for i in range(f_vert_count):
                file_pointer.write(' {}'.format(face.loops[i].vert.index + 1))

            file_pointer.write('\n')

            file_pointer.write('uv')

            for i in range(f_vert_count):
                file_pointer.write(' {} {}'.format(face.loops[i][uv_layer].uv[0], face.loops[i][uv_layer].uv[1]))


            file_pointer.write('\n')

            """
            file_pointer.write('index {} {} {} {}\n'.format(face.loops[0].vert.index + 1, face.loops[1].vert.index + 1, face.loops[2].vert.index + 1, face.loops[3].vert.index + 1))

            file_pointer.write(
                'uv {} {} {} {} {} {} {} {}\n'.format(
                    face.loops[0][uv_layer].uv[0],
                    face.loops[0][uv_layer].uv[1],
                    face.loops[1][uv_layer].uv[0],
                    face.loops[1][uv_layer].uv[1],
                    face.loops[2][uv_layer].uv[0],
                    face.loops[2][uv_layer].uv[1],
                    face.loops[3][uv_layer].uv[0],
                    face.loops[3][uv_layer].uv[1]
                )
            )
            """

            file_pointer.write('sg 1\n')

            # if not a visual lod, don't parse mats.
            if self.visual_lod:

                if len(obj.material_slots) > 0:

                    mat = obj.material_slots[face.material_index].material

                    rvtex = None
                    rvmat = None
                    use_diffuse = True

                    if mat != None:

                        if 'rvmat' in mat:
                            rvmat = mat['rvmat']

                        if 'rvtex' in mat:
                            rvtex = mat['rvtex']

                        if 'use_diffuse' in mat:
                            use_diffuse = mat['use_diffuse']


                        if rvtex != None:
                            file_pointer.write('texture "{}"\n'.format(rvtex))
                        elif use_diffuse:
                            diffuse = mat.diffuse_color
                            file_pointer.write('texture "#(argb,8,8,3)color({},{},{},{},CO)"\n'.format(diffuse[0], diffuse[1], diffuse[2], diffuse[3]))
                        else:
                            pass # don't use texture or diffuse, untextured

                        if rvmat != None:
                            file_pointer.write('material "{}"\n'.format(rvmat))


        self.process_vertex_groups(obj, bm, file_pointer)

        bpy.data.objects.remove(obj, do_unlink=True)

    def is_collection_visible(self, target_collection, parent=None):

        if parent == None:
            vlayer = bpy.context.scene.view_layers['View Layer']
            parent = vlayer.layer_collection

        for col_layer in parent.children:
            if col_layer.name == target_collection.name:
                return col_layer.is_visible
            else:
                is_vis = self.is_collection_visible(target_collection, col_layer)

                if is_vis != None:
                    return is_vis

        return None

    def execute(self, context):

        file_pointer = open("output.bitxt", "w")

        file_pointer.write(':header\n')
        file_pointer.write('version 1.0\n')
        file_pointer.write('sharp sg\n\n')

        p3d_collection = bpy.data.collections['p3d']

        for child_col in p3d_collection.children:

            self.current_collection = child_col

            if not self.is_collection_visible(child_col):
                print('collection {} is hidden, not exporting...\n'.format(child_col.name))
                continue

            name = child_col.name

            
            if name.startswith('lod_'):
                lod_index = int(name.partition("lod_")[2])
                self.process_lod(child_col, lod_index, file_pointer)
            elif name == 'geometry':
                self.process_lod(child_col, '1e+013', file_pointer)
            elif name == 'view_geometry':
                self.process_lod(child_col, "6e+015", file_pointer)
            elif name == 'memory':
                self.process_lod(child_col, '1e+015', file_pointer)
            

        #self.process_dayz_collection(self.get_first_collection_by_name(bpy.data.collections, "p3d"), file_pointer)

        file_pointer.write('\n:end')

        file_pointer.close()

        return {'FINISHED'}


class BlenderToDayZPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Blender To DayZ"
    bl_idname = "OBJECT_PT_BlenderToDayZPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_catagory = 'BToDayZ'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.scale_y = 3.0
        row.operator("blendertodayz.setup")

        row = layout.row()
        row.scale_y = 3.0
        row.operator("blendertodayz.export")
