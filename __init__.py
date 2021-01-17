bl_info = {
    "name": "dp16's Various Tools",
    "author": "Sakenfor(dp16)",
    "version": (1, 0),
    "blender": (2, 79, 0),
    "location": "Toolpanel > Misc",
    "description": "All kind of useful things.",
    "warning": "",
    "category": "Object",
    }


from os import path as osp
import bpy,sys,bmesh
import numpy as np
from bpy import utils as butils
from bpy.app import handlers

base_dir = osp.dirname(osp.realpath(__file__))
if not base_dir in sys.path:sys.path.append(base_dir)
from general_tools import *

from bpy.types import (
    Operator,Object,
    Mesh,
    UIList,
    PropertyGroup,
    
    )
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    )


def specials_draw(self,context):
    row=self.layout.row()
    C=bpy.context
    ob=C.active_object
    if not ob:return
    if ob.type=="MESH":
        row.operator('dp16var.safely_remove_doubles')


class GroupsFile(Operator):
    bl_idname = "dp16ops.groups_file_base"
    bl_label = 'None'
    def invoke(self,context,event):
        self.event=event
        return self.execute(context)
    
    def execute(self,context):
    
        import json
        ob=context.active_object
        obj=ob.dp_helper
        active_group = obj.active_group
        if not active_group:return {"FINISHED"}
        
        path = '%s/%s.json'%(osp.dirname(bpy.data.filepath),active_group.name)
        
        if self.action == 'SAVE':
            with open(path,'w') as file:
                json.dump(active_group.indices,file, indent=1, sort_keys=True)
            print("Saved %s indices to %s"%(active_group.name,path))
            
        elif self.action == 'LOAD':
            with open(path,'r') as file:
                indices=json.load(file)
                bm,my_id=obj.bmesh_layer()
                for v in bm.verts:
                    v[my_id] = 1 if v.index in indices else 0
                active_group.update_length(bm,my_id)
                
                if self.event.ctrl:
                    obj.select_group(bm,my_id)

        return {"FINISHED"}

class GroupsFileSave(GroupsFile):
    bl_idname = 'dp16ops.groups_file_save'
    bl_label = 'Save'
    bl_description = "Save vertics indices of group to blend file's directory+group's name"
    action = 'SAVE'

class GroupsFileLoad(GroupsFile):
    bl_idname = 'dp16ops.groups_file_load'
    bl_label = 'Load'
    bl_description = 'Hold CTRL to select vertices after load'
    action = 'LOAD'

class GroupsManagement(Operator):
    bl_idname = "dp16ops.group_print_base"
    def invoke(self,context,event):
        #scene=context.scene
        self.event=event
        #self.ob=context.active_object
        return self.execute(context)
    
    def execute(self,context):

        context.active_object.dp_helper.operate_groups(self,self.action)
        return {"FINISHED"}
        
class TagVertsPrintIndices(GroupsManagement):
    '''Print indices'''
    bl_label = "Indices"
    bl_idname = "dp16ops.group_print_indices"
    action="INDICES"
    
class TagVertsAdd(GroupsManagement):
    '''Add selected vertices to object's active group'''
    bl_label = "Assign"
    bl_idname = "dp16ops.add_to_group"
    action="ADD"


class TagVertsSet(GroupsManagement):
    '''Set ONLY selected vertices to be part of the active group'''
    bl_label = "Set Group"
    bl_idname = "dp16ops.set_to_group"
    action="SET"

class TagVertsSelect(GroupsManagement):
    '''Select vertices of the active group'''
    bl_label = "Select"
    bl_idname = "dp16ops.select_group"
    action="SELECT"
    
class TagVertsDeselect(GroupsManagement):
    '''Deselect vertices of the active group'''
    bl_label = "Deselect"
    bl_idname = "dp16ops.deselect_group"
    action="DESELECT"
    
class TagVertsRemove(GroupsManagement):
    '''Remove selected vertices from the active group'''
    bl_label = "Remove"
    bl_idname = "dp16ops.remove_from_group"
    action="REMOVE"


def get_group_name(self):
    return self.get("name", "")

def set_group_name(self, value):
    oldname = self.get("name","")
    ob=self.id_data
    groups = ob.dp_helper.groups
    new_name = value
    digits = new_name.split('.')
    #if len(digits)>1:
    if digits[-1].isnumeric():
        new_name = value[:-4]
    already = groups.get(new_name)
    nn=1
    while already:
        new_name = '%s.%03d'%(value,nn)
        already = groups.get(new_name)
        if already == self:already=None
        nn+=1
    self["name"] = new_name
    if oldname != new_name:
        #return
        ob=self.id_data
        mode = ob.mode
        if ob.mode!='EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        #o=obj.obje
        me=ob.data
        bm = bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()
        vlayer = bm.verts.layers.float.get(oldname)
        if not vlayer:
            bpy.ops.object.mode_set(mode=mode)
            return
        vlayer_new = bm.verts.layers.float.new(new_name)
        vlayer_new.copy_from(vlayer)
        bm.verts.layers.float.remove(vlayer)


        old_color=me.vertex_colors.get(oldname)
        if old_color:
            old_color.name = new_name
            
        bpy.ops.object.mode_set(mode=mode)

def get_group_color(self):
    return self.get("color",(1,1,1))

def set_group_color(self, value):
    
    mode = self.id_data.mode
    if mode !='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    mesh = self.id_data.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    color_name="Groups Combined Colors" #self.name
    
    color_layer = bm.loops.layers.color.get(color_name) or bm.loops.layers.color.new(color_name)
    color_layer_single = bm.loops.layers.color.get(self.name) or bm.loops.layers.color.new(self.name)
    
    my_id = bm.verts.layers.float.get(self.name) or bm.verts.layers.float.new(self.name)
    bverts=[v for v in bm.verts if v[my_id]>0]
    
    color_table = {v : value for v in bverts}
    all_color_groups = [x.name for x in self.id_data.dp_helper.groups]
    

    for face in bm.faces:
        for loop in face.loops:
            if loop.vert in bverts:

                loop[color_layer_single] = color_table[loop.vert]

            else:
                loop[color_layer_single] = (1,1,1)
            
            mcols=[np.array(loop[ bm.loops.layers.color[id]]) for id in all_color_groups \
            if bm.loops.layers.color.get(id) and not all(x==1 for x in loop[bm.loops.layers.color[id]])
            ]
            if mcols:
                loop[color_layer] = tuple(np.divide(np.add.reduce(mcols) ,len(mcols)))
 
    bm.to_mesh(self.id_data.data)

    self["color"]=value
    bpy.ops.object.mode_set(mode=mode)

class VertexGroup(PropertyGroup):

    name=StringProperty(get=get_group_name,set=set_group_name)
    vertices_len=IntProperty()
    color = FloatVectorProperty(
        set=set_group_color,
        get=get_group_color,
        subtype='COLOR',
        default=(1,1,1),
        )
    
    @property
    def indices(self):
        return [ v.index for v in self.vertices ]
    
    def update_length(self,bm=None,my_id=None):
        bm.verts.ensure_lookup_table() #Not sure if needed
        self.vertices_len = len([v for v in bm.verts if v[my_id]>0])
    
    @property
    def vertices(self):

        mesh=self.id_data.data
        bm,my_id = self.id_data.dp_helper.bmesh_layer()
        b_ids=[v.index for v in bm.verts if v[my_id]>0]
        mesh_verts = mesh.vertices
        
        return [ mesh_verts[i] for i in b_ids ]

class dpDrawVertexGroupUI(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #item.draw_item(layout)
        row=layout.row()
        row=row.split(.45)
        row.prop(item,'name',text='',emboss=False,icon='ALIASED')
        if item.vertices_len:
            row.label('(%s)'%item.vertices_len)
            row.prop(item,'color',text='')
    def invoke(self, context, event):        
        pass   

class DpHelper(PropertyGroup):

    groups=CollectionProperty(type=VertexGroup)
    groups_index = IntProperty()
    groups_weight = FloatProperty(min=0,max=1,default=1,name='Weight',precision=4)
    do_draw_groups = BoolProperty(default=True)
    
    @property
    def active_group(self):
        return self.groups[self.groups_index] if self.groups_index <= len(self.groups)-1 else None
        
    def draw_groups(self,layout):
        if not self.do_draw_groups:return
        group = self.active_group
        ob=self.id_data
        #row=layout.row()
        #box=layout.box()
        row=layout.row()
        
        row.template_list("dpDrawVertexGroupUI", "", self, "groups", self, "groups_index", rows=2)
        template_list_control(row,4,group='objects["%s"].dp_helper'%self.id_data.name,member='groups')
        lay0=layout
        if ob.mode=='EDIT' and self.groups:
            row=layout.row()
            row.prop(self,'groups_weight',slider=1)
            row=layout.row()
            sub=row.row(align=1)
            sub.operator('dp16ops.add_to_group')
            sub=sub.split(.8,1)
            sub.operator('dp16ops.remove_from_group')
            #sub.operator('dp16ops.group_print_indices',text='',icon='STICKY_UVS_DISABLE',emboss=0)

            sub=row.row(align=1)
            sub.operator('dp16ops.select_group')
            sub.operator('dp16ops.deselect_group')
            lay0=row
        
        sub=lay0.row(align=1)
        sub.operator('dp16ops.groups_file_save',text='',icon='SAVE_AS')
        sub.operator('dp16ops.groups_file_load',text='',icon='LOAD_FACTORY')
        sub.operator('dp16ops.group_print_indices',text='',icon='STICKY_UVS_DISABLE',emboss=0)
    
    #@property
    def bmesh_layer(self,group_name=None):
        
        if not group_name:
            group_name=self.active_group.name
        bm = bmesh.from_edit_mesh(self.id_data.data)
        bm.verts.ensure_lookup_table()
        my_id = bm.verts.layers.float.get(group_name) or bm.verts.layers.float.new(group_name)
        
        return (bm,my_id)
    
    def select_group(self,bm=None,my_id=None,select=True,group=None):
        
        if not bm or not my_id:
            bm,my_id = self.bmesh_layer(group)
            
        bverts=[v for v in bm.verts if v[my_id]>0]
        bm.select_mode = {'VERT'}
        for v in bverts:
            v.select = select
        bm.select_flush_mode()   
        self.id_data.data.update()
    
    def operate_groups(self,operator,action):
        
        if not self.active_group:return
        group=self.active_group
        group_name=group.name

        bm,my_id=self.bmesh_layer()
        
        if action == "INDICES":
            print("Indices of %s's group \"%s\":\n%s"%(self.id_data.name,group_name,[v.index for v in bm.verts if v[my_id]==1]))
        
        elif action in {"SELECT","DESELECT"}:
            self.select_group(bm,my_id,action == "SELECT")

        else:

            if action=="ADD":
                for v in [x for x in bm.verts if x.select and not x.hide]:
                    v[my_id] = self.groups_weight
            
            elif action=="SET":
                for v in bm.verts:
                    v[my_id] = self.groups_weight if v.select else 0
            else:
                for v in [x for x in bm.verts if x.select and not x.hide]:
                    v[my_id] = 0
            
            group.update_length(bm,my_id)

def groups_menu_draw(self,context):
    self.layout.prop(context.active_object.dp_helper,'do_draw_groups',text='Draw helper groups',icon='ALIASED')

def vg_UI_draw(self, context):
    layout = self.layout

    ob = context.object.dp_helper
    #if context.object.mode == 'EDIT':
    ob.draw_groups(layout)

def post_load(scene):
    bpy.types.VIEW3D_MT_object_specials.append(specials_draw)


handlers.load_post.append(post_load)

register_classes = [
    TagVertsAdd,
    TagVertsSelect,
    TagVertsDeselect,
    TagVertsRemove,
    TagVertsPrintIndices,

    GroupsFileSave,
    GroupsFileLoad,

    VertexGroup,
    DpHelper,

    dpDrawVertexGroupUI,

    ]

from bpy.utils import register_class
for cls in register_classes:
    register_class(cls)
    
def register():

    Object.dp_helper = PointerProperty(type=DpHelper)
    
    bpy.types.VIEW3D_MT_object_specials.append(specials_draw)
    bpy.types.DATA_PT_vertex_groups.append(vg_UI_draw)
    bpy.types.MESH_MT_vertex_group_specials.append(groups_menu_draw)
    


def unregister():
    handlers.load_post.remove(post_load)
    del Object.dp_helper
    
    bpy.types.VIEW3D_MT_object_specials.remove(specials_draw)
    bpy.types.DATA_PT_vertex_groups.remove(vg_UI_draw)
    bpy.types.MESH_MT_vertex_group_specials.remove(groups_menu_draw)
    
