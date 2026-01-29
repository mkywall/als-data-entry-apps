from ScopeFoundry.measurement import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from mfid import mfid


class MFCrucibleControlPanel(Measurement):
    
    name = "user_login_mf_crucible"
    default_session_name = 'session name'
    default_email = 'user-email@lbl.gov'
    default_user_name = ''
    default_tags="tags,separated,by,commas"
    default_comments ='comments'
    default_run_id = ''
    default_orcid = 'XXXX-XXXX-XXXX-XXXX'
    default_trayname = 'TRAYXXXXX'
    default_trayuuid = "Scan/Enter Tray UUID"

    def setup(self):
        self.setup_ui()
    
    def setup_ui(self):

        self.ui_filename = sibling_path(__file__,"crucible-layout-2.ui")
        ui = self.ui = load_qt_ui_file(self.ui_filename)

        self.hw_name = "mf_crucible_nirvana"
        self.mf_crucible = self.app.hardware[self.hw_name]

        # connect to layout defined in ui file
        self.mf_crucible.settings.email.connect_to_widget(ui.email_lineEdit)
        self.mf_crucible.settings.user_name.connect_to_widget(ui.username_lineEdit)
        self.mf_crucible.settings.project.connect_to_widget(ui.project_comboBox)
        self.mf_crucible.settings.session_name.connect_to_widget(ui.session_lineEdit)
        self.mf_crucible.settings.comments.connect_to_widget(ui.comments_lineEdit)
        self.mf_crucible.settings.tags.connect_to_widget(ui.tags_lineEdit)
        #self.mf_crucible.settings.uvvis_run_id.connect_to_widget(ui.runid_lineEdit)

        self.mf_crucible.settings.tray1_name.connect_to_widget(ui.tray1_name)
        self.mf_crucible.settings.tray1_uuid.connect_to_widget(ui.tray1_uuid)
        for ii in range(8):
            name_lq = self.mf_crucible.settings.get_lq(f"tray1_sample{ii+1}_name")
            name_lq.connect_to_widget(getattr(self.ui, f"tray1_sample{ii+1}_name"))

            uuid_lq = self.mf_crucible.settings.get_lq(f"tray1_sample{ii+1}_uuid")
            uuid_lq.connect_to_widget(getattr(self.ui, f"tray1_sample{ii+1}_uuid"))

        self.mf_crucible.settings.tray2_name.connect_to_widget(ui.tray2_name)
        self.mf_crucible.settings.tray2_uuid.connect_to_widget(ui.tray2_uuid)
        for ii in range(8):
            name_lq = self.mf_crucible.settings.get_lq(f"tray2_sample{ii+1}_name")
            name_lq.connect_to_widget(getattr(self.ui, f"tray2_sample{ii+1}_name"))

            uuid_lq = self.mf_crucible.settings.get_lq(f"tray2_sample{ii+1}_uuid")
            uuid_lq.connect_to_widget(getattr(self.ui, f"tray2_sample{ii+1}_uuid"))

        #ui.generate_runid_button.clicked.connect(self.generate_run_id)
        ui.logout_button.clicked.connect(self.clear_userinfo)
        ui.clear_samples_button.clicked.connect(self.clear_sampleinfo)
    
    def clear_userinfo(self):
        print(self.mf_crucible.settings.project)
        self.mf_crucible.settings['user_name'] = self.default_user_name
        self.mf_crucible.settings['orcid'] = self.default_orcid
        self.mf_crucible.settings['email'] = self.default_email
        self.mf_crucible.settings['session_name'] = self.default_session_name
        self.mf_crucible.settings['tags'] = self.default_tags
        self.mf_crucible.settings['comments'] = self.default_comments
       # self.mf_crucible.settings['uvvis_run_id'] = self.default_run_id
        prop_lq = self.mf_crucible.settings.get_lq('project')
        prop_lq.change_choice_list([])
        prop_lq.update_value("")

    def clear_sampleinfo(self):
        for ii in [1,2]:
            self.mf_crucible.settings[f'tray{ii}_uuid'] = self.default_trayuuid
            self.mf_crucible.settings[f'tray{ii}_name'] = self.default_trayname
            for jj in range(8):
                self.mf_crucible.settings[f'tray{ii}_sample{jj+1}_name'] = ''
                self.mf_crucible.settings[f'tray{ii}_sample{jj+1}_uuid'] = ''










