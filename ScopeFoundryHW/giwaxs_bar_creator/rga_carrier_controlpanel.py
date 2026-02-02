from ScopeFoundry.measurement import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from mfid import mfid
import os
import csv
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


# RGA position mapping (A-F rows, 1-6 columns)
RGA_POSITIONS = []
for row in 'ABCDEF':
    for col in range(1, 7):
        RGA_POSITIONS.append(f'{row}{col}')

# Placeholder positions - these will need to be calibrated
# Format: {position: (x, y)}
RGA_POSITION_COORDS = {
    'A1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'A2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'A3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'A4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'A5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'A6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'B6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'C6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'D6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'E6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F1': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F2': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F3': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F4': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F5': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
    'F6': ('PLACEHOLDER_X', 'PLACEHOLDER_Y'),
}


class RgaCarrierControlPanel(Measurement):

    name = "rga_carrier_creator"

    default_carrier_name = 'No Carrier Scanned'
    default_carrier_uuid = ''

    default_rga_name = ''
    default_rga_uuid = ''

    default_session_name = 'session name'
    default_email = 'user-email@lbl.gov'
    default_user_name = ''
    default_comments= 'comments'
    default_tags="tags,separated,by,commas"
    default_orcid = ''

    def setup(self):
        S = self.settings

        # Crucible
        S.New("email", initial = self.default_email, dtype = str)
        S.New("user_name", initial = self.default_user_name, dtype = str)
        S.New("orcid", initial = self.default_orcid, dtype = str)
        S.New("project", initial = "", choices = ([]), dtype = str)
        S.New("session_name", initial = self.default_session_name, dtype = str)
        S.New("comments", initial = self.default_comments, dtype = str)
        S.New("tags", initial = self.default_tags, dtype = str)

        # RGA Carrier Info
        S.New('rga_name', initial = self.default_rga_name, dtype = str)
        S.New('rga_mf_uuid', initial = self.default_rga_uuid, dtype = str)
        S.New(f'rga_als_uuid', initial = self.default_rga_uuid, dtype = str)

        # Source Carrier Info (where samples come from)
        S.New('carrier_name', initial = self.default_carrier_name, dtype = str)
        S.New("carrier_uuid", initial = self.default_carrier_uuid, dtype = str)

        # Enter Sample Info
        S.New('select_rga_pos', initial = 'A1', choices = (RGA_POSITIONS), dtype = str)
        S.New('select_thinfilm', initial = '', choices = ([]), dtype = str)

        # RGA Layout - 36 positions (A1-F6)
        for pos in RGA_POSITIONS:
            S.New(f'pos_{pos}_thin_film', initial = '', dtype = str)

        # Shutter and mass range parameters for RGA CSV
        S.New('shutter_open_s', initial = 300, dtype = int)
        S.New('mass_range_amu', initial = 300, dtype = int)

        # actions
        S.email.add_listener(self.on_enter_email, argtype = str)
        S.rga_name.add_listener(self.on_enter_rga_name, argtype = str)
        S.carrier_uuid.add_listener(self.on_enter_carrier_uuid, argtype = str)

        # Initialize all_sample_info
        self.all_sample_info = []
        self.setup_ui()


    def setup_ui(self):
        S = self.settings
        self.ui_filename = sibling_path(__file__,"rga-carrier-creator.ui")
        ui = self.ui = load_qt_ui_file(self.ui_filename)

        # connect to layout defined in ui file
        S.email.connect_to_widget(ui.email_lineEdit)
        S.user_name.connect_to_widget(ui.username_lineEdit)
        S.project.connect_to_widget(ui.project_comboBox)
        S.session_name.connect_to_widget(ui.session_lineEdit)
        S.comments.connect_to_widget(ui.comments_lineEdit)
        S.tags.connect_to_widget(ui.tags_lineEdit)

        S.rga_name.connect_to_widget(ui.lineEdit_rgaName)
        S.rga_mf_uuid.connect_to_widget(ui.lineEdit_mf_rga_uuid)
        S.rga_als_uuid.connect_to_widget(ui.lineEdit_als_rga_uuid)

        S.carrier_name.connect_to_widget(ui.label_carrier_name)
        S.carrier_uuid.connect_to_widget(ui.lineEdit_carrier_uuid)

        S.select_rga_pos.connect_to_widget(ui.comboBox_select_rgapos)
        S.select_thinfilm.connect_to_widget(ui.comboBox_select_thinfilm)

        S.shutter_open_s.connect_to_widget(ui.spinBox_shutter)
        S.mass_range_amu.connect_to_widget(ui.spinBox_mass_range)

        # Connect position widgets
        for pos in RGA_POSITIONS:
            S.get_lq(f'pos_{pos}_thin_film').connect_to_widget(getattr(self.ui, f'lineEdit_tf_{pos}'))

        ui.logout_button.clicked.connect(self.clear_userinfo)
        ui.pushButton_create_rga_crucible.clicked.connect(self.upload_rga_info_crucible)
        ui.pushButton_create_rga_als.clicked.connect(self.upload_rga_info_als)
        ui.pushButton_add_to_rga.clicked.connect(self.add_sample_to_rga_layout)
        ui.pushButton_add_all.clicked.connect(self.add_all)
        ui.pushButton_upload_rga.clicked.connect(self.add_rga_samples_to_database)
        ui.pushButton_new_rga_name.clicked.connect(self.read_rga_number_from_crucible)
        ui.pushButton_clear_rga.clicked.connect(self.clear_rga_layout)
        ui.pushButton_generate_csv.clicked.connect(self.generate_rga_csv)

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

    def on_enter_rga_name(self):
        mf_rgas = cruc_client.list_samples(sample_name=self.settings['rga_name'])
        if len(mf_rgas) == 1:
            mfid = mf_rgas[0]['unique_id']
            alsid = mf_rgas[0]['description'].split('|| Set ID:')[-1].strip()
        else:
            print(f'{mf_rgas=}')
            return

        self.update_lq(mfid, 'rga_mf_uuid')
        self.update_lq(alsid, 'rga_als_uuid')

    def clear_userinfo(self):
        self.settings['user_name'] = self.default_user_name
        self.settings['orcid'] = self.default_orcid
        self.settings['email'] = self.default_email
        self.settings['session_name'] = self.default_session_name
        self.settings['tags'] = self.default_tags
        self.settings['comments'] = self.default_comments

        prop_lq = self.get_lq('project')
        prop_lq.change_choice_list([])
        prop_lq.update_value("")

    def clear_rga_layout(self):
        """Clear all RGA layout positions"""
        for pos in RGA_POSITIONS:
            self.update_lq('', f'pos_{pos}_thin_film')
        self.all_sample_info = []

    def upload_rga_info_crucible(self):
        try:
            rga_name = self.settings['rga_name']

            # CREATE IN CRUCIBLE
            new_crux_rga = cruc_client.add_sample(sample_name = rga_name,
                                        creation_date = get_tz_isoformat(),
                                        owner_orcid = self.settings['orcid'],
                                        project_id = self.settings['project'],
                                        sample_type = 'rga carrier'
                                        )
            mfid = new_crux_rga['unique_id']
            self.update_lq(mfid, 'rga_mf_uuid')

            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "RGA Carrier Created Successfully",
                f"RGA Carrier '{self.settings['rga_name']}' created successfully!\n\n"
                f"Crucible UUID: {self.settings['rga_mf_uuid']}\n\n"
                "Please add to the ALS Scicat Database next"
            )
            return

        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "RGA Carrier Creation Failed",
                f"Failed to create RGA carrier.\n\nError: {str(e)}"
            )
            return

    def upload_rga_info_als(self):
        try:
            if self.settings['rga_mf_uuid'] == '':
                raise Exception("Please add to crucible before adding to the ALS database")

            # CREATE IN ALS SCICAT
            new_als_set = als_sc_client.create_set(name = self.settings['rga_name'],
                                                   groupId = '733',
                                                   proposalId = 'DD-00839',
                                                   description = f'MF RGA Carrier (mfid: {self.settings['rga_mf_uuid']})')
            print(new_als_set)
            print(new_als_set.id)

            # ADD ALS INFO TO CRUCIBLE
            cruc_client.update_sample(unique_id= self.settings['rga_mf_uuid'],
                                     description =f'ALS RGA Carrier || Set ID: {new_als_set.id}')
            self.update_lq(new_als_set.id, 'rga_als_uuid')

            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "RGA Carrier Created Successfully",
                f"RGA Carrier '{self.settings['rga_name']}' created successfully!\n\n"
                f"Crucible UUID: {self.settings['rga_mf_uuid']}\n"
                f"ALS Set ID: {self.settings['rga_als_uuid']}"
            )
            return

        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "RGA Carrier Creation Failed",
                f"Failed to create RGA carrier.\n\nError: {str(e)}"
            )
            return

    def read_rga_number_from_crucible(self):
        rga_number = get_next_serial_sample('RGA', self.settings['project'])
        rga_name = f'RGA{rga_number:06d}'
        self.update_lq(rga_name, 'rga_name')
        return rga_name

    def on_enter_carrier_uuid(self, carrier_uuid):
        if len(carrier_uuid) != 26:
            self.update_lq(self.default_carrier_name, 'carrier_name')
            self.update_lq_list([], '', 'select_thinfilm')
            return carrier_uuid

        # carrier info
        carrier_info = cruc_client.get_sample(sample_id = carrier_uuid)
        carrier_name = carrier_info['sample_name']
        self.update_lq(carrier_name, f'carrier_name')

        # update thin film choices to select from
        samples_on_carrier = cruc_client.list_samples(parent_id = carrier_uuid)
        sorted_samples = sorted(samples_on_carrier, key=lambda item: item['sample_name'])
        sorted_sample_names = [x['sample_name'] for x in sorted_samples]
        self.update_lq_list(sorted_sample_names, sorted_sample_names[0],'select_thinfilm')

    def add_all(self):
        lq = self.settings.get_lq('select_thinfilm')
        tflist = [t[0] for t in lq.choices]
        print(tflist)
        tfind = 0
        for pos in RGA_POSITIONS:
            if tfind >= len(tflist):
                break
            if self.settings[f'pos_{pos}_thin_film'] == '':
                tf_name = tflist[tfind]
                self.update_lq(tf_name, f'pos_{pos}_thin_film')
                tfind += 1

    def add_sample_to_rga_layout(self):
        pos = self.settings['select_rga_pos']
        tf_name = self.settings['select_thinfilm']
        self.update_lq(tf_name, f'pos_{pos}_thin_film')
        return

    def collect_single_sample_info(self, pos):
        tf_name = self.settings[f'pos_{pos}_thin_film']

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
        sample_synds = [ds for ds in sample_ds if ds['measurement'] == 'spin_run']

        if not sample_synds:
            return None

        sample_syn_md = sample_synds[0]['scientific_metadata']['scientific_metadata']
        sample_syn_md['mfid'] = tf_mfid

        sample_info_preview = {
            'rga_position': pos,
            'tf_name': tf_name,
            'tf_mfid': tf_mfid,
            'tf_descrip': tf_descrip,
            'sample_parameters': sample_syn_md
        }

        return sample_info_preview

    def collect_all_sample_info(self):
        import time
        stime = time.time()
        self.all_sample_info = []
        for pos in RGA_POSITIONS:
            sample_info_preview = self.collect_single_sample_info(pos)
            if sample_info_preview:
                self.all_sample_info.append(sample_info_preview)

        # Sort by position
        self.all_sample_info.sort(key=lambda x: RGA_POSITIONS.index(x['rga_position']))

        etime = time.time()
        print(f'took {etime - stime}')

    def show_sample_preview_dialog(self):
        """Show preview dialog with sample information"""
        if not self.all_sample_info:
            QtWidgets.QMessageBox.warning(
                self.ui,
                "No Samples",
                "No samples found in RGA carrier layout."
            )
            return False

        # Create preview text
        preview_text = f"RGA Carrier Name: {self.settings['rga_name']}\n"
        preview_text += f"Crucible UUID: {self.settings['rga_mf_uuid']}\n"
        preview_text += f"ALS Set ID: {self.settings['rga_als_uuid']}\n\n"
        preview_text += f"Samples ({len(self.all_sample_info)}):\n"
        preview_text += "-" * 60 + "\n"

        for sample in self.all_sample_info:
            preview_text += f"\nPosition {sample['rga_position']}: {sample['tf_name']}\n"
            preview_text += f"  MFID: {sample['tf_mfid']}\n"
            preview_text += f"Metadata: {sample['sample_parameters']}\n"

        # Create dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Sample Preview")
        dialog.resize(700, 500)
        dialog.setMinimumSize(500, 400)
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

    def add_rga_samples_to_database(self):
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

                # link to RGA carrier in crucible
                cruc_client.link_samples(parent_id = self.settings['rga_mf_uuid'],
                                         child_id = tf_mfid)

                new_als_samp = als_sc_client.create_sample(name = tf_name,
                                            group_id = '733',
                                            proposal_id = 'DD-00839',
                                            scan_type = 'RGA',
                                            set_id = self.settings['rga_als_uuid'],
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

    def generate_rga_csv(self):
        """Generate RGA input CSV file based on current layout"""
        try:
            # Collect sample information
            self.collect_all_sample_info()

            if not self.all_sample_info:
                QtWidgets.QMessageBox.warning(
                    self.ui,
                    "No Samples",
                    "No samples found in RGA carrier layout. Cannot generate CSV."
                )
                return

            # Ask user for save location
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.ui,
                "Save RGA Input CSV",
                f"{self.settings['rga_name']}_RGA_INPUT.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return  # User cancelled

            # Write CSV file
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['sample spot', 'sample x', 'sample y', 'sample_name',
                             'shutter open,s', 'mass range, amu', 'group_name']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                for sample in self.all_sample_info:
                    pos = sample['rga_position']
                    x_coord, y_coord = RGA_POSITION_COORDS[pos]

                    writer.writerow({
                        'sample spot': pos,
                        'sample x': x_coord,
                        'sample y': y_coord,
                        'sample_name': sample['tf_name'],
                        'shutter open,s': self.settings['shutter_open_s'],
                        'mass range, amu': self.settings['mass_range_amu'],
                        'group_name': sample['tf_name']
                    })

            # Success dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "CSV Generated",
                f"RGA input CSV generated successfully!\n\nSaved to: {file_path}\n\n"
                f"Note: X and Y coordinates are placeholders and need to be calibrated."
            )

        except Exception as e:
            # Failure dialog
            QtWidgets.QMessageBox.critical(
                self.ui,
                "CSV Generation Failed",
                f"Failed to generate CSV file.\n\nError: {str(e)}"
            )
