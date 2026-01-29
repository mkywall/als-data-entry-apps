from ScopeFoundry import HardwareComponent
import os
from dotenv import load_dotenv
from pycrucible import CrucibleClient

load_dotenv()
client = CrucibleClient(
    api_url="https://crucible.lbl.gov/testapi",
    api_key = os.environ.get("crucible_apikey")
)

class GiwaxsBarHW(HardwareComponent):
    
    name = 'giwaxs_bar_creator'
  
   # default_trayname = 'TRAYXXXXX'
   # default_trayuuid = "Scan/Enter Tray UUID"

    #def setup(self):
        
       # self.settings.New(f'tray_name', initial = self.default_trayname, dtype = str)
       # self.settings.New(f"tray_uuid", initial = self.default_trayuuid, dtype = str)
       
        #self.settings.tray_uuid.add_listener(self.on_enter_tray_uuid, argtype = str)

    def update_lq(self, newval, lq_name):
        # update name
        lq = self.settings.get_lq(lq_name)
        lq.update_value(newval)

    def on_enter_tray_uuid(self, tray_num):
        tray_uuid = self.settings[f'tray_uuid']
        print(tray_uuid)
        if len(tray_uuid) != 26:
            return tray_uuid
        tray_info = client.get_sample(sample_id = tray_uuid)
        tray_name = tray_info['sample_name']
        self.update_lq(tray_name, f'tray_name')
        samples_on_tray = client.list_samples(parent_id = tray_uuid)
        sorted_samples = sorted(samples_on_tray, key=lambda item: item['sample_name'])

        for ii,sample in enumerate(sorted_samples):
            tray_pos = ii + 1
            sample_name = sample['sample_name']
            sample_uuid = sample['unique_id']
            self.update_lq(sample_name, f'tray{tray_num}_sample{tray_pos}_name')
            self.update_lq(sample_uuid, f'tray{tray_num}_sample{tray_pos}_uuid')
    
            