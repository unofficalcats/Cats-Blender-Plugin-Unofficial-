# MIT License

import bpy

from . import common as Common
from .register import register_wrap
from .. import globs
from .translations import t

from .rootbone import get_parent_root_bones

@register_wrap
class LoadBonesButton(bpy.types.Operator):
    bl_idname = 'cats_bonemerge.load_bones'
    bl_label = t('LoadBonesButton.label')
    bl_description = t('LoadBonesButton.desc')
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return Common.get_armature() is not None

    def execute(self, context):
        armature = Common.get_armature()
        
        globs.root_bones_choices = {}
        choices = get_parent_root_bones(self, context)
        
        wrapped_items = Common.wrap_dynamic_enum_items(
            lambda s, c: choices,
            'merge_bone'
        )
        
        bpy.types.Scene.merge_bone = bpy.props.EnumProperty(
            name=t('Scene.merge_bone.label'),
            description=t('Scene.merge_bone.desc'),
            items=wrapped_items
        )

        return {'FINISHED'}

@register_wrap
class BoneMergeButton(bpy.types.Operator):
    bl_idname = 'cats_bonemerge.merge_bones'
    bl_label = t('BoneMergeButton.label')
    bl_description = t('BoneMergeButton.desc')
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return (context.scene.merge_bone in globs.root_bones and 
                Common.is_enum_non_empty(context.scene.merge_mesh))

    def execute(self, context):
        saved_data = Common.SavedData()
        armature = Common.set_default_stage()
        
        # Cache bones dictionary
        bones_dict = {bone.name: bone for bone in armature.data.bones}
        
        parent_bones = globs.root_bones[context.scene.merge_bone]
        mesh = Common.get_objects()[context.scene.merge_mesh]
        ratio = context.scene.merge_ratio

        did = 0
        todo = 0
        for bone_name in parent_bones:
            bone = bones_dict.get(bone_name)
            if not bone:
                continue

            for child in bone.children:
                todo += 1

        wm = bpy.context.window_manager
        wm.progress_begin(did, todo)

        # Process bones using cached dictionary
        for bone_name in parent_bones:
            print('\nPARENT: ' + bone_name)
            bone = bones_dict.get(bone_name)
            if not bone:
                continue

            children = [child.name for child in bone.children]

            for child_name in children:
                child = bones_dict.get(child_name)
                print('CHILD: ' + child.name)
                self.check_bone(mesh, child, ratio, ratio, bones_dict)
                did += 1
                wm.progress_update(did)

        saved_data.load()
        wm.progress_end()
        
        self.report({'INFO'}, t('BoneMergeButton.success'))
        return {'FINISHED'}

    def check_bone(self, mesh, bone, ratio, i, bones_dict):
        if bone is None:
            print('END FOUND')
            return

        i += ratio
        bone_name = bone.name

        # Collect children names
        children = [child.name for child in bone.children]
        
        # Collect vertex groups for batched processing
        mix_operations = []

        if i >= 100:
            i -= 100
            if bone.parent is not None:
                parent_name = bone.parent.name
                vg = mesh.vertex_groups.get(bone_name)
                vg2 = mesh.vertex_groups.get(parent_name)
                
                if vg is not None and vg2 is not None:
                    mix_operations.append((bone_name, parent_name))

        # Batch process vertex group operations
        if mix_operations:
            Common.set_default_stage()
            Common.remove_rigidbodies_global()
            Common.set_active(mesh)
            
            for bone_name, parent_name in mix_operations:
                Common.mix_weights(mesh, bone_name, parent_name)
                Common.remove_bone(bone_name)

        # Process children using cached bones
        for child_name in children:
            child_bone = bones_dict.get(child_name)
            if child_bone is not None:
                self.check_bone(mesh, child_bone, ratio, i, bones_dict)
