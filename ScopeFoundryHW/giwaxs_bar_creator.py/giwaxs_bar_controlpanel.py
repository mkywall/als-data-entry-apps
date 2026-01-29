from ScopeFoundry.measurement import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from mfid import mfid
import os

# ============ CRUCIBLE
from dotenv import load_dotenv
from pycrucible import CrucibleClient
from pycrucible.utils import get_tz_isoformat
load_dotenv()
cruc_client = CrucibleClient(
    api_url="https://crucible.lbl.gov/testapi",
    api_key = os.environ.get("crucible_apikey")
)

# ================ ALS BEAMLINE SCICAT
from beamline_data_toolkit.sample_tracker import SampleTrackerClient

# TODO: REMOVE LATER
test_qr_code = "HTTPS://DATAPORTAL-STAGING.ALS.LBL.GOV/SAMPLE-TRACKING/SET/B84387D1-5EE9-4FC9-AD2D-49D64A2422EF"

# Create a client object.
als_sc_client = SampleTrackerClient(
    scicat_base_url="https://dataportal-staging.als.lbl.gov/api/v3/",
    scicat_username="admin",
    scicat_password=os.environ.get('als_scicat_password')
)


def get_next_serial_sample(sample_prefix, project):
    project_samples = cruc_client.list_samples(project_id = project)
    filtered_samples = [x['sample_name'] for x in project_samples if x['sample_name'].startswith(sample_prefix)]
    sample_nums = [int(x.replace(sample_prefix, '')) for x in filtered_samples]
    sample_nums.sort()
    if len(sample_nums) == 0:
        return 1
    return sample_nums[-1] + 1


class GiwaxsBarCreatorControlPanel(Measurement):
    
    name = "giwaxs_bar_creator"
    
    default_trayname = 'No Tray or Carrier Scanned'
    default_trayuuid = "Scan/Enter Tray or Carrier UUID"

    default_barname = ''
    default_baruuid = ''

    def setup(self):
        self.mf_crucible = self.app.hardware['mf_crucible_nirvana']
        S = self.settings

        # Bar Info
        S.New('bar_name', initial = self.default_barname, dtype = str)
        S.New('bar_mf_uuid', initial = self.default_baruuid, dtype = str)
        S.New(f'bar_als_uuid', initial = self.default_baruuid, dtype = str)


        # Tray Info
        S.New('tray_name', initial = self.default_trayname, dtype = str)
        S.New("tray_uuid", initial = self.default_trayuuid, dtype = str)
        
        # Enter Sample Info 
        bar_pos_options = list(range(1,13))
        S.New('select_bar_pos', initial = 1, choices = (bar_pos_options), dtype = int)
        S.New('enter_distance_mm', initial = 0.0, dtype = float)
        S.New('select_thinfilm', initial = '', choices = ([]), dtype = str)

        # Populated Bar Layout
        wafer_width = 15 
        for i in range(1,15):
            S.New(f'pos{i}_distance_mm', initial = (i*wafer_width)+25, dtype = float)
            S.New(f'pos{i}_thin_film', initial = '', dtype = str)
            S.New(f'pos{i}_thin_film_mfid', initial = '', dtype = str)
            S.New(f'pos{i}_thin_film_descrip', initial = '', dtype = str)

        # actions
        S.tray_uuid.add_listener(self.on_enter_tray_uuid, argtype = str)
        self.setup_ui()
    

    def setup_ui(self):
        
        S = self.settings
        self.ui_filename = sibling_path(__file__,"giwaxs-bar-creator.ui")
        ui = self.ui = load_qt_ui_file(self.ui_filename)

        # connect to layout defined in ui file
        S.bar_name.connect_to_widget(ui.lineEdit_bar_name)
        S.bar_mf_uuid.connect_to_widget(ui.lineEdit_mf_bar_uuid)
        S.bar_als_uuid.connect_to_widget(ui.lineEdit_als_bar_uuid)

        S.tray_name.connect_to_widget(ui.label_tray_name)
        S.tray_uuid.connect_to_widget(ui.lineEdit_tray_uuid)

        S.select_bar_pos.connect_to_widget(ui.comboBox_select_barpos)
        S.enter_distance_mm.connect_to_widget(ui.doubleSpinBox_enter_mm)
        S.select_thinfilm.connect_to_widget(ui.comboBox_select_thinfilm)
        
        for i in range(1,15):
            S[f'pos{i}_distance_mm'].connect_to_widget(ui[f'doubleSpinBox_mm_{i}'])
            S[f'pos{i}_thin_film'].connect_to_widget(ui[f'lineEdit_tf_{i}'])

        ui.pushButton_create_bar.clicked.connect(self.generate_bar_info)
        ui.pushButton_add_to_bar.clicked.connect(self.add_sample_to_bar_layout)
        ui.pushButton_print_barcode.clicked.connect(self.print_barcode)
        ui.pushButton_upload_bar.clicked.connect(self.add_bar_samples_to_database)
    
    
    def update_lq(self, newval, lq_name):
        lq = self.settings.get_lq(lq_name)
        lq.update_value(newval)

    def update_lq_list(self, new_choices, new_value, lq_name):
        prop_lq = self.settings.get_lq(lq_name)
        prop_lq.change_choice_list(new_choices)
        prop_lq.update_value(new_value)

    # === TODO: Add Dialog if this fails // AND IF SUCCEEDS
    # === TODO: clear bar layout when you create a new bar // also clear the all_sample_info
    # === NOTE: does it make sense to have a setting the whole time that is a list of the samples in the layout..
    def generate_bar_info(self):
        bar_name = self.read_bar_number_from_crucible()

        # CREATE IN CRUCIBLE
        new_crux_bar = cruc_client.add_sample(sample_name = bar_name,
                                    creation_date = get_tz_isoformat(),
                                    owner_orcid = self.mf_crucible.settings['orcid'],
                                    project_id = self.mf_crucible.settings['project_id'],
                                    sample_type = 'giwaxs bar'
                                    )
        mfid = new_crux_bar['unique_id']

        # CREATE IN ALS SCICAT
        new_als_set = als_sc_client.create_set(name = bar_name, 
                                               groupId = '733',
                                               proposalId = 'DD-00839',
                                               description = f'MF Thin Film Perovskites GWBAR (mfid: {mfid})')

        # ADD ALS INFO TO CRUCIBLE
        cruc_client.update_sample(sample_description =f'ALS GIWAXS Bar || Set ID: {new_als_set['id']}' )

        self.update_lq(new_crux_bar['unique_id'], 'bar_mf_uuid')
        self.update_lq(new_als_set['id'], 'bar_als_uuid')



    def read_bar_number_from_crucible(self):
        bar_number = self.get_next_serial_sample(self.mf_crucible.settings['project_id'],'GWBAR')
        bar_name = f'GWBAR{bar_number:06d}'
        self.update_lq(bar_name, 'bar_name')
        return bar_name


    def on_enter_tray_id(self):
        tray_uuid = self.settings[f'tray_uuid']
        if len(tray_uuid) != 26:
            self.update_lq(self.default_trayname, tray_name)
            self.update_lq_list([], '', 'select_thinfilm')
            return tray_uuid
        
        # tray / carrier info
        tray_info = cruc_client.get_sample(sample_id = tray_uuid)
        tray_name = tray_info['sample_name']
        self.update_lq(tray_name, f'tray_name')
        
        # update thin film choices to select from
        samples_on_tray = cruc_client.list_samples(parent_id = tray_uuid)
        sorted_samples = sorted(samples_on_tray, key=lambda item: item['sample_name'])
        sorted_sample_names = [x['sample_name'] for x in sorted_samples]
        self.update_lq_list(sorted_sample_names, sorted_sample_names[0],'select_thinfilm')
        


    def add_sample_to_bar_layout(self):
        i = self.settings['select_bar_pos']
        tf_name = self.settings['select_thinfilm']
        tf_found = cruc_client.list_samples(sample_name = tf_name, project_id = self.mf_crucible.settings['project_id'])
        if len(tf_found) == 1:
            tf_found = tf_found[0]
        else:
            print(f'{tf_found}')
            return
        
        tf_mfid = tf_found['unique_id']
        tf_descrip = tf_found['description']
        self.update_lq(tf_name, f'pos{i}_thin_film')
        self.update_lq(tf_mfid, f'pos{i}_thin_film_mfid')
        self.update_lq(tf_descrip, f'pos{i}_thin_film_descrip')
        self.update_lq(self.settings['enter_distance'], f'pos{i}_distance_mm')
        return


    def print_barcode(self):
        pass

    
    def collect_single_sample_info(self, i):
        tf_name = self.settings[f'pos{i}_thin_film']
        tf_mfid = self.settings[f'pos{i}_thin_film_mfid']
        tf_descrip = self.settings[f'pos{i}_thin_film_descrip']

        # get metadata
        sample_ds = cruc_client.list_datasets(sample_id = tf_mfid, measurement = 'spin_run', include_metadata = True)
        sample_synds = [ds for ds in sample_ds if ds['measurement'] == 'spin_run'] # filtering currently broken
        sample_syn_md = sample_synds['scientific_metadata']['scientific_metadata']

        # NOTE: Is it appropriate to have our metadata in parameters? - do we need to recalculate center?
        sample_syn_md['mfid'] = tf_mfid
        sample_syn_md["sample_center_position"]= self.settings[f'pos{i}_thin_film_dist']
        sample_syn_md["incident_angles"] =  "0.14" # ??

        sample_info_preview = {'bar position': i,
                               'tf_name': tf_name,
                               'tf_mfid': tf_mfid,
                               'sample_parameters': sample_syn_md
                               }
        
        return sample_info_preview

    def collect_all_sample_info(self):
        import time
        stime = time.now()
        self.all_sample_info = []
        for i in range(1,15):
            # TODO: parallelize
            sample_info_preview = self.collect_single_sample_info(i)
            self.all_sample_info.append(sample_info_preview)
            # TODO: sort results by position
        etime = time.now()
        print(f'took {etime - stime}s')
        return
    
    # === TODO: ADD A BUTTON FOR THIS AND A WIDGET TO VIEW / OR DIALOG POPUP 
    # ==== NOTE: OR MAYBE INSTEAD OF PREVIEW. THERE IS A DIALOG IN THE UPLOAD FUNC
    def preview_samples_for_upload(self):
        if not self.all_sample_info:
            self.collect_all_sample_info()
        # TODO: display this info somewhere
        return

    # TODO: Add dialog on success or fail
    def upload_to_database(self):
        if not self.all_sample_info:
            self.collect_all_sample_info()
        
        for tf in self.all_sample_info():
            tf_name = tf['tf_name']
            tf_mfid = tf['tf_mfid']

            # link to bar in crucible
            cruc_client.link_samples(parent_sample_id = self.settings['bar_mf_uuid'],
                                     child_sample_id = tf_mfid)

            # create sample in ALS scicat
            # sample_ds = cruc_client.list_datasets(sample_id = tf_mfid, measurement = 'spin_run', include_metadata = True)
            # sample_synds = [ds for ds in sample_ds if ds['measurement'] == 'spin_run'] # filtering currently broken
            # sample_syn_md = sample_synds['scientific_metadata']['scientific_metadata']
            # sample_syn_md['mfid'] = tf_mfid

            new_als_samp = als_sc_client.create_sample(name = tf_name,
                                        group_id = '733',
                                        proposal_id = 'DD-00839',
                                        scan_type = 'GIWAXS',
                                        set_id = self.settings['bar_als_uuid'],
                                        description = f'TMF Perovskite Thin Film (mfid: {tf_mfid})',
                                        parameters = tf['sample_parameters'])
            
            # update sample in crucible
            updated_description = f'{tf['tf_descrip']} {new_als_samp['id']}'.strip()
            cruc_client.update_sample(tf_mfid, sample_description = updated_description)
            return
    # === TODO: CREATE AN OUTPUT FILE WITH ALL THE SETTINGS