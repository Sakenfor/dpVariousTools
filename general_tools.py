from bpy.types import (
Operator,
)
from bpy.props import (
StringProperty,
)
from bpy import utils as butils
import bpy

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
        cadd=col.operator('dp16ops.generic_list_add',text='',icon=template_icons[crange_list[i]])
        cadd.action=crange_list[i]
        cadd.group=group
        cadd.member=member


class generic_list_adder(Operator):
    bl_idname = "dp16ops.generic_list_add"
    bl_label = "Generic List Controller"
    bl_description = "Add, remove or move items in the list on the left side.\nHold Ctrl when adding to prompt naming window.\nHold Ctrl when removing to not prompt confirm."
    bl_options = {'REGISTER','UNDO'}
    
    group=StringProperty()
    member=StringProperty()
    action=StringProperty()
    new_member_name=StringProperty(name='Name')
    
    def execute(self,context):
    
        scene=context.scene
        group=eval('scene.%s'%self.group)
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
    bl_idname = "dp16ops.safely_remove_doubles"
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


register_classes = [
    SafelyRemoveDoubles,
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

