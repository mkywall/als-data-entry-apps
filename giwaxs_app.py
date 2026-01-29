from ScopeFoundry import BaseMicroscopeApp

# giwaxs bar
#from ScopeFoundryHW.giwaxs_bar_creator.giwaxs_bar_hardware import GiwaxsBarHW
from ScopeFoundryHW.giwaxs_bar_creator.giwaxs_bar_controlpanel import GiwaxsBarControlPanel

# cruxxxxx
from ScopeFoundryHW.mf_crucible.mf_crucible_hardware import MFCrucibleHW
from ScopeFoundryHW.mf_crucible.mf_crucible_controlpanel import MFCrucibleControlPanel

class GiwaxsApp(BaseMicroscopeApp):
    """
    App to create bars of samples for Giwaxs at the ALS
    """

    name = 'giwaxs_app'

    def setup(self):
        """Setup hardware components and measurements."""

        # ========== Hardware Components ==========
        #giwaxs_bar_creator = self.add_hardware(GiwaxsBarHW)
        crucible = self.add_hardware(MFCrucibleHW)

        # ========== Measurements ==========
        self.add_measurement(GiwaxsBarControlPanel(self))
        self.add_measurement(MFCrucibleControlPanel(self))

if __name__ == '__main__':
    import sys
    app = GiwaxsApp(sys.argv)
    app.exec_()
