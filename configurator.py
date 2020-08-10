import os

import yaml
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QFileDialog, QDialogButtonBox


# import preferences_ui

# os.environ[
#     'QT_QPA_PLATFORM_PLUGIN_PATH'] = '/Users/kevin/opt/anaconda3/envs/ml/lib/python3.7/site-packages/PySide2/Qt/plugins'


class Configurator:
    def __init__(self, conf_file_path=None, conf_to_get='default'):
        self.conf_file_path = conf_file_path
        self.conf_to_get = conf_to_get

        # dicts
        self.default_conf_dict = {
            'root for file dialog init open': '.',
            'root for tagging results': './results/',
            'default processing mode': 'Copy',
            'image default display size': [600, 600],
            'tags set': ['Tag0', 'Tag1', 'Tag2', 'Tag3']
        }
        self.using_conf_dict = self.default_conf_dict.copy()  # using conf
        self.read_conf_file('default', 'application-config.yml')  # read default
        if not os.path.exists(self.conf_file_path):
            self.save_conf_file(self.using_conf_dict, 'using conf', 'user-config.yml')

        if self.conf_file_path:
            self.read_conf_file(self.conf_to_get, self.conf_file_path)
        self.tmp_conf_dict = self.using_conf_dict.copy()  # unsaved conf
        self.conf_changed_dict = {
            'root for file dialog init open': False,
            'root for tagging results': False,
            'default processing mode': False,
            'image default display size': False,
            'tags set': False
        }
        self.using_conf_changed_dict = self.conf_changed_dict.copy()

        self.preferences_ui = QUiLoader().load('./ui/preferences.ui')
        # self.preferences_ui = preferences_ui.Ui_Dialog()
        # self.get_and_set_ui(self.using_conf_dict)

        # handle
        self.preferences_ui.root_dialog_line_edit.textChanged.connect(self.get_and_set_root_for_dialog)
        self.preferences_ui.root_tagged_line_edit.textChanged.connect(self.get_and_set_root_for_tagged)
        self.preferences_ui.root_dialog_btn.clicked.connect(self.change_root_for_dialog_by_file_dialog)
        self.preferences_ui.root_tagged_btn.clicked.connect(self.change_root_for_tagged_by_file_dialog)
        self.preferences_ui.default_processing_mode_btn_group.buttonClicked.connect(
            self.get_and_set_default_processing_mode)
        self.preferences_ui.img_h_val.valueChanged.connect(self.get_and_set_image_default_display_h_size)
        self.preferences_ui.img_w_val.valueChanged.connect(self.get_and_set_image_default_display_w_size)
        self.preferences_ui.tags_set_text_edit.textChanged.connect(self.get_and_set_tags_set)
        self.preferences_ui.dialog_btn_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
            self.restore_defaults)
        # self.preferences_ui.dialog_btn_box.accepted.connect(self.confirm_settings)

    def read_conf_file(self, conf_to_get='default', conf_file_path=None):
        if conf_file_path:
            with open(conf_file_path, 'r') as f:
                confs = yaml.load(f, Loader=yaml.FullLoader)
            # print(confs)
            conf = confs[conf_to_get]
            if conf['root for file dialog init open']:
                self.using_conf_dict['root for file dialog init open'] = conf['root for file dialog init open']
            if conf['root for tagging results']:
                self.using_conf_dict['root for tagging results'] = conf['root for tagging results']
            if conf['default processing mode']:
                self.using_conf_dict['default processing mode'] = conf['default processing mode']
            if conf['image default display size']:
                self.using_conf_dict['image default display size'] = conf['image default display size']
            if conf['tags set']:
                self.using_conf_dict['tags set'] = conf['tags set']
            if conf_to_get == 'default':
                self.default_conf_dict = self.using_conf_dict.copy()
        else:
            print('No configure file path')

    def save_conf_file(self, conf_dict, conf_name, conf_file_path):
        if conf_name == self.conf_to_get and conf_file_path == 'user-config.yml':
            mode = 'w'
        else:
            mode = 'a'
        # print(yaml.dump(conf_dict))
        save_conf_dict = dict()
        save_conf_dict[conf_name] = conf_dict
        with open(conf_file_path, mode) as f:
            f.write(yaml.dump(save_conf_dict))

    def get_and_set_ui(self, conf_dict):
        QApplication.processEvents()
        self.preferences_ui.root_dialog_line_edit.setText(conf_dict['root for file dialog init open'])
        self.preferences_ui.root_tagged_line_edit.setText(conf_dict['root for tagging results'])
        default_processing_modes = ['Tag Only', 'Move', 'Copy']
        self.preferences_ui.default_processing_mode_btn_group.buttons()[
            default_processing_modes.index(conf_dict['default processing mode'])].setChecked(True)
        self.preferences_ui.img_h_val.setValue(conf_dict['image default display size'][0])
        self.preferences_ui.img_w_val.setValue(conf_dict['image default display size'][1])
        tags_set_text = ''.join(str(t) + '\n' for t in conf_dict['tags set'])
        self.preferences_ui.tags_set_text_edit.setPlainText(tags_set_text)

    def change_root_for_dialog_by_file_dialog(self):
        self.open_dir("dialog")

    def change_root_for_tagged_by_file_dialog(self):
        self.open_dir("tagged")

    def get_and_set_root_for_dialog(self):
        self.tmp_conf_dict['root for file dialog init open'] = self.preferences_ui.root_dialog_line_edit.text()
        self.using_conf_changed_dict['root for file dialog init open'] = True
        # print('Changed: root for file dialog init open', self.tmp_conf_dict['root for file dialog init open'])

    def get_and_set_root_for_tagged(self):
        self.tmp_conf_dict['root for tagging results'] = self.preferences_ui.root_tagged_line_edit.text()
        self.using_conf_changed_dict['root for tagging results'] = True
        # print('Changed: root for tagging results', self.tmp_conf_dict['root for tagging results'])

    def open_dir(self, for_which):
        dir_path = QFileDialog.getExistingDirectory(self.preferences_ui,
                                                    "Select one dir",
                                                    self.using_conf_dict['root for file dialog init open'])
        if dir_path == '':
            self.preferences_ui.info_box_label.setText("No dir selected")
        else:
            if for_which == "dialog":
                self.preferences_ui.root_dialog_line_edit.setText(dir_path)
            else:
                self.preferences_ui.root_tagged_line_edit.setText(dir_path)
        return dir_path

    def get_and_set_default_processing_mode(self):
        mode_btn = self.preferences_ui.default_processing_mode_btn_group.checkedButton()
        self.tmp_conf_dict['default processing mode'] = mode_btn.text()
        self.preferences_ui.info_box_label.setText("If confirm 'OK', the current processing mode will also change")
        self.using_conf_changed_dict['default processing mode'] = True
        # print('Changed: default processing mode', self.tmp_conf_dict['default processing mode'])

    def get_and_set_image_default_display_h_size(self):
        self.tmp_conf_dict['image default display size'][0] = self.preferences_ui.img_h_val.value()
        self.using_conf_changed_dict['image default display size'] = True
        # print('Changed: image default display size', self.tmp_conf_dict['image default display size'])

    def get_and_set_image_default_display_w_size(self):
        self.tmp_conf_dict['image default display size'][1] = self.preferences_ui.img_w_val.value()
        self.using_conf_changed_dict['image default display size'] = True
        # print('Changed: image default display size', self.tmp_conf_dict['image default display size'])

    def get_and_set_tags_set(self):
        self.tmp_conf_dict['tags set'] = self.preferences_ui.tags_set_text_edit.toPlainText().splitlines()
        if self.tmp_conf_dict['tags set'] != self.using_conf_dict['tags set']:
            self.using_conf_changed_dict['tags set'] = True
            # print('Changed: tags set:\n', self.tmp_conf_dict['tags set'])

    def restore_defaults(self):
        self.tmp_conf_dict = self.default_conf_dict.copy()
        self.get_and_set_ui(self.tmp_conf_dict)
        self.preferences_ui.info_box_label.setText("Press 'OK' to confirm")

# if __name__ == '__main__':
#     app = QApplication([])
#     tester = Configurator('conf.yml', 'conf_for_fau')
#     tester.preferences_ui.show()
#     app.exec_()
