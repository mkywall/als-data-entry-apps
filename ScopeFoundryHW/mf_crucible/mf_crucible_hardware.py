from ScopeFoundry import HardwareComponent
import os
from dotenv import load_dotenv
from pycrucible import CrucibleClient

load_dotenv()
client = CrucibleClient(
    api_url="https://crucible.lbl.gov/testapi",
    api_key = os.environ.get("crucible_apikey")
)

class MFCrucibleHW(HardwareComponent):
    
    name = 'mf_crucible_nirvana'
    default_session_name = 'session name'
    default_email = 'user-email@lbl.gov'
    default_user_name = ''
    default_comments= 'comments'
    default_tags="tags,separated,by,commas"
    default_run_id = ''
    default_orcid = 'XXXX-XXXX-XXXX-XXXX'   
    default_trayname = 'TRAYXXXXX'
    default_trayuuid = "Scan/Enter Tray UUID"

    def setup(self):
        self.settings.New("email", initial = self.default_email, dtype = str)
        self.settings.New("user_name", initial = self.default_user_name, dtype = str)
        self.settings.New("orcid", initial = self.default_orcid, dtype = str)
        self.settings.New("project", initial = "", choices = ([]), dtype = str)
        self.settings.New("session_name", initial = self.default_session_name, dtype = str)

        self.settings.New("comments", initial = self.default_comments, dtype = str)
        self.settings.New("tags", initial = self.default_tags, dtype = str)
        #self.settings.New("uvvis_run_id", initial = self.default_run_id, dtype = str)

        for ii in [1,2]:
            self.settings.New(f'tray{ii}_name', initial = self.default_trayname, dtype = str)
            self.settings.New(f"tray{ii}_uuid", initial = self.default_trayuuid, dtype = str)
            for jj in range(8):
                self.settings.New(f"tray{ii}_sample{jj+1}_name", initial = "", dtype = str)
                self.settings.New(f"tray{ii}_sample{jj+1}_uuid", initial = "", dtype = str)

        self.settings.email.add_listener(self.on_enter_email, argtype = str)             
        self.settings.tray1_uuid.add_listener(self.on_enter_tray1_uuid, argtype = str)
        self.settings.tray2_uuid.add_listener(self.on_enter_tray2_uuid, argtype = str)


    def connect(self):
        print("connected")

    def disconnect(self):
        print("disconnected")

    def update_projects(self, project_list):
        print(project_list)
        prop_lq = self.settings.get_lq('project')
        prop_lq.change_choice_list(project_list)
        prop_lq.update_value(project_list[0])

    
    def update_lq(self, newval, lq_name):
        # update name
        lq = self.settings.get_lq(lq_name)
        lq.update_value(newval)

    def on_enter_tray1_uuid(self):
        self.on_enter_tray_uuid(tray_num = 1)

    def on_enter_tray2_uuid(self):
        self.on_enter_tray_uuid(tray_num = 2)

    def on_enter_tray_uuid(self, tray_num):
        tray_uuid = self.settings[f'tray{tray_num}_uuid']
        print(tray_uuid)
        if len(tray_uuid) != 26:
            return tray_uuid
        tray_info = client.get_sample(sample_id = tray_uuid)
        tray_name = tray_info['sample_name']
        self.update_lq(tray_name, f'tray{tray_num}_name')
        samples_on_tray = client.list_samples(parent_id = tray_uuid)
        sorted_samples = sorted(samples_on_tray, key=lambda item: item['sample_name'])

        for ii,sample in enumerate(sorted_samples):
            tray_pos = ii + 1
            sample_name = sample['sample_name']
            sample_uuid = sample['unique_id']
            self.update_lq(sample_name, f'tray{tray_num}_sample{tray_pos}_name')
            self.update_lq(sample_uuid, f'tray{tray_num}_sample{tray_pos}_uuid')
        

    def on_enter_email(self):
        import os 
        from dotenv import load_dotenv
        from pycrucible import CrucibleClient
        load_dotenv()
        crucible_url = 'https://crucible.lbl.gov/testapi'
        crucible_apikey = os.environ.get('crucible_apikey')

        client = CrucibleClient(crucible_url, crucible_apikey)
        provided_email = self.settings.email.value.strip()
        user_info = client.get_user(email = provided_email)

        # update user info
        user_name = f'{user_info['first_name']}_{user_info['last_name']}'
        self.update_lq(user_name, 'user_name')
        self.update_lq(user_info['orcid'], 'orcid')

        # update project list
        projects = client.list_projects(user_info['orcid'])
        project_ids = [x['project_id'] for x in projects]
        project_ids.sort()
        self.update_projects(project_ids)
    
            