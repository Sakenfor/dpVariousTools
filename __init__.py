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
from contextlib import contextmanager 
from collections import OrderedDict
from importlib import reload as lib_reload

if 'gt' in locals():
    lib_reload(general_tools)
else:
    from . import general_tools as gt

from bpy.types import (
    Operator,Object,
    Mesh,
    PropertyGroup,
    Menu,

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
from bmesh.types import BMesh

class IndicesStoreMenu(Menu):
    bl_idname = "dp16.indices_store_menu"
    bl_label = "Indices"
    
    def draw(self, context):
        layout = self.layout
        layout.label("Hello")
        
class GroupsMenu(Menu):
    bl_idname = "dp16.groups_menu"
    bl_label = "Select"

    def draw(self, context):
        layout = self.layout
        layout.label('Groups:',icon='TRIA_DOWN')
        layout.operator('dp16.groups_file_save',icon='SAVE_AS')
        layout.operator('dp16.groups_file_load',icon='LOAD_FACTORY')
        layout.operator('dp16.group_print_indices',icon='STICKY_UVS_DISABLE')
        layout.operator('dp16.groups_clean_all',icon='PANEL_CLOSE')
        #layout.menu('dp16.indices_store_menu',icon='LINENUMBERS_ON')
        layout.separator()
        layout.label('Indices:',icon='TRIA_DOWN')
        layout.operator('dp16.store_indices',icon='VERTEXSEL')
        layout.operator('dp16.restore_indices',icon='RECOVER_LAST')
        layout.separator()
        layout.label('Mesh:',icon='TRIA_DOWN')
        layout.operator('dp16.select_ngons',icon='FACESEL')
        layout.operator('dp16.geo_merge',icon='MESH_ICOSPHERE')
        layout.label('Transfer:',icon='TRIA_DOWN')
        layout.operator('dp16.transfer_shapekey',icon='SHAPEKEY_DATA',text='Shapes').transfer_type = 'Shape'
        layout.operator('dp16.transfer_shapekey',icon='COPY_ID',text='Indices').transfer_type = 'ID'
        

class GroupsFile(Operator):


    def invoke(self,context,event):
        self.event=event
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
            #return context.window_manager.invoke_props_dialog(self)
        #return self.execute(context)
    
    def execute(self,context):
        
        ob=context.active_object
        obj=ob.dp_helper
        path = self.filepath
        if not path.endswith('.txt'):
            self.report({"WARNING"},"Path %s was not a .txt file, did not save!"%self.filepath)
            return {"FINISHED"}
        sign='='
        mode=ob.mode
        if mode !='OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if self.action == 'SAVE':
            indices_save=[]
            with obj.bm() as bm:
                bmv = bm.verts
                bmv.ensure_lookup_table()
                for g in [ _ for _ in obj.groups if _.export ]:
                    
                    my_id = bmv.layers.float.get(g.name)# or bm.verts.layers.float.new(group_name)
                    if not my_id:continue
                    indices_save.append('%s%s%s'%(g.name,sign,[v.index for v in bmv if v[my_id]>0]))

            if osp.exists(osp.dirname(path)) and indices_save:
                with open(path,'w') as file:
                    file.write(str('\n'.join(x for x in indices_save)))
                

        elif self.action == 'LOAD':
            from ast import literal_eval

            with open(path,'r') as file:
                raw = file.read()
                bm = bmesh.new()
                bm.from_mesh(ob.data)
                bm.verts.ensure_lookup_table()
                for line in raw.split('\n'):
                    line=line.strip(' ')
                    if sign not in line or line.startswith('//'):continue
                    name,indices = line.split(sign)
                    name=name.strip('"')
                    indices = literal_eval(indices)
                    
                    group = obj.groups.get(name)
                    if not group:
                        group = obj.groups.add()
                        group.name = name
                        #continue
                    if group.lock:continue
                    
                    my_id = bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)
                    
                    for v in bm.verts:
                        v[my_id] = 1 if v.index in indices else 0

                    group.update_length(bm,my_id)

                bm.to_mesh(ob.data)
                
        bpy.ops.object.mode_set(mode=mode)


        return {"FINISHED"}
    
    def draw(self,context):
        #layout=self.layout
        box=self.layout.box()
        row=box.row()
        ob=context.active_object
        obj=ob.dp_helper
        
class GroupsClean(Operator):
    bl_idname = 'dp16.groups_clean_all'
    bl_label = 'Clean'
    bl_description = "Remove all groups from this object,\nHold Ctrl to not prompt confirm"
    
    @classmethod
    def poll(self,context):
        return len(context.active_object.dp_helper.groups)
        
    def invoke(self,context,event):
        if event.ctrl:return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self,context):
        self.layout.label("Are you sure?")
    
    def execute(self,context):
        context.active_object.dp_helper.clean_groups()
        return {"FINISHED"}

class HelperStoreIndices(Operator):

    def execute(self,context):
        context.active_object.dp_helper.do_indices_storage(self.ACTION)
        
        return {"FINISHED"}

class StoreIndices(HelperStoreIndices):
    bl_idname = 'dp16.store_indices'
    bl_label = 'Store'
    bl_description = 'Store vertex indices in bmesh layer'
    ACTION = 'STORE'
    
class RestoreIndices(HelperStoreIndices):
    bl_idname = 'dp16.restore_indices'
    bl_label = 'Restore'
    ACTION = 'RESTORE'
    bl_description = 'Restore vertex indices from bmesh layer. NOTE: When extruding geomtry, bmesh layers are copied too!'
    
class HelperNgonsSelect(Operator):
    bl_idname = 'dp16.select_ngons'
    bl_label = 'Ngons'
    bl_description = "Select Ngons (Faces with more than 4 vertices)"
    

    def execute(self,context):
        context.active_object.dp_helper.select_ngons()
        
        return {"FINISHED"}



class GroupsFileSave(GroupsFile):
    bl_idname = 'dp16.groups_file_save'
    bl_label = 'Save'
    bl_description = "Save indices to a file"
    
    action = 'SAVE'

    filepath = StringProperty(subtype = 'FILE_PATH')
    filter_glob = StringProperty(
        default='*.txt',
        options={'HIDDEN'}
    )
    
    @classmethod
    def poll(self,context):
        return len(context.active_object.dp_helper.groups)
        
class GroupsFileLoad(GroupsFile):
    bl_idname = 'dp16.groups_file_load'
    bl_label = 'Load'
    bl_description = 'Load indices from a file'
    action = 'LOAD'
    filepath = StringProperty(subtype = 'FILE_PATH')
    filter_glob = StringProperty(
        default='*.txt',
        options={'HIDDEN'}
    )
    
class GroupsManagement(Operator):
    
    def invoke(self,context,event):
        self.event=event
        return self.execute(context)
    
    def execute(self,context):

        context.active_object.dp_helper.operate_groups(self,self.action)
        return {"FINISHED"}

class TransferOperator(Operator):
    bl_idname = 'dp16.transfer_weights'
    bl_label = 'Transfer'
    bl_description = 'Transfer weights from source object on the left'
    
    def invoke(self,context,event):
        self.event=event
        return self.execute(context)
    
    def execute(self,context):
        
        context.active_object.dp_helper.transfer_weight(operator=self)
        return {"FINISHED"}



class TagVertsPrintIndices(GroupsManagement):
    '''Print indices'''
    bl_label = "Indices"
    bl_idname = "dp16.group_print_indices"
    action="INDICES"
    
    @classmethod
    def poll(self,context):
        return len(context.active_object.dp_helper.groups)
        
class TagVertsAdd(GroupsManagement):
    '''Add selected vertices to object's active group'''
    bl_label = "Assign"
    bl_idname = "dp16.add_to_group"
    action="ADD"

class TagVertsSet(GroupsManagement):
    '''Set ONLY selected vertices to be part of the active group'''
    bl_label = "Set Group"
    bl_idname = "dp16.set_to_group"
    action="SET"

class TagVertsSelect(GroupsManagement):
    '''Select vertices of the active group'''
    bl_label = "Select"
    bl_idname = "dp16.select_group"
    action="SELECT"
    
class TagVertsDeselect(GroupsManagement):
    '''Deselect vertices of the active group'''
    bl_label = "Deselect"
    bl_idname = "dp16.deselect_group"
    action="DESELECT"
    
class TagVertsRemove(GroupsManagement):
    '''Remove selected vertices from the active group'''
    bl_label = "Remove"
    bl_idname = "dp16.remove_from_group"
    action="REMOVE"


def get_group_name(self):
    return self.get("name", "")

def set_group_name(self, value):
    oldname = self.get("name","")
    ob=self.id_data
    groups = ob.dp_helper.groups
    new_name = value

    already = groups.get(value)
    if already == self:already=None
    # if already:
        # digits = new_name.split('.')
        # if len(digits)>1:
            # if digits[-1].isnumeric():
                # new_name = value[:-4] 
    nn=1
    while already:
        new_name = '%s.%03d'%(value,nn)
        already = groups.get(new_name)
        if already == self:
            already=None
            #new_name = value
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
    export=BoolProperty(
        default=True,
        description='Toggle off to not export to file this group, when saving',
        )
    lock=BoolProperty(
        default=False,
        description='Loading indices from a file will not affect this group',
        )
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
        bm,my_id = self.id_data.dp_helper.bmesh_layer(self.name)
        b_ids=[v.index for v in bm.verts if v[my_id]>0]
        mesh_verts = mesh.vertices
        
        return [ mesh_verts[i] for i in b_ids ]
    
    @property
    def verts(self):
        bm,my_id = self.id_data.dp_helper.bmesh_layer(self.name)
        return [ v for v in bm.verts if v[my_id]>0]
        #mesh_verts = mesh.vertices


def mesh_poll(self,o):
    return o.data and o.data.bl_rna.name == 'Mesh'


BM_Track = {}


class DpObjectHelper(PropertyGroup):

    groups=CollectionProperty(type=VertexGroup)
    groups_index = IntProperty()
    groups_weight = FloatProperty(min=0,max=1,default=1,name='Weight',precision=4)
    do_draw_groups = BoolProperty(default=True)
    to_mesh=BoolProperty()
    sk_settings = PointerProperty(type = gt.ShapeKeySettings)
    wgt_source = PointerProperty(type = Object,
        poll = mesh_poll,
        name='Source',
        description = 'Source of weight transfer',
        )
    wgt_selected = BoolProperty(
        name = 'Selected',
        description = '''Transfer weights only to selected vertices.
NOTE: This check is done with "Group" option too, IF this is enabled!
In short it is acumulative''',
        )
    wgt_group = StringProperty(
        name = 'Group',
        description = 'Group of vertices to use when transfering',
        )
    wgt_use_group = BoolProperty(
        name = 'Limit to group',
        description = 'Toggle on to choose and transfer ONLY to chosen group of vertices',
        
        )
    wgt_topology = BoolProperty(name = 'Topo',
        description = '''Modifier will have "Topology" method on.
But IF number of vertices is not same, it will be skipped (a light check)'''        
        )
    
    wgt_dis_arma = BoolProperty(
        default = True,
        description = '''Temporarily turn off armature modifiers on both objects when transfering weights'''
        )
    wgt_clean_after = BoolProperty(
        default = True,
        description = '''Remove unused vertex groups after the transfer
NOTE: Useful to leave ON, if groups have .R,.L, and you want to mirror the mesh later''',
        )
    @property
    def BM(self):
        return BM_Track.get(self)
        
    @BM.setter
    def BM(self,v):
        BM_Track[self] = v
    
    @BM.deleter
    def BM(self):
        del BM_Track[self]
    
    join_group = StringProperty()
    merge_threshold = FloatProperty(
        min=0.000001,
        max=0.02,
        default=0.0001,
        precision=6,
        name='Threshold',
        )
    
    def log(self,*args):
        print(args)
    
    def wgt_transfer_draw(self,layout):
        row=layout.row()
        box=row.box()
        row=box.row()
        row=row.split(.14,1)
        row.operator('dp16.transfer_weights',icon='PLAY')
        #row.separator()
        row=row.split(.5,1)
        row.prop(self,'wgt_source',text='')
        
        row.split()
        row.prop(self,'wgt_selected',text='Sel',icon='RESTRICT_SELECT_OFF')
        row.prop(self,'wgt_topology',text='Topo',icon = 'RETOPO')
        row.prop(self,'wgt_dis_arma',text='',icon='OUTLINER_DATA_ARMATURE')
        row.prop(self,'wgt_clean_after',text='',icon='STICKY_UVS_DISABLE')
        row=box.row(1)
        row.prop(self,'wgt_use_group',icon='STICKY_UVS_DISABLE')
        if self.wgt_use_group:
            row.prop_search(self,'wgt_group',self,'groups',text='')
    
    def transfer_weight(self, src = None, operator = None):
        if not src:
            src = self.wgt_source
        if not src:
            return
        if not src.data or src.data and src.data.bl_rna.name!='Mesh':
            print("Source was not a mesh")
            return
            
        ob = self.id_data
        mname = 'QuickTransfer'
        m = ob.modifiers.get(mname)
        if not m:
            m = ob.modifiers.new(mname, type='DATA_TRANSFER')
        
        while ob.modifiers.find(mname) != 0:
            bpy.ops.object.modifier_move_up(modifier=mname)
        m.use_vert_data = True
        m.data_types_verts = {'VGROUP_WEIGHTS'}
        #wgr = None
        wgr = ob.vertex_groups.get('temp_transfer_group')
        if not wgr:
            wgr = ob.vertex_groups.new(name = 'temp_transfer_group')
        mesh = ob.data
        with self.bm() as bm:
            '''
            Enter bmesh mode if we are transfering selected vertices only,
            so we can faster assign weights to selected vertices vertex group,
            '''
            sel_v_bk = [ v.index for v in mesh.vertices if v.select ]
            bm.verts.layers.deform.verify()
            bm.verts.ensure_lookup_table()
            myv = bm.verts
            srcv = len(src.data.vertices)
            myv_len = len(myv)
            
            if self.wgt_topology and myv_len == srcv:
                m.vert_mapping = 'TOPOLOGY'
            else:
                m.vert_mapping = 'POLYINTERP_NEAREST'
            
            
            m.object = src
            limit_group = self.groups.get(self.wgt_group)
            valid_v = set(myv)

            if self.wgt_use_group and limit_group:
                
                valid_v = set(limit_group.verts)
                
            if self.wgt_selected:
                valid_v = { v for v in valid_v if v.select }

            if not valid_v:
                self.log("No valid vertices for transfer %s > %s, aborted"%(source.name,ob.name))
                ob.modifiers.remove(m)
                ob.vertex_groups.remove(wgr) 
                return 
                
            if len(valid_v) != myv_len: 
                self.to_mesh = 1 #Upon exit of with self.bm, data is updated, cos new vertex group data
                
                dl = bm.verts.layers.deform.active
                for v in valid_v:
                    v[dl][wgr.index] = 1
                m.vertex_group = wgr.name
        
        preserve_options = {'armatures':not self.wgt_dis_arma}
        with self.preserve(**preserve_options):
            with src.dp_helper.preserve(**preserve_options):
                bpy.ops.object.datalayout_transfer(modifier=mname)
                bpy.ops.object.modifier_apply(apply_as='DATA',modifier=mname)
        
        
        #Remove leftover 0.0 weights on vertices
        if self.wgt_clean_after:
            remove_empty_vg(ob)
        bpy.context.scene.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL',limit=0)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for i in sel_v_bk:
            mesh.vertices[i].select = True

        if wgr:
            ob.vertex_groups.remove(wgr) 
    
    @contextmanager
    def preserve(self,armatures=1):
        '''
            with obj.dp_helper.preserve():
                do something
        '''
        ob = self.id_data
        try:
            
            modif_state = {}
            #if modifiers:
            for m in ob.modifiers:
                if m.type == 'ARMATURE' and not armatures:continue
                modif_state[m] = m.show_viewport
                m.show_viewport = False
            yield
        finally:
            for k,v in modif_state.items():k.show_viewport = v
            
    @contextmanager
    def bm(self,to_mesh=False,m='OBJECT'):
        mode=self.id_data.mode
        
        try:
            if mode!=m:
                bpy.ops.object.mode_set(mode=m)
            if m == 'OBJECT':
                bm = bmesh.new()
                bm.from_mesh(self.id_data.data)
            else:
                bm = bmesh.from_edit_mesh(self.id_data.data)
            self.BM = bm
            bm.verts.ensure_lookup_table()
            yield bm
        
        finally:
            #print(to_mesh,self.to_mesh)
            if to_mesh or self.to_mesh:
                # try:
                bm.to_mesh(self.id_data.data)
                # except:
                    # pass
            bpy.ops.object.mode_set(mode=mode)
            self.to_mesh=False
            bm.free()
            del self.BM
            #self.BM = None
            
    
    def on_groups_remove(self,index):
        with self.bm(1) as bm:
            my_id = bm.verts.layers.float.get(self.groups[index].name)
            if my_id and bm.verts.layers.float:bm.verts.layers.float.remove(my_id)

    
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
        
        row.template_list("dpDrawVertexGroupUI", "", self, "groups", self, "groups_index", rows=4)
        col=row.column(align=True)
        gt.template_list_control(row,4,
            group='objects["%s"].dp_helper'%self.id_data.name,
            member='groups',
            col=col)
            
        col.menu('dp16.groups_menu',icon='DOWNARROW_HLT',text='')
        lay0=layout
        if ob.mode in {"EDIT","WEIGHT_PAINT"} and self.groups:
            row=layout.row()
            row.prop(self,'groups_weight',slider=1)
            row=layout.row()
            sub=row.row(align=1)
            sub.operator('dp16.add_to_group')
            sub=sub.split(.8,1)
            sub.operator('dp16.remove_from_group')
            #sub.operator('dp16.group_print_indices',text='',icon='STICKY_UVS_DISABLE',emboss=0)

            sub=row.row(align=1)
            sub.operator('dp16.select_group')
            sub.operator('dp16.deselect_group')
            lay0=row
    
    def select_ngons(self):
        with self.bm(1) as bm:
            bm.select_mode = {'FACE'}
            for f in bm.faces: 
                f.select=True if len(f.verts)> 4 else False
            bm.select_flush_mode()
            self.id_data.data.update()
        bpy.ops.object.mode_set(mode='EDIT')
    
    def bmesh_layer(self,group_name=None):
        
        print(self.BM,group_name)
        if not group_name:
            group_name=self.active_group.name
        if not self.BM: #Check if we are in "with self.bm"
            if self.id_data.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(self.id_data.data)
            else:
                bm = bmesh.new()
                bm.from_mesh(self.id_data.data)
        else:
            bm = self.BM
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
    
    def do_indices_storage(self,action):
        with self.bm(1) as bm:
            layer_id = bm.verts.layers.int.get("indices_save") or bm.verts.layers.int.new("indices_save")
            if action == 'STORE':
                for v in bm.verts:
                    v[layer_id] = v.index
            elif action == 'RESTORE':
                for v in bm.verts:
                    v.index = v[layer_id]
                bm.verts.sort()
            else:
                print([v[layer_id] for v in bm.verts])
                
    def clean_groups(self):
        with self.bm(1) as bm:
            while self.groups:

                my_id = bm.verts.layers.float.get(self.groups[0].name)
                if my_id and bm.verts.layers.float:bm.verts.layers.float.remove(my_id)
                self.groups.remove(0)
                
    def operate_groups(self,operator,action='SELECT'):

        if not self.active_group:return
        group=self.active_group
        group_name=group.name
        manip = action in {"ADD","SET","REMOVE"}

        with self.bm(m='EDIT' if not manip else 'OBJECT') as bm:

            my_id = bm.verts.layers.float.get(group_name) or bm.verts.layers.float.new(group_name)
            ob=self.id_data
            
            if action == "INDICES":
                operator.report({"INFO"},"Indices of %s's group \"%s\":"%(self.id_data.name,self.active_group.name))
                operator.report({"INFO"},str(self.active_group.indices))
                    

            elif action in {"SELECT","DESELECT"}:
                self.select_group(bm,my_id,action == "SELECT")

            else:
                
                self.to_mesh=True # on exit of context, will put bmesh to mesh
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

def modif_draw(self,context):
    ob = context.active_object
    if not ob.data:return
    if ob.data.bl_rna.name != 'Mesh':return
    ob.dp_helper.wgt_transfer_draw(self.layout)


def vg_UI_draw(self, context):
    layout = self.layout

    ob = context.object.dp_helper
    #if context.object.mode == 'EDIT':
    ob.draw_groups(layout)




register_classes = [
    TransferOperator,
    IndicesStoreMenu,
    GroupsMenu,
    
    StoreIndices,
    RestoreIndices,
    
    TagVertsAdd,
    TagVertsSelect,
    TagVertsDeselect,
    TagVertsRemove,
    TagVertsPrintIndices,
    
    HelperNgonsSelect,
    
    GroupsFileSave,
    GroupsFileLoad,
    GroupsClean,
    
    VertexGroup,
    DpObjectHelper,


    
    ]


def post_load(scene):
    bpy.types.VIEW3D_MT_object_specials.append(gt.specials_draw)
    # for cls in register_classes:
        # register_class(cls)

    
def register():
    from bpy.utils import register_class
    for cls in register_classes:
        register_class(cls)
        
    Object.dp_helper = PointerProperty(type=DpObjectHelper)
    handlers.load_post.append(post_load)
    bpy.types.VIEW3D_MT_object_specials.append(gt.specials_draw)
    bpy.types.DATA_PT_vertex_groups.append(vg_UI_draw)
    bpy.types.MESH_MT_vertex_group_specials.append(groups_menu_draw)
    bpy.types.DATA_PT_modifiers.prepend(modif_draw)


def unregister():
    from bpy.utils import unregister_class
    
    handlers.load_post.remove(post_load)
    del Object.dp_helper
    
    bpy.types.VIEW3D_MT_object_specials.remove(gt.specials_draw)
    bpy.types.DATA_PT_vertex_groups.remove(vg_UI_draw)
    bpy.types.MESH_MT_vertex_group_specials.remove(groups_menu_draw)
    bpy.types.DATA_PT_modifiers.remove(modif_draw)
    
    for cls in register_classes:
        unregister_class(cls)

if __name__ == '__main__':register()
