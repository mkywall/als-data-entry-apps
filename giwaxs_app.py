from ScopeFoundry import BaseMicroscopeApp

# Individual control panels
from ScopeFoundryHW.giwaxs_bar_creator.giwaxs_bar_controlpanel import GiwaxsBarCreatorControlPanel
from ScopeFoundryHW.giwaxs_bar_creator.rga_carrier_controlpanel import RgaCarrierControlPanel

# cruxxxxx
#from ScopeFoundryHW.mf_crucible.mf_crucible_hardware import MFCrucibleHW
#from ScopeFoundryHW.mf_crucible.mf_crucible_controlpanel import MFCrucibleControlPanel

class GiwaxsApp(BaseMicroscopeApp):
    """
    App to create bars of samples for GIWAXS and RGA carriers at the ALS
    """

    name = 'giwaxs_app'

    def setup(self):
        """Setup hardware components and measurements."""

        # ========== Hardware Components ==========
        #giwaxs_bar_creator = self.add_hardware(GiwaxsBarHW)
        #crucible = self.add_hardware(MFCrucibleHW)

        # ========== Measurements ==========
        self.add_measurement(GiwaxsBarCreatorControlPanel(self))
        self.add_measurement(RgaCarrierControlPanel(self))
        #self.add_measurement(MFCrucibleControlPanel(self))

if __name__ == '__main__':
    import sys
    app = GiwaxsApp(sys.argv)
    app.exec_()
