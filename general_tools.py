from bpy.types import (
Operator,
Mesh,
PropertyGroup,
UIList,
Object,
)

from bpy.props import (
StringProperty,
BoolProperty,
IntProperty,
CollectionProperty,
PointerProperty,
EnumProperty,
)

from bpy import utils as butils
import bpy

def remove_empty_vg(ob):

    ob.update_from_editmode()
    
    vgroup_used = {i: False for i, k in enumerate(ob.vertex_groups)}
    
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > 0.0:
                vgroup_used[g.group] = True
    
    for i, used in sorted(vgroup_used.items(), reverse=True):
        if not used:
            ob.vertex_groups.remove(ob.vertex_groups[i])

def copy_obj(scene,obj):
    o=obj.copy()
    if o.data:
        o.data=obj.data.copy()
    o.hide=0
    o.hide_select=0
    if o.name not in scene.objects:
        scene.objects.link(o)
    return o

crange_list=['ADD','REMOVE','UP','DOWN']
template_icons={'ADD':'ZOOMIN','REMOVE':'ZOOMOUT','UP':'TRIA_UP','DOWN':'TRIA_DOWN'}

def template_list_control(row,crange,group,member,align=1,col=None):
    if not col:
        col=row.column(align=align)
    for i in range(0,crange):
        cadd=col.operator('dp16.generic_list_add',text='',icon=template_icons[crange_list[i]])
        cadd.action=crange_list[i]
        cadd.group=group
        cadd.member=member


class generic_list_adder(Operator):

    bl_idname = "dp16.generic_list_add"
    bl_label = "Generic List Controller"
    bl_description = "Add, remove or move items in the list on the left side.\nHold Ctrl when adding to prompt naming window.\nHold Ctrl when removing to not prompt confirm."
    bl_options = {'REGISTER','UNDO'}
    
    group=StringProperty()
    member=StringProperty()
    action=StringProperty()
    new_member_name=StringProperty(name='Name')
    
    def execute(self,context):
    
        scene=context.scene
        #print(self.group)
        if 'scene' not in self.group and 'bpy.data' not in self.group:
            group=eval('scene.%s'%self.group)
        else:
            group = eval(self.group)
        collection=getattr(group,self.member)
        index='%s_index'%self.member
        sel_id=getattr(group,index)
        
        if self.action=='ADD':
            member=collection.add()
            n=self.new_member_name if self.new_member_name else 'new %s %s'%(self.member,len(collection))
            member.name=n
        
        elif self.action=='REMOVE':
            for i,g in enumerate(collection):
            
                if i==sel_id:
                    
                    remstr='on_%s_remove'%self.member
                    if hasattr(group,remstr):
                        getattr(group,remstr)(i)
                    collection.remove(i)
                    setattr(group,index,sel_id-1)
        elif self.action=='UP':
            if sel_id!=0:
                collection.move(sel_id,sel_id-1)
                setattr(group,index,sel_id-1)
        else:
        #elif self.action=='DOWN':
            if sel_id<len(collection)-1:
                collection.move(sel_id,sel_id+1)
                setattr(group,index,sel_id+1)
        
        return {"FINISHED"}
    
    def invoke(self,context,event):
        #self.event=event
        self.new_member_name=''
        if (self.action=='REMOVE' and not event.ctrl) or (event.ctrl and self.action=='ADD'):
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self,context):
        if self.action=='ADD':
            self.layout.prop(self,'new_member_name')
        else:
            self.layout.label("Confirm removal")


def transfer_normals(source,target,method='Normals Transfer'):
    mname='dpmhw_normals_transfer'
    target_state=[target.hide,target.hide_select]
    if method=='Normals Split':
        m=target.modifiers.new(mname,"NORMAL_EDIT")
        m.target=source
        m.mode='DIRECTIONAL'
        m.use_direction_parallel=1
    elif method=='Normals Transfer':
        m = target.modifiers.new(mname,"DATA_TRANSFER")
        m.use_loop_data = True
        m.loop_mapping = "NEAREST_POLYNOR"
        m.data_types_loops = {'CUSTOM_NORMAL'}
        m.object = source
    else:
        return
    #bpy.ops.object.select_all(action='DESELECT')
    target.select=1
    bpy.context.scene.objects.active=target
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.datalayout_transfer(modifier=mname)
    bpy.ops.object.modifier_apply(apply_as='DATA',modifier=mname)
    target.hide,target.hide_select=target_state

class SafelyRemoveDoubles(Operator):
    """Remove doubles and keep normals"""
    bl_idname = "dp16.safely_remove_doubles"
    bl_label="Safely Remove Doubles"
    bl_options= {'REGISTER','UNDO'}
    
    @classmethod 
    def poll(self,context):
        return context.active_object!=None
    def execute(self,context):
        
        scene=context.scene
        obj=context.active_object
        # bpy.ops.uv.seams_from_islands()
        # bpy.ops.mesh.select_mode(type="EDGE")
        nrm_src=copy_obj(scene,obj)
        if context.mode!='EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.reveal()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        transfer_normals(nrm_src,obj)
        bpy.data.objects.remove(nrm_src)
        return {"FINISHED"}

def join_bmesh(target_bm, source_bm):
    '''
    source_bm into target_bm
    returns target_bm with added geometry, if source_bm is not empty.
    '''

    source_bm.verts.layers.int.new('index')
    idx_layer = source_bm.verts.layers.int['index']
    nverts=[]
    for face in source_bm.faces:
        new_verts = []
        for old_vert in face.verts:
            #tag is False by defualt, Im using it to mean its been added
            if not old_vert.tag:
                new_vert = target_bm.verts.new(old_vert.co)
                target_bm.verts.index_update()
                old_vert[idx_layer] = new_vert.index
                old_vert.tag = True

            target_bm.verts.ensure_lookup_table()
            idx = old_vert[idx_layer]
            new_verts.append(target_bm.verts[idx])

        f=target_bm.faces.new(new_verts)
        nverts.extend(f.verts)
    return target_bm,list(set(nverts))

import bmesh
class GeoMerge(Operator):
    
    bl_idname = "dp16.geo_merge"
    bl_label="Geo Merge"
    bl_options= {'REGISTER','UNDO'}
    
    def invoke(self,context,event):
        
        #print(len(context.selected_objects))
        if len(context.selected_objects)>2:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self,context):
        #print("DRAWING")
        box=self.layout.box()
        row=box.row()
        target = context.active_object
        row.label(target.name)
        row.prop_search(target.dp_helper,'join_group',target.dp_helper,'groups',icon='SNAP_VOLUME',text='')
        row=box.row()
        row.prop(target.dp_helper,'merge_threshold')

    def execute(self,context):
        
        ob = context.active_object
        obj = context.active_object.dp_helper
        joins = context.selected_objects
        joins.remove(context.active_object)
        
        with obj.bm(0) as bm:
            
            merge_id = bm.verts.layers.float.get(obj.join_group)
            graft = obj.join_group and merge_id and len(joins)==1

            for j in joins:
                jm = bmesh.new()
                jm.from_mesh(j.data)
                _,new_verts = join_bmesh(bm,jm)
                #nw = 
                jm.clear()
                
            if graft:
                graft_verts = [ v for v in bm.verts if v[merge_id]>0]
                #print(graft_verts)
                bmesh.ops.remove_doubles(bm, verts=new_verts+graft_verts, dist=obj.merge_threshold)

            bm.to_mesh(ob.data)
            ob.data.update()
            bm.clear()
            bm.free()
        
        return {"FINISHED"}
            
def specials_draw(self,context):
    ob=context.active_object
    if not ob:return
    
    layout=self.layout#.row()
    if ob.type=="MESH":
        layout.operator('dp16.safely_remove_doubles')
        #layout.operator('dp16.geo_merge',icon='MESH_ICOSPHERE')
        #layout.operator('dp16.transfer_shapekey',icon='SHAPEKEY_DATA')



class TS_Choice(PropertyGroup):
    transfer =  BoolProperty(default=True)
    
class TransferChoiceGroup(PropertyGroup):
    choices = CollectionProperty(type=TS_Choice)
    choices_index = IntProperty()
    mesh = PointerProperty(type=Mesh)
    
    @property
    def name(self):
        return self.mesh.name
    
    def refresh_keys(self):
        
        kb = self.mesh.shape_keys.key_blocks
        for k in list(kb)[1:]:
            k2 = self.choices.get(k.name)
            if not k2:
                k2 = self.choices.add()
                k2.name = k.name
        for i,k in enumerate(list(reversed(self.choices))):
            if not kb.get(k.name):
                self.choices.remove(i)
    
    @property
    def transferable(self):
        return [ k for k in self.choices if k.transfer ]




class ShapeKeySettings(PropertyGroup):
    ssettings = CollectionProperty(type = TransferChoiceGroup)
    last_transfer = PointerProperty(type = Mesh)
    
    def get_shape_settings(self,mesh):
        if type(mesh) is Object:
            mesh = mesh.data
        for i,s in enumerate(self.ssettings):
            if s.mesh == mesh:
                return s
        s = self.ssettings.add()
        s.mesh = mesh
        #self.last_transfer = 
        
        return s
        
    def refresh(self,source):
        
        s = self.get_shape_settings(source.data)
        s.refresh_keys()
    

    def transfer(self, target, operator = None, transfer_type='Shape'):
        context = bpy.context
        
        s = self.get_shape_settings(target)
        obj = self.id_data.dp_helper
        ob = self.id_data
        me = ob.data
        source = context.selected_objects[:]
        source.remove(ob)
        
        if operator:
            transfer_type = operator.transfer_type
        #with obj.bm(1) as bm:
        if transfer_type == 'Shape':
            if not me.shape_keys:
                ob.shape_key_add("Basis")
            kb = me.shape_keys.key_blocks
            for sk in s.transferable:
                key = kb.get(sk.name)
                if not key:
                    key = ob.shape_key_add(sk.name)
            me.update()
        source_ob = source[0].dp_helper
        #print(operator,transfer_type)
        
        with obj.bm(1) as bm:
            indices_id = bm.verts.layers.int.get("indices_save")
            if transfer_type == 'ID' and not indices_id:
                indices_id = bm.verts.layers.int.new('indices_save')
            
            with source_ob.bm() as sbm:
                source_verts = sbm.verts
                indices_id2 = sbm.verts.layers.int.get("indices_save")
                if not indices_id2 or not indices_id :
                    operator.report({"ERROR"},"Store indices first in source AND target")
                    return
                
                if transfer_type == 'ID':
                    from mathutils import kdtree
                    size = len(source_verts)
                    kd = kdtree.KDTree(size)
                    for i,v in enumerate(source_verts):
                        kd.insert(v.co, i)
                    kd.balance()
                    for i,v in enumerate(bm.verts):
                        if not v.select:continue
                        closest = kd.find_n(v.co,2)
                        #print(closest)
                        v[indices_id] = source_verts[closest[1][1]][indices_id2]
                        

                elif transfer_type == 'Shape':
                    mapped_source = { v[indices_id2]:v for v in source_verts } 
                    
                    for k in s.transferable:
                        source_shape_lay = sbm.verts.layers.shape.get(k.name)
                        target_lay = bm.verts.layers.shape.get(k.name)
                        #source_v = {
                        for v in bm.verts:
                            if mapped_source.get(v[indices_id]):
                                v[target_lay] = mapped_source[v[indices_id]][source_shape_lay]

        me.update()

# create a kd-tree from a mesh
# me = ob.data
# size = len(me.vertices)
# kd = mathutils.kdtree.KDTree(size)
# for i, v in enumerate(me.vertices):
    # kd.insert(v.co, i)
# kd.balance()

'''create ordered list of closest vertex indices'''
# closest_vIdx = []
# for v in me.vertices:
    # co_find = v.co
    # closest_2 = kd.find_n(co_find,2)
    # closest_vIdx.append(closest_2[1][1])

'''Insert the index of the queried vertex here:'''
# vIdx = 5707

# print (f"vertex:{vIdx} closest vertex:{closest_vIdx[vIdx]}")

class TransferShapeKeyUI(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row=layout.row()
        row.label(item.name)
        row.prop(item,'transfer')
    
    def invoke(self, context, event):        
        pass 
        
class TransferShapekey(Operator):
    bl_idname = "dp16.transfer_shapekey"
    bl_label="Transfer ShapeKey"
    bl_options= {'REGISTER','UNDO'}
    transfer_type = EnumProperty(items=[(a,a,a) for a in ['Shape','ID']])
    
    def invoke(self,context,event):
        source = context.selected_objects[:]
        if len(source)!=2:return {"FINISHED"}
        source.remove(context.active_object)
        if self.transfer_type == 'ID' :return self.execute(context)
        context.active_object.dp_helper.sk_settings.refresh(source[0])
        
        return context.window_manager.invoke_props_dialog(self)
    
    
    def draw(self,context):
        source = context.selected_objects[:]
        source.remove(context.active_object)

        se = context.active_object.dp_helper.sk_settings.get_shape_settings(source[0])
        
        l = self.layout
        box=l.box()
        row=box.row()
        row.label("Choose which keys to transfer")
        row=box.row()
        row.template_list("TransferShapeKeyUI", "", se, "choices", se, "choices_index", rows=4)

    def execute(self,context):
        source = context.selected_objects[:]
        source.remove(context.active_object)
        
        context.active_object.dp_helper.sk_settings.transfer(source[0],self)
        
        return {"FINISHED"}

class dpDrawVertexGroupUI(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row=layout.row()
        row=row.split(.05)
        row.prop(item,'export',icon=['RADIOBUT_OFF','RADIOBUT_ON'][item.export],text='',emboss=0)
        row.prop(item,'name',text='',emboss=False)#,icon='ALIASED')
        lenl=''
        if item.vertices_len:
            lenl='(%s)'%item.vertices_len

        sub=row.split(.8,1)
        sub.label(lenl)
        sub.prop(item,'lock',icon=['UNLOCKED','LOCKED'][item.lock],text='')
        #sub.prop(item,'export',icon=['RADIOBUT_OFF','RADIOBUT_ON'][item.export],text='')
        sub.prop(item,'color',text='')
    
    def invoke(self, context, event):        
        pass   



register_classes = [
    TransferShapeKeyUI,
    dpDrawVertexGroupUI,
    
    TS_Choice,
    TransferChoiceGroup,
    ShapeKeySettings,
    TransferShapekey,
    
    SafelyRemoveDoubles,
    GeoMerge,
    generic_list_adder,
    ]
    
def register():
    from bpy.utils import register_class
    for cls in register_classes:
        register_class(cls)
        
def unregister():
    from bpy.utils import unregister_class
    for cls in register_classes:
        unregister_class(cls)
        
if __name__ == 'dpVariousTools.general_tools':
    register()

