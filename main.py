from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, loadPrcFileData
from direct.actor.Actor import Actor
import simplepbr

# Config
loadPrcFileData("", "framebuffer-alpha true")
loadPrcFileData("", "win-size 400 600")
loadPrcFileData("", "background-color 0 0 0 0")

class DesktopPet(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Transparent, always on top
        wp = WindowProperties()
        wp.setUndecorated(True)
        wp.setZOrder(WindowProperties.ZTop)
        self.win.requestProperties(wp)

        # Enable PBR so GLTF materials show
        simplepbr.init()

        # Load GLTF Mixamo model as an Actor (with animation support)
        self.pet = Actor("models/girl001.glb")

        self.pet.reparentTo(self.render)
        self.pet.setScale(1.5)
        self.pet.setPos(0, 5, -2)

        # Play the available animation
        # GLTF animations will be named "anim_0", "anim_1", ...
        anims = self.pet.getAnimNames()
        # self.pet = Actor(
        #     "models/sophia_base.glb", 
        #     {"idle": "models/sophia_idle.glb",
        #     "wave": "models/sophia_wave.glb"}
        # )
        # self.pet.loop("'Armature|Take 001|BaseLayer.002'")
        print("Animations found:", anims)

        if "anim_0" in anims:
            self.pet.loop("anim_0")
        else:
            print("⚠️ No animation found in this GLTF")

        # Camera setup
        # self.disableMouse()
        self.camera.setPos(0, -10, 3)
        self.camera.lookAt(0, 0, 0)

app = DesktopPet()
app.run()