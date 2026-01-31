from ScopeFoundry.measurement import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from mfid import mfid
import os
from qtpy import QtWidgets

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
#test_qr_code = "HTTPS://DATAPORTAL-STAGING.ALS.LBL.GOV/SAMPLE-TRACKING/SET/B84387D1-5EE9-4FC9-AD2D-49D64A2422EF"

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
    print(sample_nums)
    if len(sample_nums) == 0:
        return 1
    return sample_nums[-1] + 1


class GiwaxsBarCreatorControlPanel(Measurement):
    
    name = "giwaxs_bar_creator"
    
    default_trayname = 'No Tray or Carrier Scanned'
    default_trayuuid = ''#"Scan/Enter Tray or Carrier UUID"

    default_barname = ''
    default_baruuid = ''

    default_session_name = 'session name'
    default_email = 'user-email@lbl.gov'
    default_user_name = ''
    default_comments= 'comments'
    default_tags="tags,separated,by,commas"
    default_orcid = ''

    def setup(self):


       # self.mf_crucible = self.app.hardware['mf_crucible_nirvana']
        S = self.settings

        # Crucible
        S.New("email", initial = self.default_email, dtype = str)
        S.New("user_name", initial = self.default_user_name, dtype = str)
        S.New("orcid", initial = self.default_orcid, dtype = str)
        S.New("project", initial = "", choices = ([]), dtype = str)
        S.New("session_name", initial = self.default_session_name, dtype = str)

        S.New("comments", initial = self.default_comments, dtype = str)
        S.New("tags", initial = self.default_tags, dtype = str)

        # Bar Info
        S.New('bar_name', initial = self.default_barname, dtype = str)
        S.New('bar_mf_uuid', initial = self.default_baruuid, dtype = str)
        S.New(f'bar_als_uuid', initial = self.default_baruuid, dtype = str)

        # Tray Info
        S.New('tray_name', initial = self.default_trayname, dtype = str)
        S.New("tray_uuid", initial = self.default_trayuuid, dtype = str)
        
        # Enter Sample Info 
        bar_pos_options = list(range(1,15))
        S.New('select_bar_pos', initial = 1, choices = (bar_pos_options), dtype = int)
        #S.New('enter_distance_mm', initial = 0.0, dtype = float)
        S.New('select_thinfilm', initial = '', choices = ([]), dtype = str)

        # Populated Bar Layout
        S.New('offset_from_left_mm', initial = 25)
        S.New('incidence_angle_all', initial = 0, dtype = float)
        S.New('wafer_width', initial = 15, dtype = float)

        for i in range(1,15):
            S.New(f'pos{i}_distance_mm', initial = ((i-1)*S['wafer_width'])+S['offset_from_left_mm'], dtype = float)
            S.New(f'pos{i}_thin_film', initial = '', dtype = str)
            S.New(f'pos{i}_incidence_angle', initial = S['incidence_angle_all'], dtype = float)

        # actions
        S.email.add_listener(self.on_enter_email, argtype = str)
        S.bar_name.add_listener(self.on_enter_bar_name, argtype = str)
        S.tray_uuid.add_listener(self.on_enter_tray_uuid, argtype = str)
        S.incidence_angle_all.add_listener(self.apply_incidence_angle, argtype = float)
        S.offset_from_left_mm.add_listener(self.recalc_positions, argtype = float)
        S.wafer_width.add_listener(self.recalc_positions, argtype = float)

        # Initialize all_sample_info
        self.all_sample_info = []
        self.setup_ui()
    

    def setup_ui(self):
        
        S = self.settings
        self.ui_filename = sibling_path(__file__,"giwaxs-bar-creator.ui")
        ui = self.ui = load_qt_ui_file(self.ui_filename)

        # connect to layout defined in ui file
        S.email.connect_to_widget(ui.email_lineEdit)
        S.user_name.connect_to_widget(ui.username_lineEdit)
        S.project.connect_to_widget(ui.project_comboBox)
        S.session_name.connect_to_widget(ui.session_lineEdit)
        S.comments.connect_to_widget(ui.comments_lineEdit)
        S.tags.connect_to_widget(ui.tags_lineEdit)

        S.bar_name.connect_to_widget(ui.lineEdit_barName)
        S.bar_mf_uuid.connect_to_widget(ui.lineEdit_mf_bar_uuid)
        S.bar_als_uuid.connect_to_widget(ui.lineEdit_als_bar_uuid)

        S.tray_name.connect_to_widget(ui.label_tray_name)
        S.tray_uuid.connect_to_widget(ui.lineEdit_tray_uuid)

        S.select_bar_pos.connect_to_widget(ui.comboBox_select_barpos)
        S.select_thinfilm.connect_to_widget(ui.comboBox_select_thinfilm)
        
        S.wafer_width.connect_to_widget(ui.doubleSpinBox_wafer_width)
        S.offset_from_left_mm.connect_to_widget(ui.doubleSpinBox_offset)
        S.incidence_angle_all.connect_to_widget(ui.doubleSpinBox_angle)
        for i in range(1,15):
            S.get_lq(f'pos{i}_distance_mm').connect_to_widget(getattr(self.ui, f'doubleSpinBox_mm_{i}'))
            S.get_lq(f'pos{i}_thin_film').connect_to_widget(getattr(self.ui, f'lineEdit_tf_{i}'))
           # S.get_lq(f'pos{i}_incidence_angle').connect_to_widget(getattr(self.ui, f'lineEdit_tf_{i}_angle'))

        ui.logout_button.clicked.connect(self.clear_userinfo)
        ui.pushButton_create_bar_crucible.clicked.connect(self.upload_bar_info_crucible)
        ui.pushButton_create_bar_als.clicked.connect(self.upload_bar_info_als)
        ui.pushButton_add_to_bar.clicked.connect(self.add_sample_to_bar_layout)
        ui.pushButton_add_all.clicked.connect(self.add_all)
        ui.pushButton_print_barcode.clicked.connect(self.print_barcode)
        ui.pushButton_upload_bar.clicked.connect(self.add_bar_samples_to_database)
        ui.pushButton_new_bar_name.clicked.connect(self.read_bar_number_from_crucible)
        ui.pushButton_clear_bar.clicked.connect(self.clear_bar_layout)
    
    def update_lq(self, newval, lq_name):
        lq = self.settings.get_lq(lq_name)
        lq.update_value(newval)
        
    def update_lq_list(self, new_choices, new_value, lq_name):
        prop_lq = self.settings.get_lq(lq_name)
        prop_lq.change_choice_list(new_choices)
        prop_lq.update_value(new_value)

    def on_enter_email(self):
        provided_email = self.settings.email.value.strip()
        user_info = cruc_client.get_user(email = provided_email)

        if user_info is None:
            return
        # update user info
        user_name = f'{user_info['first_name']}_{user_info['last_name']}'
        self.update_lq(user_name, 'user_name')
        self.update_lq(user_info['orcid'], 'orcid')

        # update project list
        projects = cruc_client.list_projects(user_info['orcid'])
        project_ids = [x['project_id'] for x in projects]
        project_ids.sort()
        self.update_lq_list(project_ids, project_ids[0], 'project')

    def on_enter_bar_name(self):
        mfid = ''
        alsid = ''
        mf_bars = cruc_client.list_samples(sample_name=self.settings['bar_name'])
        print(mf_bars)
        if len(mf_bars) == 1:
            mfid = mf_bars[0]['unique_id']
            descrip =  mf_bars[0]['description']
            if descrip is not None:
                alsid = mf_bars[0]['description'].split('|| Set ID:')[-1].strip()      

        self.update_lq(mfid, 'bar_mf_uuid')
        self.update_lq(alsid, 'bar_als_uuid')


    def clear_userinfo(self):
        print(self.settings.project)
        self.settings['user_name'] = self.default_user_name
        self.settings['orcid'] = self.default_orcid
        self.settings['email'] = self.default_email
        self.settings['session_name'] = self.default_session_name
        self.settings['tags'] = self.default_tags
        self.settings['comments'] = self.default_comments

        prop_lq = self.get_lq('project')
        prop_lq.change_choice_list([])
        prop_lq.update_value("")


    def recalc_positions(self):
        for i in range(1,15):
            new_mm = ((i-1)*self.settings['wafer_width'])+self.settings['offset_from_left_mm']
            self.update_lq(new_mm, f'pos{i}_distance_mm')

    def apply_incidence_angle(self):
        for i in range(1,15):
            self.update_lq(self.settings['incidence_angle_all'], f'pos{i}_incidence_angle')

    def clear_bar_layout(self):
        """Clear all bar layout positions"""
        for i in range(1, 15):
            self.update_lq('', f'pos{i}_thin_film')
        self.all_sample_info = []


    def upload_bar_info_crucible(self):
        try:
            bar_name = self.settings['bar_name']

            # CREATE IN CRUCIBLE
            new_crux_bar = cruc_client.add_sample(sample_name = bar_name,
                                        creation_date = get_tz_isoformat(),
                                        owner_orcid = self.settings['orcid'],
                                        project_id = self.settings['project'],
                                        sample_type = 'giwaxs bar'
                                        )
            mfid = new_crux_bar['unique_id']
            self.update_lq(mfid, 'bar_mf_uuid')
            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "Bar Created Successfully",
                f"Bar '{self.settings['bar_name']}' created successfully!\n\n"
                f"Crucible UUID: {self.settings['bar_mf_uuid']}\n\n"
                "Please add to the ALS Scicat Database next"
            )
            return
            
        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "Bar Creation Failed",
                f"Failed to create bar.\n\nError: {str(e)}"
            )
            return


    def upload_bar_info_als(self):
        try: 
            if self.settings['bar_mf_uuid'] == '':
                raise Exception("Please add to crucible before adding to the ALS database")
            
            # CREATE IN ALS SCICAT
            new_als_set = als_sc_client.create_set(name = self.settings['bar_name'], 
                                                   groupId = '733',
                                                   proposalId = 'DD-00839',
                                                   description = f'MF Thin Film Perovskites GWBAR (mfid: {self.settings['bar_mf_uuid']})')
            print(new_als_set)
            print(new_als_set.id)
            # ADD ALS INFO TO CRUCIBLE
            cruc_client.update_sample(unique_id= self.settings['bar_mf_uuid'], description =f'ALS GIWAXS Bar || Set ID: {new_als_set.id}' )
            self.update_lq(new_als_set.id, 'bar_als_uuid')
            
            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "Bar Created Successfully",
                f"Bar '{self.settings['bar_name']}' created successfully!\n\n"
                f"Crucible UUID: {self.settings['bar_mf_uuid']}\n"
                f"ALS Set ID: {self.settings['bar_als_uuid']}"
            )
            return
            
        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "Bar Creation Failed",
                f"Failed to create bar.\n\nError: {str(e)}"
            )
            return


    def read_bar_number_from_crucible(self):
        bar_number = get_next_serial_sample('GWBAR', self.settings['project'])
        bar_name = f'GWBAR{bar_number:06d}'
        self.update_lq(bar_name, 'bar_name')
        return bar_name


    def on_enter_tray_uuid(self, tray_uuid):
        if len(tray_uuid) != 26:
            self.update_lq(self.default_trayname, 'tray_name')
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


    def add_all(self):
        lq = self.settings.get_lq('select_thinfilm')
        tflist = [t[0] for t in lq.choices]
        print(tflist)
        tfind = 0
        for i in range(1,15):
            if tfind >= len(tflist):
                break
            if self.settings[f'pos{i}_thin_film'] == '':
                tf_name = tflist[tfind]
                self.update_lq(tf_name, f'pos{i}_thin_film')
                tfind+=1


    def add_sample_to_bar_layout(self):
        i = self.settings['select_bar_pos']
        tf_name = self.settings['select_thinfilm']
        self.update_lq(tf_name, f'pos{i}_thin_film')
        return


    def print_barcode(self):
        SAMPLE_TRACKER_URL = 'HTTPS://DATAPORTAL-STAGING.ALS.LBL.GOV/SAMPLE-TRACKING'
        from image_print import make_qr, make_nirvana_image, print_label
        bar_num = int(self.settings['bar_name'].split('GWBAR')[-1])
        short_bar_name = f'GWBAR{bar_num}'

        for uuid_key in ['bar_mf_uuid','bar_als_uuid']:
            uuid_val = self.settings[uuid_key]
            if uuid_key == 'bar_als_uuid':
                qrval = f'{SAMPLE_TRACKER_URL}/set/{uuid_val}'.upper()
            else:
                qrval = uuid_val

            qr_img = make_qr(qrval)
            make_nirvana_image(qr_img, [short_bar_name, uuid_val], f"batch_{uuid_key}.png")
            print_label("Brother PT-D610BT", f"batch_{uuid_key}.png")

    
    def collect_single_sample_info(self, i):
        tf_name = self.settings[f'pos{i}_thin_film']
        
        # Skip empty positions
        if not tf_name:
            return None
        
        tf_found = cruc_client.list_samples(sample_name = tf_name, project_id = self.settings['project'])
        if len(tf_found) == 1:
            tf_found = tf_found[0]

        else:
            print(f'{tf_found}')
            return
        
        tf_mfid = tf_found['unique_id']
        tf_descrip = tf_found['description']


        # get metadata
        sample_ds = cruc_client.list_datasets(sample_id = tf_mfid, measurement = 'spin_run', include_metadata = True)
        sample_synds = [ds for ds in sample_ds if ds['measurement'] == 'spin_run'] # filtering currently broken
        
        if not sample_synds:
            return None
            
        sample_syn_md = sample_synds[0]['scientific_metadata']['scientific_metadata']

        # NOTE: Is it appropriate to have our metadata in parameters? - do we need to recalculate center?
        sample_syn_md['mfid'] = tf_mfid
        sample_syn_md["sample_center_position"]= self.settings[f'pos{i}_distance_mm']
        sample_syn_md["incident_angles"] = self.settings[f'pos{i}_incidence_angle']

        sample_info_preview = {'bar_position': i,
                               'tf_name': tf_name,
                               'tf_mfid': tf_mfid,
                               'sample_parameters': sample_syn_md
                               }
        
        return sample_info_preview

    def collect_all_sample_info(self):
        import time
        stime = time.time()
        self.all_sample_info = []
        for i in range(1,15):
            # TODO: parallelize
            sample_info_preview = self.collect_single_sample_info(i)
            if sample_info_preview:  # Only add non-empty samples
                self.all_sample_info.append(sample_info_preview)
        
        # Sort results by position
        self.all_sample_info.sort(key=lambda x: x['bar_position'])
        
        etime = time.time()
        print(f'took {etime - stime}')
        

    def show_sample_preview_dialog(self):
        """Show preview dialog with sample information"""
        if not self.all_sample_info:
            QtWidgets.QMessageBox.warning(
                self.ui,
                "No Samples",
                "No samples found in bar layout."
            )
            return False
            
        # Create preview text
        preview_text = f"Bar Name: {self.settings['bar_name']}\n"
        preview_text += f"Crucible UUID: {self.settings['bar_mf_uuid']}\n"
        preview_text += f"ALS Set ID: {self.settings['bar_als_uuid']}\n\n"
        preview_text += f"Samples ({len(self.all_sample_info)}):\n"
        preview_text += "-" * 60 + "\n"
        
        for sample in self.all_sample_info:
            preview_text += f"\nPosition {sample['bar_position']}: {sample['tf_name']}\n"
            preview_text += f"  MFID: {sample['tf_mfid']}\n"
            preview_text += f"Metadata: {sample['sample_parameters']}\n"
        
        # Create dialog                                                                                                                                                                                                                                                       
        dialog = QtWidgets.QDialog(self.ui)                                                                                                                                                                                                                                   
        dialog.setWindowTitle("Sample Preview")                                                                                                                                                                                                                               
        dialog.resize(700, 500)                                                                                                                                                                                                                                               
        dialog.setMinimumSize(500, 400)                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                                                
        # Enable resizing                                                                                                                                                                                                                                                     
        dialog.setSizeGripEnabled(True)                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                                                
        layout = QtWidgets.QVBoxLayout()                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                                
        # Add label                                                                                                                                                                                                                                                           
        label = QtWidgets.QLabel("Review samples before uploading to database:")                                                                                                                                                                                              
        layout.addWidget(label)                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                                
        # Add text edit with preview                                                                                                                                                                                                                                          
        text_edit = QtWidgets.QTextEdit()                                                                                                                                                                                                                                     
        text_edit.setPlainText(preview_text)                                                                                                                                                                                                                                  
        text_edit.setReadOnly(True)                                                                                                                                                                                                                                           
        layout.addWidget(text_edit)                                                                                                                                                                                                                                           
                                                                                                                                                                                                                                                                                
        # Add buttons                                                                                                                                                                                                                                                         
        button_box = QtWidgets.QDialogButtonBox(                                                                                                                                                                                                                              
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel                                                                                                                                                                                                 
        )                                                                                                                                                                                                                                                                     
        button_box.accepted.connect(dialog.accept)                                                                                                                                                                                                                            
        button_box.rejected.connect(dialog.reject)                                                                                                                                                                                                                            
        layout.addWidget(button_box)                                                                                                                                                                                                                                          
                                                                                                                                                                                                                                                                                
        dialog.setLayout(layout)                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                
        # Show dialog and return result                                                                                                                                                                                                                                       
        result = dialog.exec_()                                                                                                                                                                                                                                               
        return result == QtWidgets.QDialog.Accepted 

    
    def add_bar_samples_to_database(self):
        try:
            # Collect all sample information
            self.collect_all_sample_info()
            
            # Show preview dialog - only continue if user clicks OK
            if not self.show_sample_preview_dialog():
                return
            
            # Upload samples
            for tf in self.all_sample_info:
                tf_name = tf['tf_name']
                tf_mfid = tf['tf_mfid']

                # link to bar in crucible
                cruc_client.link_samples(parent_id = self.settings['bar_mf_uuid'],
                                         child_id = tf_mfid)

                new_als_samp = als_sc_client.create_sample(name = tf_name,
                                            group_id = '733',
                                            proposal_id = 'DD-00839',
                                            scan_type = 'GIWAXS',
                                            set_id = self.settings['bar_als_uuid'],
                                            description = f'TMF Perovskite Thin Film (mfid: {tf_mfid})',
                                            parameters = tf['sample_parameters'])
                
                # update sample in crucible
                updated_description = f"{tf.get('tf_descrip', '')} {new_als_samp.id}".strip()
                cruc_client.update_sample(tf_mfid, description = updated_description)
            
            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "Upload Successful",
                f"Successfully uploaded {len(self.all_sample_info)} samples to database."
            )
            
        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "Upload Failed",
                f"Failed to upload samples to database.\n\nError: {str(e)}"
            )