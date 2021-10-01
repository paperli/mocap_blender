bl_info = {
    "name": "MoCap",
    "description": "Real-time animation from MoCap app",
    "author": "Ken-Jung Lee",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "3D View > Tools",
    "category": "Animation"
}

import socket
import select
import json
import threading
import traceback
import re
import bpy
from bpy.props import (StringProperty,
                        BoolProperty,
                        IntProperty,
                        FloatProperty,
                        FloatVectorProperty,
                        EnumProperty,
                        PointerProperty)
from bpy.types import (Panel,
                        Menu,
                        Operator,
                        PropertyGroup)

running = False

SKELETON = [
    "hips_joint", "right_upLeg_joint", "right_leg_joint", "right_foot_joint", "right_toes_joint", "right_toesEnd_joint",
    "left_upLeg_joint", "left_leg_joint", "left_foot_joint", "left_toes_joint", "left_toesEnd_joint",
    "spine_1_joint", "spine_2_joint", "spine_3_joint", "spine_4_joint", "spine_5_joint", "spine_6_joint", "spine_7_joint",
    "right_shoulder_1_joint", "right_arm_joint", "right_forearm_joint", "right_hand_joint",
    "left_shoulder_1_joint", "left_arm_joint", "left_forearm_joint", "left_hand_joint",
    "neck_1_joint", "neck_2_joint", "neck_3_joint", "neck_4_joint", "head_joint"
]

SKELETON_PROPERTY_NAME = [
    "hips", "rightUpLeg", "rightLeg", "rightFoot", "rightToes", "rightToesEnd",
    "leftUpLeg", "leftLeg", "leftFoot", "leftToes", "leftToesEnd",
    "spine1", "spine2", "spine3", "spine4", "spine5", "spine6", "spine7",
    "rightShoulder1", "rightArm", "rightForearm", "rightHand",
    "leftShoulder1", "leftArm", "leftForearm", "leftHand",
    "neck1", "neck2", "neck3", "neck4", "head"
]

def getBonePropertyName(boneName):
    return re.sub(r'_([a-z0-9])', lambda x: x.group(1).upper(), boneName).replace("Joint", "")

HOSTNAME = socket.gethostname()
IP = socket.gethostbyname(HOSTNAME)

class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True

    def resumeServer(self):
        self.running = True
        self.server.running = True
    
    def stopServer(self):
        self.running = False
        self.server.running = False

    def run(self):
        try:
            self.server = Server()
            while self.running:
                self.server.receive()
        except:
            pass


class Server:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(False)
        ip = IP
        print(ip)
        self.socket.bind((ip, 9845))
        self.socket.listen(2)
        self.running = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.socket.close()

    def receive(self):
        pairs = []
        timeout = 1
        while self.running:
            sockets = list(map(lambda x: x[0], pairs))
            if len(pairs) > 0:
                read_sockets, write_sockets, error_sockets = select.select(sockets, [], [], timeout)
                for sock in read_sockets:
                  data = sock.recv(4096)
                  if not data :
                    print('Client disconnected')
                    pairs = []
                  else :
                    self.connectionReceivedData(connection, data.decode())
                    del data
            try:
                try:
                    connection,address = self.socket.accept()
                    print("new connection: ", connection)
                    pairs.append((connection, address))
                except:
                    pass

            except:
                pass

        for pair in pairs:
            (connection, address) = pair
            connection.close()

    def connectionReceivedData(self, connection, data):
        motions = re.findall(r'{\"[^(y\")&^(x\")&^(x\")].*?\}\}', data)
        if len(motions) < 1:
            return None
        try:
            motionData = json.loads(motions[0])
        except json.decoder.JSONDecodeError:
            print("Invalid JSON: ", data)
            return None
        receivedMotionData(motionData)
    
    def connectionReceivedDataBackup(self, connection, data):
        motions = re.findall(r'{\"[^(y\")&^(x\")&^(x\")].*?\}\}', data)
        print("motions count: ", len(motions))
        for m in motions:
            try:
                motionData = json.loads(m)
            except json.decoder.JSONDecodeError:
                print("Invalid JSON: ", data)
                pass
            receivedMotionData(motionData)

# This is a global so when we run the script again, we can keep the server alive
# but change how it works

class MyProperties(PropertyGroup):

    running: BoolProperty(
        name = "server_running",
        description = "Is server running?",
        default = False
    )

    skeleton: StringProperty(
        name = "Armature",
        description = "Select an armature",
        default = "",
        maxlen = 1024
    )

def updatePhoneRotation(rotation):
    phone = bpy.context.scene.objects["iPhone"]
    phone.rotation_quaternion.x = float(rotation['x'])
    phone.rotation_quaternion.y = 0 - float(rotation['z'])
    phone.rotation_quaternion.z = float(rotation['y'])
    phone.rotation_quaternion.w = float(rotation['w'])

def updateSkeletonPose(motionData):
    for bone in SKELETON:
        #propertyName = getBonePropertyName(bone)
        r = motionData[bone]
        updateBoneRotation(r, bone)

def updateBoneRotation(rotation, boneName):
    scene = bpy.context.scene
    armature = scene.objects[scene.skeleton]
    bone = armature.pose.bones.get(boneName)
    if bone is not None:
        #bone.rotation_mode = "ZXY"
        #bone.rotation_euler = (float(rotation['x']), float(rotation['y']), float(rotation['z']))
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (float(rotation['w']), float(rotation['x']), float(rotation['y']), float(rotation['z']))

def receivedMotionData(motionData):
    #updatePhoneRotation(motionData)
    #updateBoneRotation(motionData)
    updateSkeletonPose(motionData)
    pass

def startOrStopServer(running = False):
    if running:
        serverThread.stopServer()
        print("Server is running. Stop it.")
    else:
        print("Start server")
        serverThread.start()

def startServer():
    try:
        if serverThread.running == False:
            serverThread = ServerThread()
            serverThread.start()
            print("Starting server")
        else:
            print("Server already running, using new motion handler.")
    except:
        serverThread = ServerThread()
        serverThread.start()
        print("Starting server")

# = Operators =
class WM_OT_StartServer(Operator):
    bl_label = "Start or Stop Server"
    bl_idname = "mocap.start_server"

    def execute(self, context):
        global serverThread
        global running
        if running:
            running = False
            try:
                serverThread.stopServer()
            except:
                print("Nothing to stop")
        else:
            running = True
            serverThread = ServerThread()
            serverThread.start()

        return {'FINISHED'}

# = Panel in Object Mode =
class OBJECT_PT_CustomPanel(Panel):
    bl_label = "MoCap Server"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MoCap"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return context.object is not None
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        global running
        btn_title = "Stop Server" if running else "Start Server"
        btn_icon = "SNAP_FACE" if running else "PLAY"
        layout.label(text=IP, icon="MOD_WAVE")
        layout.operator("mocap.start_server", text=btn_title, icon=btn_icon)
        layout.prop_search(scene, "skeleton", bpy.data, "armatures", text="Skeleton")
        layout.separator()

# = Registration =

classes = (
    MyProperties,
    WM_OT_StartServer,
    OBJECT_PT_CustomPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)
    bpy.types.Scene.skeleton = StringProperty()

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.my_tool
    del bpy.types.Scene.skeleton

# = Test =
if __name__ == "__main__":
    register()