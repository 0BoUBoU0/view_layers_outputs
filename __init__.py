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

bl_info = {
    "name": "View Layers Outputs",
    "author": "Yannick 'BoUBoU' Castaing",
    "description": "add some tool to handle view layers for rendering",
    "location": "PROPERTIES > OUTPUT",
    "doc_url": "",
    "warning": "",
    "category": "View Layers",
    "blender": (3,6,0),
    "version": (1,4,3)
}

# get addon name and version to use them automaticaly in the addon
Addon_Name = str(bl_info["name"])
Addon_Version = str(bl_info["version"]).replace(",",".").replace("(","").replace(")","")

### import modules ###
import bpy
from random import uniform

### define global variables ###
debug_mode = False
separator = "-" * 20
precomp_scene_suffixe = "_Pre-Compositing"

def get_base_path(scene):
    # remove main output namefile to keep only filepath : 
    main_file_output = scene.render.filepath
    possible_separator = ["\\"]
    for separator in possible_separator:
        if separator in main_file_output:
            main_file_output = main_file_output.split(separator)
            file_name = main_file_output[-1]
            main_file_output.remove(file_name)
            main_file_output = separator.join(main_file_output)
            main_file_output = f"{main_file_output}{separator}"
    return main_file_output


## define addon preferences
class VLOUTPUT_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    precomp_checkbox_pref : bpy.props.BoolProperty(name="Precomp Tab", default=False, description = "if checked, show precomp tab")

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "precomp_checkbox_pref")

### create property ###
class VLOUTPUT_properties (bpy.types.PropertyGroup):
    selection_options = [("ALL SCENES","ALL SCENES","ALL SCENES",0),
                                ("CURRENT SCENE","CURRENT SCENE","CURRENT SCENE",1),
                                ("ALL SCENES WITH CURRENT SETTINGS","ALL SCENES WITH CURRENT SETTINGS","ALL SCENES WITH CURRENT SETTINGS",2)
                                ]
    ## outputs
    outputs_scenes_selection : bpy.props.EnumProperty (items = selection_options,name = "Scenes ?",description = "choose selection type",default=1)
    outputs_alpha_solo : bpy.props.BoolProperty (default=False,name="Render Alpha separatly",description="if unchecked, the alpha will be embeded in the main image file")
    output_reset_options = [("RESET ALL TREE","RESET ALL TREE","RESET ALL TREE",0),
                                ("ONLY UPDATE LINKS","ONLY UPDATE LINKS","Will update output links, meaning recreating links between nodes",1),
                                ("ONLY UPDATE PATHS","ONLY UPDATE PATHS","will update all outputs nodes paths",2),
                                #("UNUSED NODES","UNUSED NODES","UNUSED NODES",2),
                                #("NOTHING","NOTHING","NOTHING",3)
                                ]
    outputs_reset_selection : bpy.props.EnumProperty (items = output_reset_options,name = "",description = "Nodes reset",default=0)
    outputs_sort_options = [('Ascending','Ascending','Ascending',"SORT_ASC",0),
                            ('Descending','Descending','Descending',"SORT_DESC",1),
                            ('Unsorted','Unsorted','Unsorted',2),
                            ]
    outputs_sort : bpy.props.EnumProperty (items = outputs_sort_options,name = "Layers sort",description = "choose selection type",default=0)
    outputs_prefix : bpy.props.StringProperty(name="Pass Prefix",default="",description="")
    layer_folder : bpy.props.BoolProperty (default=True,name="One folder per layer",description="if checked, images sequences of each layer will be stored in a different folder")
    outputs_folder : bpy.props.BoolProperty (default=False,name="One folder per output",description="if checked, images sequences of each passes will be stored in folders")    
    corresponding : bpy.props.StringProperty(name="Translation",default="Image=rgba",description='translate field a to field b, separated by ",". I.E. "Image=rgba,Alpha=alpha"')
    clear_unusedSockets : bpy.props.BoolProperty (default=False,name="Clear Unused Output",description="if checked, clear user unused outputs")
    use_layerName_in_pass : bpy.props.BoolProperty (default=False,name="Use Layer Name",description="if checked, the view layer name will be added in each pass name")
    change_only_node_output : bpy.props.BoolProperty (default=False,name="Change Only Node Path",description="if checked, will only change in the node output path, without touching the base path")
    del_x_signs : bpy.props.IntProperty (default=0,name="Delete X First Signs",description="")

    path_to_change_options = [("Base Path","Base Path","base path from the main output",0),
                            ("Subpath","Subpath","subpath for all outputs of a node output",1)
                            ]
    path_to_change : bpy.props.EnumProperty (items = path_to_change_options,name = "Path to Change",description = "choose selection type",default=1)
    
    #basepath_prop: bpy.props.BoolProperty(default=False, name="", description='')
    basepath_previs: bpy.props.StringProperty(default="", name="", description='')
    #subpath_prop: bpy.props.BoolProperty(default=True, name="", description='')
    subpath_previs: bpy.props.StringProperty(default="[Layer Name]**\\**[Pass Name]**\\", name="Output previs", description='output path')
    customfield_a: bpy.props.StringProperty(default="", name="", description='First user custom field (A)')
    customfield_b: bpy.props.StringProperty(default="", name="", description='Second user custom field (B)')
    customfield_c: bpy.props.StringProperty(default="", name="", description='Third user custom field (C)')
    pathlength : bpy.props.IntProperty(default=0, name="", description='')
    postscript_checkbox : bpy.props.BoolProperty (default=False,name="",description="launch this script after action it")
    postscript : bpy.props.PointerProperty (type=bpy.types.Text, name="Additional Script", description="script to launch after the nodes creation")
    fileformat_checkbox : bpy.props.BoolProperty (default=False,name="",description="if checked, will use custom image type. If unchecked, will use the scene output file's type")
    fileformat_options = [ #'BMP', 'IRIS', 'PNG', 'JPEG', 'JPEG2000', 'TARGA', 'TARGA_RAW', 'CINEON', 'DPX', 'OPEN_EXR_MULTILAYER', 'OPEN_EXR', 'HDR', 'TIFF', 'WEBP'
                            ('BMP','BMP','BMP',0),
                            ('IRIS','IRIS','IRIS',1),
                            ('PNG','PNG','PNG',2),
                            ('JPEG','JPEG','JPEG',3),
                            ('JPEG2000','JPEG2000','JPEG2000',4),
                            ('TARGA','TARGA','TARGA',5),
                            ('TARGA_RAW','TARGA_RAW','TARGA_RAW',6),
                            ('CINEON','CINEON','CINEON',7),
                            ('DPX','DPX','DPX',8),
                            ('OPEN_EXR_MULTILAYER','OPEN_EXR_MULTILAYER','OPEN_EXR_MULTILAYER',9),
                            ('OPEN_EXR','OPEN_EXR','OPEN_EXR',10),
                            ('HDR','HDR','HDR',11),
                            ('TIFF','TIFF','TIFF',12),
                            ('WEBP','WEBP','WEBP',13),
                            ]
    fileformat : bpy.props.EnumProperty (items = fileformat_options,name = "Node Output Image Type",description = "choose image type",default=2)

    ## precomp
    precomp_bg_under : bpy.props.BoolProperty(default=False,name="",description="")
    precomp_bg_img : bpy.props.PointerProperty(type=bpy.types.Image, name="BG under", description="")
    precomp_freestyle : bpy.props.BoolProperty (default=True,name="Freestyle Over",description="if freestyle on separate pass, freestyle over")
    precomp_postscript_checkbox : bpy.props.BoolProperty (default=False,name="",description="launch this script after action it")
    precomp_postscript : bpy.props.PointerProperty (type=bpy.types.Text, name="Additional Script", description="script to launch after the nodes creation")
    
    
### create panels ###
# create panel UPPER_PT_lower
# for view 3D
class VLOUTPUT_PT_filesoutput(bpy.types.Panel):
    bl_label = f"View Layers Outputs - {Addon_Version}"
    bl_idname = "VLOUTPUT_PT_filesoutput"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = 'output'
    #bl_parent_id = "RENDER_PT_output"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='NODETREE')

    def draw(self, context):
        vloutputs_props = context.scene.vloutputs_props
        layout = self.layout
        ## update box
        uptbox = layout.box()
        split = uptbox.split(factor=.85, align = True)
        if vloutputs_props.pathlength>=64:
            text = "Cannot update (subpath too long)"
            icon = "STRIP_COLOR_01"
        else:
            text = "Update Layers outputs"
            icon = "OUTPUT"
        split.operator("vloutputs.createnodesoutput",text=text,emboss=True,depress=False,icon=icon)
        split.prop(vloutputs_props, "outputs_reset_selection")
        ## path selection
        outputs_basepathprevis = vloutputs_props.basepath_previs.replace("**", "")
        outputs_subpathprevis = vloutputs_props.subpath_previs.replace("**", "")
        pathbox = layout.box()
        ## box for each path
        row = pathbox.row()
        row.prop(vloutputs_props,"path_to_change",expand=True)
        row = pathbox.row()
        colA = row.column()
        bpbox = colA.box()
        colB = row.column()
        subbox = colB.box()
        if vloutputs_props.path_to_change == "Base Path": 
            bpbox.active = True
            subbox.active = False
            base_icon = "FOLDER_REDIRECT"
            sub_icon = "BLANK1"
        elif vloutputs_props.path_to_change == "Subpath": 
            bpbox.active = False
            subbox.active = True
            base_icon = "BLANK1"
            sub_icon = "FOLDER_REDIRECT"

        ## subpath box
        split = bpbox.split(factor=.9)
        #split = row.split(factor=.1)
        add_user = f" [+] {outputs_basepathprevis}" if outputs_basepathprevis != "" else ""
        split.label(icon=base_icon,text=f"Base_Path: {get_base_path(bpy.context.scene)}{add_user}")
        if vloutputs_props.path_to_change == "Base Path": 
            split.operator('vloutputs.dellastcharacter', text="", icon="TRIA_LEFT_BAR")
        bprow = bpbox.row()
        bprow.label(text="")

        ## subpath box
        row = subbox.row()
        split = row.split(align=True, factor=0.9)
        split.label(icon=sub_icon,text=f"Subpath: {outputs_subpathprevis}")
        if vloutputs_props.path_to_change == "Subpath": 
            split.operator('vloutputs.dellastcharacter', text="", icon="TRIA_LEFT_BAR")
        row = subbox.row()
        if vloutputs_props.pathlength>=64:
            str_check = "too long !!"
            icon = "STRIP_COLOR_01"
        else:
            str_check = "ok"
            icon = "STRIP_COLOR_04"
        row.label(icon=icon,text=f"length : {vloutputs_props.pathlength} on 64 ( {str_check} )")

        ## fields options
        box = layout.box()
        # text blocs
        def ui_blocs(list):
            iter = 0
            for char,label,descr,icon in list:
                operator = row.operator('vloutputs.add_character_enum', text=label,icon=icon)
                operator.character = char
                operator.tooltip = descr
                iter += 1
        # main options
        row = box.row()
        char_options_A = [
            ("[File Name]","", "File Name","FILE"),
            ("[Layer Name]","", "Layer Name","RENDERLAYERS"),
            ("[Pass Name]","","Pass Name","IMAGE_PLANE"),
            ("[File Version]","", "File Version","LINENUMBERS_ON"),
            ("[Scene Name]","", "Scene Name","SCENE_DATA"),
            ("[Camera Name]","", "Camera Name","CAMERA_DATA"),
            #("[Frame Number]", "Frame Number","TIME")
        ]
        ui_blocs(char_options_A)
        # separators
        #row = box.row()
        row.label(text="")
        char_options_B = [
            #("\\", "Backlash \\","NONE"),
            ("//","/", "Forward Slash /","NONE"),
            ("_","_", "Underscore _","NONE"),
            ("-","-", "Dash -","NONE"),
            (".",".", "Dot .","NONE"),
        ]
        ui_blocs(char_options_B)

class VLOUTPUT_PT_filesoutputfieldsoptions(bpy.types.Panel):
    bl_label = "Fields Options"
    bl_idname = "VLOUTPUT_PT_filesoutputfieldsoptions"
    bl_region_type = "WINDOW"
    bl_space_type = "PROPERTIES"
    bl_context = 'output'
    bl_parent_id = "VLOUTPUT_PT_filesoutput"
    bl_options = {"DEFAULT_CLOSED"}
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='SMALL_CAPS')

    def draw(self, context):
        vloutputs_props = context.scene.vloutputs_props
        layout = self.layout
        
        ### custom fields
        box = layout.box()
        row = box.row()
        row.label(text="Add custom fields:")
        row = box.row()
        split = row.split(factor=2/5)
        split.operator('vloutputs.add_character_enum', text="Custom A").character = "[Custom A]"
        split.prop(vloutputs_props, "customfield_a",text="" )
        split = row.split(factor=2/5)
        split.operator('vloutputs.add_character_enum', text="Custom B").character = "[Custom B]"
        split.prop(vloutputs_props, "customfield_b",text="" )
        row = box.row()
        split = row.split(factor=2/5)
        split.operator('vloutputs.add_character_enum', text="Custom C").character = "[Custom C]"
        split.prop(vloutputs_props, "customfield_c",text="" )
        split = row.split(factor=2/5)
        split.label(text="")
        split.label(text="")

        ### options
        box = layout.box()
        row = box.row()

        col2 = row.column()
        col2.prop(vloutputs_props, "output_custom_filepath",icon="FILE_FOLDER")
        row = col2.row()
        row.prop(vloutputs_props, "output_corresponding")

        row.prop(vloutputs_props, "change_only_node_output",icon="OUTLINER_DATA_LIGHTPROBE",text="")
        row.prop(vloutputs_props, "del_x_signs")

class VLOUTPUT_PT_filesoutputoptions(bpy.types.Panel):
    bl_label = "Advanced Options"
    bl_idname = "VLOUTPUT_PT_filesoutputoptions"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = 'output'
    bl_parent_id = "VLOUTPUT_PT_filesoutput"
    bl_options = {"DEFAULT_CLOSED"}
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='OPTIONS')

    def draw(self, context):
        vloutputs_props = context.scene.vloutputs_props

        layout = self.layout
        # misc options
        box = layout.box()
        row = box.row()
        row.prop(vloutputs_props, "outputs_sort")
        row.prop(vloutputs_props, "outputs_scenes_selection")
        row = box.row()
        row.prop(vloutputs_props, "outputs_alpha_solo")
        split = row.split(factor = .05)
        split.active = vloutputs_props.fileformat_checkbox
        split.prop(vloutputs_props, "fileformat_checkbox")
        split.prop(vloutputs_props, "fileformat")
        # add script
        box = layout.box()
        box.active = vloutputs_props.postscript_checkbox
        split = box.split(factor=.05)
        split.prop(vloutputs_props, "postscript_checkbox")
        split.prop(vloutputs_props, "postscript")

class VLOUTPUT_PT_precomptree(bpy.types.Panel):
    bl_label = f"Create Precomp Tree "
    bl_idname = "VLOUTPUT_PT_precomptree"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = 'output'
    bl_parent_id = "VLOUTPUT_PT_filesoutput"
    
    # # show the tab regarding preferences
    # @classmethod
    # def poll(cls, context):
    #     return context.preferences.addons[__name__].preferences.precomp_checkbox_pref

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='NODETREE')

    def draw(self, context):
        vloutputs_props = context.scene.vloutputs_props
        layout = self.layout
        bigbox = layout.box()
        split = bigbox.split(factor=.6)
        box = split.box()
        #row = box.row()
        box.operator("vloutputs.createprecomp",text="Create View Layers Pre-Comp Tree",emboss=True,depress=False,icon="NODE")

        # misc options
        box = layout.box()
        row = box.row()
        split = row.split(factor = .1)
        split.prop(vloutputs_props, "precomp_bg_under")
        split.active = vloutputs_props.precomp_bg_under
        split.prop(vloutputs_props, "precomp_bg_img")
        row = box.row()
        row.prop(vloutputs_props, "precomp_freestyle")
        #
        #row.prop(vloutputs_props, "precomp_input_prop")
        # add script
        box = self.layout.box()
        box.active = vloutputs_props.precomp_postscript_checkbox
        split = box.split(factor=.05)
        split.prop(vloutputs_props, "precomp_postscript_checkbox")
        split.prop(vloutputs_props, "precomp_postscript")


### create functions ###
# create function > create files output
def list_renderlayers(selected_scene,sort_option):
    ## variables
    selected_scene = selected_scene
    sort_option = sort_option
    selected_scene_layer_list = []
    
    ## create layer list from the target scene
    for layer in bpy.data.scenes[selected_scene.name].view_layers:
        selected_scene_layer_list.append(layer)
    # sort layers regarding name
    scene_layerName_list = []
    for layer in selected_scene_layer_list:
        scene_layerName_list.append(layer.name)
    if sort_option == 'Ascending':
        scene_layerName_list.sort()
    elif sort_option == 'Descending':
        scene_layerName_list.sort(reverse=True)
    # recrate the list
    selected_scene_layer_list = []
    for layer in scene_layerName_list:
        selected_scene_layer_list.append(selected_scene.view_layers[layer])
    return selected_scene_layer_list

def list_renderlayers_nodes(selected_scene,sort_option):
    ## variables
    selected_scene = selected_scene
    node_tree = selected_scene.node_tree

    renderLayer_nodes_list = []
    for node in node_tree.nodes:
        if node.type == "R_LAYERS" :
            check_name = node.name.replace("Render Layers - ","")
            if check_name not in bpy.context.scene.view_layers.keys(): # check if the layer is still in the scene 
                node.mute = True
            if node.mute == False:
                renderLayer_nodes_list.append(node)
    print(f"{renderLayer_nodes_list=}")
    # sort render layers regarding name
    renderLayer_nodes_names_list = []
    for node in renderLayer_nodes_list:
        renderLayer_nodes_names_list.append(node.name)
    if sort_option == 'Ascending':
        renderLayer_nodes_names_list.sort()
    elif sort_option == 'Descending':
        renderLayer_nodes_names_list.sort(reverse=True)
    #print(f"{renderLayer_nodes_names_list=}")
    # recrate the list
    renderLayer_nodes_list = []
    for node in renderLayer_nodes_names_list:
        renderLayer_nodes_list.append(node_tree.nodes[node])
    #print(f"{renderLayer_nodes_list}")
    return renderLayer_nodes_list

def create_renderlayers_nodes(selected_scene,selected_scene_layer_list):
    ## variables
    selected_scene = selected_scene
    selected_scene_layer_list = selected_scene_layer_list
    outputs_reset_selection = bpy.context.scene.vloutputs_props.outputs_reset_selection

    output_enabled_dict = {}
    
    bpy.data.scenes[selected_scene.name].use_nodes = True
    compo_tree = bpy.data.scenes[selected_scene.name].node_tree

    ## create render layers
    iter_node = 0
    for layer in selected_scene_layer_list:
        ## generate variables
        render_node_name = f"Render Layers - {layer.name}"
        #print(f"{render_node_name=}")
        node_color = (uniform(0,1), uniform(0,1), uniform(0,1))
        x_coord = 0

        ## create layer node if needed
        if render_node_name not in compo_tree.nodes:
            last_render_layer_node = compo_tree.nodes.new(type="CompositorNodeRLayers").name
            compo_tree.nodes[last_render_layer_node].scene = selected_scene # set the scene name 
            compo_tree.nodes[last_render_layer_node].layer = layer.name
            compo_tree.nodes[last_render_layer_node].name = render_node_name
        compo_tree.nodes[render_node_name].label = render_node_name        
        # manage color node
        if compo_tree.nodes[render_node_name].use_custom_color == False:
            compo_tree.nodes[render_node_name].use_custom_color = True
            compo_tree.nodes[render_node_name].color = node_color
        
        ## check number of outputs (= passes) for each layer node
        output_number = 0
        output_enabled_list = []
        for key, output in compo_tree.nodes[render_node_name].outputs.items():
            if getattr(output, 'enabled', False):
                output_enabled_list.append(key)
                output_number += 1    
        output_enabled_dict[render_node_name] = output_enabled_list

        ## move render nodes
        # set coordinates
        if iter_node == 0:
            y_coord = previous_node_size = 0
        else:
            y_coord = previous_node_size*-1
        
        # store the node size for better layout
        if output_number>3:
            offset_outputs = (output_number-3)*20
        else:
            offset_outputs = 0
        previous_node_size += 400 + offset_outputs
        
        # move render layers node
        compo_tree.nodes[render_node_name].location = (x_coord,y_coord)
        
        ## if not used for rendering => mute node
        if layer.use == False:
            compo_tree.nodes[render_node_name].mute = True
        else:
            compo_tree.nodes[render_node_name].mute = False
        
        iter_node += 1 

    #print(f"{output_enabled_dict}")
    return output_enabled_dict

# function to grab all informations given by the user regarding the name of the layers
def nodes_paths(layername,outputname,outputpath,del_signs):
    scene = bpy.context.scene
    vloutput_path = outputpath
    del_x_signs = bpy.context.scene.vloutputs_props.del_x_signs
    corresponding = bpy.context.scene.vloutputs_props.corresponding
    output_split = vloutput_path.split("**")
    #print(f"{output_split=}")
    vloutput_filepath = ""
    for elem in output_split:
        if elem == "[Base Path]":
            elem = ""
        elif elem == "[Pass Name]":
            elem = outputname
        elif elem == "[Layer Name]":
            elem = layername
        elif elem == "[File Name]":
            elem = bpy.data.filepath.split("\\")[-1].split(".")[0]
        elif elem == "[Scene Name]":
            elem = scene.name
        elif elem == "[Camera Name]":
            elem = scene.camera.name if scene.camera else ""
        elif elem == "[Custom A]":
            elem = scene.vloutputs_props.customfield_a
        elif elem == "[Custom B]":
            elem = scene.vloutputs_props.customfield_b
        elif elem == "[Custom C]":
            elem = scene.vloutputs_props.customfield_c
        elif elem == "[File Version]":
            if 'Snapshots_History' in bpy.data.texts.keys():
                snap_history = bpy.data.texts['Snapshots_History'].lines[0].body
                file_version = snap_history.replace("--", "").split(":")[-1].strip()
            else:
                file_version = "v001"
            elem = file_version
        # elif elem == "[Frame Number]":
        #     elem = str(scene.frame_current)

        # allow user to use bpy. blablabla
        if elem.startswith("bpy."):
            parts = elem.split(".")
            obj = bpy
            for part in parts[1:]:  # ignore "bpy"
                obj = getattr(obj, part)
            elem = obj
        
        vloutput_filepath += elem # create the complete path

        clean_filepath = vloutput_filepath.replace("\\\\", "\\").replace("\\//", "\\").replace("////", "//") # clean to avoid dirty things 
        # change names regarding the translation dic (Image=rgba, etc)
        outputs_corresponding_list = corresponding.split(',')
        outputs_corresponding_dict = {}
        for corres in outputs_corresponding_list:
            corres = corres.replace(" ","")
            corres_split = corres.split("=")
            outputs_corresponding_dict[corres_split[0]] = corres_split[-1]
            #print(f"{outputs_corresponding_dict=}")
        # check if user wants to change the string
        for string in outputs_corresponding_dict.keys():
            if string in clean_filepath :
                clean_filepath = clean_filepath.replace(string,outputs_corresponding_dict.get(string))
    if del_signs:
        complete_filepath = clean_filepath[del_x_signs:]
    else:
        complete_filepath = clean_filepath
    scene.vloutputs_props.pathlength = len(complete_filepath)
    return complete_filepath

def create_outputsNodes(selected_scene,selected_scene_layer_list,output_enabled_dict):
    ## variables
    selected_scene = selected_scene
    selected_scene_layer_list = selected_scene_layer_list
    output_enabled_dict = output_enabled_dict
    compo_tree = bpy.data.scenes[selected_scene.name].node_tree
    corresponding = bpy.context.scene.vloutputs_props.corresponding
    clear_unusedSockets = bpy.context.scene.vloutputs_props.clear_unusedSockets
    outputs_reset_selection = bpy.context.scene.vloutputs_props.outputs_reset_selection
    fileformat_checkbox = bpy.context.scene.vloutputs_props.fileformat_checkbox
    fileformat = bpy.context.scene.vloutputs_props.fileformat
    outputs_alpha_solo = bpy.context.scene.vloutputs_props.outputs_alpha_solo
    change_only_node_output = bpy.context.scene.vloutputs_props.change_only_node_output
    del_x_signs = bpy.context.scene.vloutputs_props.del_x_signs

    bpy.data.scenes[selected_scene.name].use_nodes = True

    # change names regarding the translation dic (Image=rgba, etc)
    outputs_corresponding_list = corresponding.split(',')
    outputs_corresponding_dict = {}
    for corres in outputs_corresponding_list:
        corres = corres.replace(" ","")
        corres_split = corres.split("=")
        outputs_corresponding_dict[corres_split[0]] = corres_split[-1]
        #print(f"{outputs_corresponding_dict=}")

    # remove main output namefile to keep only filepath : 
    main_file_output = get_base_path(selected_scene)
    # main_file_output = selected_scene.render.filepath
    # possible_separator = ["\\"]
    # for separator in possible_separator:
    #     if separator in main_file_output:
    #         main_file_output = main_file_output.split(separator)
    #         file_name = main_file_output[-1]
    #         main_file_output.remove(file_name)
    #         main_file_output = separator.join(main_file_output)
    #         main_file_output = f"{main_file_output}{separator}"

    # check output image type
    if fileformat_checkbox:
        file_format = fileformat
    else:
        file_format = selected_scene.render.image_settings.file_format

    ## create outputs nodes
    iter_node = 0
    for layer in selected_scene_layer_list: 
        # variables
        render_node_name = f"Render Layers - {layer.name}"
        output_node_name = f"File Output - {layer.name}"

        # update base_path
        layer_basepath = main_file_output + nodes_paths(layer.name,"",bpy.context.scene.vloutputs_props.basepath_previs,False)
        
        if bpy.context.scene.vloutputs_props.pathlength<=64:
            # create output nodes if needed
            if outputs_reset_selection!="ONLY UPDATE PATHS":
                # check if file output node exists
                if output_node_name not in compo_tree.nodes:
                    # create file output
                    last_output_node = compo_tree.nodes.new(type="CompositorNodeOutputFile").name
                    compo_tree.nodes[last_output_node].name = output_node_name
                    new_output = True
                else:
                    new_output = False
                compo_tree.nodes[output_node_name].label = output_node_name
                ## customise node regarding to render output
                # move for more readability
                if new_output:
                    compo_tree.nodes[output_node_name].location[0] = 400
                    compo_tree.nodes[output_node_name].width = (900)
                compo_tree.nodes[output_node_name].location[1] = compo_tree.nodes[render_node_name].location[1] # always align output to render layer
                compo_tree.nodes[output_node_name].use_custom_color = True
                compo_tree.nodes[output_node_name].color = compo_tree.nodes[render_node_name].color # give the same color as render layer node
                compo_tree.nodes[output_node_name].mute = compo_tree.nodes[render_node_name].mute # check if mute
                compo_tree.nodes[output_node_name].format.file_format = file_format
                if fileformat_checkbox:
                    if outputs_alpha_solo:
                        compo_tree.nodes[output_node_name].format.color_mode = 'RGB'
                    else:
                        compo_tree.nodes[output_node_name].format.color_mode = 'RGBA'
                else:
                    compo_tree.nodes[output_node_name].format.color_mode = selected_scene.render.image_settings.color_mode
                compo_tree.nodes[output_node_name].format.color_depth = selected_scene.render.image_settings.color_depth
                compo_tree.nodes[output_node_name].format.compression = selected_scene.render.image_settings.compression
            else:
                new_output = False

            #print(f"{new_output=}")

            # update output node path (different from output names !)
            compo_tree.nodes[output_node_name].base_path = f"{layer_basepath}"

            output_enabled_list = output_enabled_dict[render_node_name]
            f"{output_enabled_list=}"
            ## create inputs in file outputs node regarding view layer
            if new_output or outputs_reset_selection == "ONLY UPDATE LINKS":
                compo_tree.nodes[output_node_name].inputs.clear()
                for output in output_enabled_list:
                    output_slot = output
                    # # check if user wants to change the name
                    # if output in outputs_corresponding_dict.keys():
                    #     output = outputs_corresponding_dict[output]
                    # create the outputs paths regarding user fields
                    vloutput_path = nodes_paths(layer.name,output,bpy.context.scene.vloutputs_props.subpath_previs,True)
                    #print(f"{vloutput_path=}")

                    # check if user wants to change the string
                    # for string in outputs_corresponding_dict.keys():
                    #     if string in vloutput_path :
                    #         vloutput_path = vloutput_path.replace(string,outputs_corresponding_dict.get(string))
                    #vloutput_path = vloutput_path[del_x_signs:]
                    input_slot = vloutput_path
                    #print(f"{input_slot=}")
                    #print(f"{output_slot=}")
                    compo_tree.nodes[output_node_name].layer_slots.new(input_slot) # "." is for better readability in files
                    if bpy.context.scene.vloutputs_props.pathlength<=64:
                        if bpy.context.scene.vloutputs_props.outputs_alpha_solo == True or bpy.context.scene.vloutputs_props.outputs_alpha_solo == False and output != "Alpha":
                            compo_tree.links.new(compo_tree.nodes[render_node_name].outputs[output_slot],compo_tree.nodes[output_node_name].inputs[input_slot])
            
            # update outputs slots names
            if outputs_reset_selection=="ONLY UPDATE PATHS":
                iter = 0
                for input_slot in output_enabled_list:
                    # check if user wants to change the name
                    # if input_slot in outputs_corresponding_dict.keys():
                    #     input_slot = outputs_corresponding_dict[input_slot]
                    # create the outputs paths regarding user fields
                    vloutput_path = nodes_paths(layer.name,input_slot,bpy.context.scene.vloutputs_props.subpath_previs,True)
                    # check if user wants to change the string
                    # for string in outputs_corresponding_dict.keys():
                    #     if string in vloutput_path :
                    #         vloutput_path = vloutput_path.replace(string,outputs_corresponding_dict.get(string))
                    #vloutput_path = vloutput_path[del_x_signs:]
                    # change the name
                    if bpy.context.scene.vloutputs_props.outputs_alpha_solo == False and input_slot != "Alpha":
                        compo_tree.nodes[output_node_name].file_slots[iter].path = vloutput_path
                        iter += 1
                    elif input_slot == "Alpha":
                        iter += 1

            # update base path (from scene output)
            base_path = compo_tree.nodes[output_node_name].base_path
            #print(f"{base_path=}")
            if change_only_node_output == False:
                for string in outputs_corresponding_dict.keys():
                    if string in base_path :
                        compo_tree.nodes[output_node_name].base_path = base_path.replace(string,outputs_corresponding_dict.get(string))


            # clean unused output
            if clear_unusedSockets:
                for input in compo_tree.nodes[output_node_name].inputs:
                    if len(input.links) == 0:
                        compo_tree.nodes[output_node_name].inputs.remove(input)
            
                #{outputs_prefix}


### create operators ###        
class VLOUTPUT_OT_createnodesoutput(bpy.types.Operator):
    bl_idname = "vloutputs.createnodesoutput"
    bl_label = Addon_Name + "create files output"
    bl_description = "create files output node in compositing module for each view layer"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        print(f"\n {separator} Begin {Addon_Name} {separator} \n")

        sort_option = bpy.context.scene.vloutputs_props.outputs_sort

        # make it for all scenes or only current
        work_scene = bpy.context.scene

        # create scene list to process
        scenes_list = []
        if bpy.context.scene.vloutputs_props.outputs_scenes_selection == "ALL SCENES":
            for scene in bpy.data.scenes:
                scenes_list.append(scene)
        elif bpy.context.scene.vloutputs_props.outputs_scenes_selection == "ALL SCENES WITH CURRENT SETTINGS":
            for scene in bpy.data.scenes:
                scene.vloutputs_props.outputs_scenes_selection = work_scene.vloutputs_props.outputs_scenes_selection
                scene.vloutputs_props.outputs_alpha_solo = work_scene.vloutputs_props.outputs_alpha_solo
                scene.vloutputs_props.outputs_reset_selection = work_scene.vloutputs_props.outputs_reset_selection
                #scene.vloutputs_props.outputs_clean_nodeslinks = work_scene.vloutputs_props.outputs_clean_nodeslinks
                scenes_list.append(scene)
        elif bpy.context.scene.vloutputs_props.outputs_scenes_selection == "CURRENT SCENE":
            scenes_list.append(work_scene)
        
        #print(f"{scenes_list=}")
        # process
        for scene in scenes_list:
            scene.use_nodes = True
            if precomp_scene_suffixe not in bpy.context.scene.name:
                if scene.vloutputs_props.outputs_reset_selection == "RESET ALL TREE":
                    scene.node_tree.nodes.clear()
                # list all render layers
                selected_scene_layer_list = list_renderlayers(work_scene,sort_option)
                # create render layers
                output_enabled_dict = create_renderlayers_nodes(work_scene,selected_scene_layer_list)
                # create output nodes
                create_outputsNodes(work_scene,selected_scene_layer_list,output_enabled_dict)
                bpy.context.window.scene = work_scene # switch back to user scene work
                #print(" --- scene finished --- ")

            # use a user script if wanted
            if bpy.context.scene.vloutputs_props.postscript_checkbox:
                exec(bpy.context.scene.vloutputs_props.postscript.as_string())

        print(f"\n {separator} {Addon_Name} Finished {separator} \n")
        return {"FINISHED"}

class VLOUTPUT_OT_dellastcharacter(bpy.types.Operator):
    bl_idname = 'vloutputs.dellastcharacter'
    bl_label = "Delete Last Character"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        # subpath_previs = context.scene.vloutputs_props.subpath_previs
        # if subpath_previs != "":
        #     output_split = subpath_previs.split("**")
        #     context.scene.vloutputs_props.subpath_previs = "**".join(output_split[:-1])



        vloutputs_props = context.scene.vloutputs_props
        
        if vloutputs_props.path_to_change == "Base Path":
            if vloutputs_props.basepath_previs != "":
                output_split = vloutputs_props.basepath_previs.split("**")
                vloutputs_props.basepath_previs = "**".join(output_split[:-1])

        elif vloutputs_props.path_to_change == "Subpath": 
            if vloutputs_props.subpath_previs != "":
                output_split = vloutputs_props.subpath_previs.split("**")
                vloutputs_props.subpath_previs = "**".join(output_split[:-1])

        return {"FINISHED"}

# Generic operator for adding characters
class VLOUTPUT_OT_add_character_enum(bpy.types.Operator):
    bl_idname = 'vloutputs.add_character_enum'
    bl_label = "Add Character"
    #bl_description = "Adds a character or field to the path"
    bl_options = {"REGISTER", "UNDO"}

    character: bpy.props.StringProperty()
    tooltip: bpy.props.StringProperty()

    ### add a class to add tooltip
    @classmethod
    def description(cls, context, properties):
        return properties.tooltip

    def execute(self, context):
        if context.scene.vloutputs_props.path_to_change == "Base Path": 
            context.scene.vloutputs_props.basepath_previs += f"**{self.character}"
        elif context.scene.vloutputs_props.path_to_change == "Subpath": 
            context.scene.vloutputs_props.subpath_previs += f"**{self.character}"
      
        return {"FINISHED"}

class VLOUTPUT_OT_createprecomp(bpy.types.Operator):
    bl_idname = "vloutputs.createprecomp"
    bl_label = Addon_Name + "Create Pre-Comp Tree scene"
    bl_description = "create a pre compositing scene from render layer in scenes. \n /!\ You need to have render once at least one frame per layer to make it works ! /!\ "
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        print(f"\n {separator} Begin {Addon_Name} {separator} \n")
        
        work_scene = bpy.context.scene
        sort_option = work_scene.vloutputs_props.outputs_sort
        precomp_bg_under = work_scene.vloutputs_props.precomp_bg_under
        precomp_bg_img = work_scene.vloutputs_props.precomp_bg_img
        precomp_freestyle = work_scene.vloutputs_props.precomp_freestyle
        
        # create scene list to process
        scenes_list = []
        if bpy.context.scene.vloutputs_props.outputs_scenes_selection == "ALL SCENES":
            for scene in bpy.data.scenes:
                scenes_list.append(scene)
        elif bpy.context.scene.vloutputs_props.outputs_scenes_selection == "ALL SCENES WITH CURRENT SETTINGS":
            for scene in bpy.data.scenes:
                scene.vloutputs_props.outputs_scenes_selection = work_scene.vloutputs_props.outputs_scenes_selection
                scene.vloutputs_props.outputs_reset_selection = work_scene.vloutputs_props.outputs_reset_selection
                scenes_list.append(scene)
        elif bpy.context.scene.vloutputs_props.outputs_scenes_selection == "CURRENT SCENE":
            scenes_list.append(work_scene)

        #print(f"{scenes_list=}")
        # process
        for scene in scenes_list:
            scene_name = scene.name
            bpy.data.scenes[scene_name].use_nodes = True
            node_tree = bpy.data.scenes[scene_name].node_tree
            # if len(node_tree.nodes)==2 : # in case of it's a new node tree, renderlayer + composite node are in
            #     node_tree.nodes.clear()
            # if bpy.context.scene.vloutputs_props.outputs_reset_selection == "RESET ALL TREE":
            #     node_tree.nodes.clear()
            # list all render layers
            selected_scene_layer_list = list_renderlayers(work_scene,sort_option)
            # create render layers
            output_enabled_dict = create_renderlayers_nodes(work_scene,selected_scene_layer_list)
            # create output nodes
            
            ## create clean list (by alphabatical order) of render layer nodes
            renderLayer_nodes_list = list_renderlayers_nodes(scene,sort_option)
            #print(f"{renderLayer_nodes_list=}")

            ### create alpha over node tree
            name_suffix = "_automatic"
            ## clean old alpha over nodes
            for node in node_tree.nodes:
                if node.name.endswith(name_suffix):
                    node_tree.nodes.remove(node_tree.nodes[node.name])
            iter = 0
            location_x = 2000
            location_x_add = 300
            node_alphaOver_list = []
            #print(f"{work_scene.vloutputs_props.precomp_input_prop=}")
            for node in renderLayer_nodes_list:
                if precomp_freestyle and scene.render.use_freestyle and bpy.context.scene.view_layers[-1].freestyle_settings.as_render_pass: # be sure freestyle will be created
                    # add line on top of color with an alpha over
                    node_alphaOverFS_name = node_tree.nodes.new(type="CompositorNodeAlphaOver").name
                    node_alphaOverFS = node_tree.nodes[node_alphaOverFS_name]
                    node_alphaOverFS.name = f"Alpha_Line{iter}"
                    node_alphaOverFS.location[0] = 1200
                    node_alphaOverFS.location[1] = node.location[1]
                    node_tree.links.new(node.outputs["Image"],node_tree.nodes[node_alphaOverFS.name].inputs[1])
                    node_tree.links.new(node.outputs["Freestyle"],node_tree.nodes[node_alphaOverFS.name].inputs[2])
                    node = node_alphaOverFS
                if iter != 1: # check if alpha over is needed
                    node_alphaOver = node_tree.nodes.new(type="CompositorNodeAlphaOver").name
                    node_alphaOver_name = f"Alpha Over.{str(iter).zfill(3)}{name_suffix}"
                    node_tree.nodes[node_alphaOver].name = node_alphaOver_name
                    #print(node_alphaOver_name)
                    node_tree.nodes[node_alphaOver_name].location[0] = location_x
                    node_alphaOver_list.append(node_alphaOver_name)
                    location_x += location_x_add
                if iter == 0:
                    if precomp_bg_under and precomp_bg_img!= None:
                        # create bg_node 
                        bg_node_name = "BG_under"
                        if bg_node_name not in node_tree.nodes:
                            last_render_layer_node = node_tree.nodes.new(type="CompositorNodeImage").name
                            bg_node = node_tree.nodes[last_render_layer_node]
                            bg_node.image = bpy.data.images[precomp_freestyle]
                            bg_node.name = bg_node_name
                            bg_node.location[0] = 0
                            bg_node.location[1] = 500
                            # add alpha for the BG with alpha over
                        bg_node = node_tree.nodes[bg_node_name]
                        node_alphaOverBG_name = "Alpha_BG"
                        if node_alphaOverBG_name not in node_tree.nodes:
                            node_alphaOverBG_tmpname = node_tree.nodes.new(type="CompositorNodeAlphaOver").name
                            node_alphaOverBG = node_tree.nodes[node_alphaOverBG_tmpname]
                            node_alphaOverBG.name = node_alphaOverBG_name
                            node_alphaOverBG.location[0] = 400*2
                            node_alphaOverBG.location[1] = bg_node.location[1]
                        node_alphaOverBG = node_tree.nodes[node_alphaOverBG_name]
                        node_tree.links.new(node_tree.nodes[bg_node.name].outputs["Image"],node_alphaOverBG.inputs[1])
                        node_tree.links.new(node_tree.nodes[node.name].outputs["Image"],node_alphaOverBG.inputs[2])
                        node_tree.links.new(node_tree.nodes[node_alphaOverBG.name].outputs["Image"],node_tree.nodes[node_alphaOver_name].inputs[1])
                    else:
                        node_tree.links.new(node_tree.nodes[node.name].outputs["Image"],node_tree.nodes[node_alphaOver_name].inputs[1])
                        if len(renderLayer_nodes_list)==1:
                            node_tree.nodes[node_alphaOver_name].mute = True
                else:
                    node_tree.links.new(node_tree.nodes[node.name].outputs["Image"],node_tree.nodes[node_alphaOver_name].inputs[2])
                    if iter != 1:
                        node_tree.links.new(node_tree.nodes[node_alphaOver_list[iter-2]].outputs["Image"],node_tree.nodes[node_alphaOver_name].inputs[1])                    
                iter+=1
            #print(f"alpha nodes created : {node_alphaOver_list}")
            
            # create final composite node
            if "Composite" in node_tree.nodes.keys():
                    node_tree.nodes.remove(node_tree.nodes["Composite"])
            if "Viewer" in node_tree.nodes.keys():
                node_tree.nodes.remove(node_tree.nodes["Viewer"])
            
            if len(renderLayer_nodes_list)>0: # check lengh of list to avoid errors
                node_composite = node_tree.nodes.new(type="CompositorNodeComposite").name
                node_composite_named = f"{node_composite}{name_suffix}"
                node_tree.nodes[node_composite].name = node_composite_named
                node_tree.nodes[node_composite_named].location = (location_x, 100)
                node_tree.links.new(node_tree.nodes[node_alphaOver_list[-1]].outputs["Image"],node_tree.nodes[node_composite_named].inputs[0])                    
                # create viewer node
                
                node_viewer = node_tree.nodes.new(type="CompositorNodeViewer").name
                node_viewer_named = f"{node_viewer}{name_suffix}"
                node_tree.nodes[node_viewer].name = node_viewer_named
                node_tree.nodes[node_viewer_named].location = (location_x, -100)
                node_tree.links.new(node_tree.nodes[node_alphaOver_list[-1]].outputs["Image"],node_tree.nodes[node_viewer_named].inputs[0])                    

        # clean useless nodes
        for node in node_tree.nodes:
            input_used = 0
            if node.type == "ALPHAOVER" or node.type == "COMPOSITE" or node.type == "VIEWER":
                for node_input in  node.inputs:
                    if node_input.is_linked == True:
                        input_used += 1
                if input_used == 0:
                    node_tree.nodes.remove(node)
        
        # use a user script if wanted
        if bpy.context.scene.vloutputs_props.precomp_postscript_checkbox:
            exec(bpy.context.scene.vloutputs_props.precomp_postscript.as_string())

        #print(iter_node)
        bpy.context.window.scene = work_scene
        
        #print(f"{Addon_Name} done on : {nodes_created_list} \n")
        print(f"\n {separator} {Addon_Name} Finished {separator} \n")
        return {"FINISHED"}

# list all classes
classes = (
    VLOUTPUT_Preferences,
    VLOUTPUT_properties,
    VLOUTPUT_PT_filesoutput,
    VLOUTPUT_PT_filesoutputfieldsoptions,
    VLOUTPUT_PT_filesoutputoptions,
    VLOUTPUT_PT_precomptree,
    VLOUTPUT_OT_createnodesoutput,
    VLOUTPUT_OT_dellastcharacter,
    VLOUTPUT_OT_add_character_enum,
    VLOUTPUT_OT_createprecomp,
    )

# register classes
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vloutputs_props = bpy.props.PointerProperty (type = VLOUTPUT_properties)

#unregister classes 
def unregister():    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.vloutputs_props
        