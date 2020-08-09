import os
import shutil
import time

import PySide2
import pandas as pd
from PySide2.QtGui import QPixmap, Qt, QMovie
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog, QLineEdit, QRadioButton

from configurator import Configurator

dirname = os.path.dirname(PySide2.__file__)
qt_plugin_path = os.path.join(dirname, 'Qt', 'plugins')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path


class ImageAnnotator:
    def __init__(self, configurator=None):
        self.ui = QUiLoader().load('ui/main.ui')
        self.user_config_file = 'user-config.yml'
        self.user_config_name = 'using conf'
        if configurator:
            self.configurator = configurator
        else:
            self.configurator = Configurator(self.user_config_file, self.user_config_name)

        # main ui handle
        # menu bar
        # QApplication.processEvents()
        self.ui.open_dir_act.triggered.connect(self.open_dir)
        self.ui.open_files_act.triggered.connect(self.open_files)
        self.ui.open_dir_adv_act.triggered.connect(self.open_files)
        self.ui.import_file_list_act.triggered.connect(self.popup_message_box)
        self.ui.export_file_list_act.triggered.connect(self.popup_message_box)
        self.ui.clear_file_list_act.triggered.connect(self.clear_file_list)
        self.ui.export_tagging_results_act.triggered.connect(self.export_tagging_results)
        self.ui.preferences_act.triggered.connect(self.show_preferences)
        # menu edit
        # self.ui.edit_menu.exec_()
        self.ui.undo_act.triggered.connect(self.undo_op)
        self.ui.redo_act.triggered.connect(self.redo_op)
        # self.ui.skip_act.triggered.connect(self.undo_processing_op)
        self.ui.delete_act.triggered.connect(self.popup_message_box)
        self.ui.add_tag_act.triggered.connect(self.add_tag)
        self.ui.remove_tag_act.triggered.connect(self.remove_tag)
        self.ui.rename_tag_act.triggered.connect(self.rename_tag)

        self.ui.refresh_act.triggered.connect(self.refresh)

        self.ui.processing_mode_btn.clicked.connect(self.change_processing_mode)
        self.ui.tag_btn_group.buttonClicked.connect(self.choose_img_tag)
        self.ui.undo_btn.clicked.connect(self.undo_op)
        self.ui.redo_btn.clicked.connect(self.redo_op)

        # preferences ui handle
        self.configurator.preferences_ui.dialog_btn_box.accepted.connect(self.confirm_settings)

        self.prev_op_src_path = ''
        self.file_paths = []
        self.idx_curr_file = 0
        self.ui.img_show_label.setText(" ")

        self.undo_op_stack = []
        self.redo_op_stack = []
        self.tag_dir_dict = dict()

        self.infos_dict = {
            'fd_info': '',
            'processed_info': ''
        }
        self.configurator.using_conf_changed_dict['tags set'] = True
        self.get_and_set_ui()
        self.configurator.using_conf_changed_dict['tags set'] = False

    def confirm_settings(self):
        self.configurator.using_conf_dict = self.configurator.tmp_conf_dict.copy()
        self.get_and_set_ui()
        self.save_settings()

    def save_settings(self):
        self.configurator.save_conf_file(self.configurator.using_conf_dict, self.user_config_name,
                                         self.user_config_file)

    def get_and_set_ui(self):
        self.ui.processing_mode_btn.setText(self.configurator.using_conf_dict['default processing mode'])
        if self.configurator.using_conf_changed_dict['tags set']:
            [tag_btn.deleteLater() for tag_btn in self.ui.tag_btn_group.buttons()[2:]]
            for tag_name in self.configurator.using_conf_dict['tags set']:
                self.add_tag_btn_with_dir(tag_name)

    def add_tag_btn_with_dir(self, tag_name):
        tag_btn = QRadioButton(tag_name)
        self.ui.tag_btn_group.addButton(tag_btn)
        self.ui.tag_hlayout.addWidget(tag_btn)
        if self.configurator.using_conf_dict['default processing mode'] != "Tag Only":
            self.tag_dir_dict[tag_name] = self.configurator.using_conf_dict[
                                              'root for tagging results'] + "/" + tag_name
            if not os.path.exists(self.tag_dir_dict[tag_name]):
                os.makedirs(self.tag_dir_dict[tag_name])

    def show_preferences(self):
        self.configurator.get_and_set_ui(self.configurator.using_conf_dict)
        self.configurator.preferences_ui.show()

    def add_tag(self):
        tag_name, ok = QInputDialog.getText(self.ui, "Add tag", "Tag name:", QLineEdit.Normal,
                                            'Tag' + str(len(self.ui.tag_btn_group.buttons()) - 2))
        if ok and tag_name:
            if tag_name not in self.configurator.using_conf_dict['tags set']:
                self.add_tag_btn_with_dir(tag_name)
                self.configurator.using_conf_dict['tags set'].append(tag_name)

    def remove_tag(self):
        self.edit_tag("Remove")

    def rename_tag(self):
        self.edit_tag("Rename")
        print(self.tag_dir_dict)

    def edit_tag(self, mode):
        tags = [btn.text() for btn in self.ui.tag_btn_group.buttons()[2:]]
        if mode == "Remove":
            tags.append("[All tags]")
        else:
            tags.append("")
        selected_tag_name, ok = QInputDialog.getItem(self.ui, mode + " tag", "Select tag:", tags, 0, False)
        if ok and selected_tag_name:
            if mode == "Remove":
                if selected_tag_name != "[All tags]":
                    self.ui.tag_btn_group.buttons()[tags.index(selected_tag_name) + 2].deleteLater()
                    self.tag_dir_dict.pop(selected_tag_name)
                    self.configurator.using_conf_dict['tags set'].pop(
                        self.configurator.using_conf_dict['tags set'].index(selected_tag_name))
                else:
                    [tag_btn.deleteLater() for tag_btn in self.ui.tag_btn_group.buttons()[2:]]
                    self.configurator.using_conf_dict['tags set'].clear()
            else:
                tag_name, ok = QInputDialog.getText(self.ui, "Rename tag", "New tag name:", QLineEdit.Normal,
                                                    selected_tag_name)
                if ok and tag_name:
                    self.configurator.using_conf_dict['tags set'].pop(
                        self.configurator.using_conf_dict['tags set'].index(selected_tag_name))
                    self.ui.tag_btn_group.buttons()[tags.index(selected_tag_name) + 2].setText(tag_name)
                    self.tag_dir_dict[tag_name] = self.configurator.using_conf_dict[
                                                      'root for tagging results'] + "/" + tag_name

                    self.configurator.using_conf_dict['tags set'].append(tag_name)
                    if not os.path.exists(self.tag_dir_dict[tag_name]):
                        os.makedirs(self.tag_dir_dict[tag_name])

        # self.ui.tag_btn_group.removeButton()

    def open_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self.ui,
                                                    "Select one dir to open to get files. (Without subdirectory files)",
                                                    self.configurator.using_conf_dict['root for file dialog init open'])
        if dir_path == '':
            self.infos_dict['fd_info'] = "No dir selected"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        else:
            files = os.listdir(dir_path)
            for f in files:
                file_path = dir_path + '/' + f
                if file_path not in self.file_paths[self.idx_curr_file:]:
                    # 当前考虑：已读文件夹1，读取文件夹2
                    # （有若干图片重合），如果不去重后面，
                    # 在对某个重合图片进行操作后，再次指向该图片时将报错
                    self.file_paths.append(file_path)
            print("files: ", len(self.file_paths))
            self.img_viewer()

    def open_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self.ui,
                                                     "Select one or more files to open",
                                                     self.configurator.using_conf_dict[
                                                         'root for file dialog init open'], "*")
        if not file_paths:
            self.infos_dict['fd_info'] = "No files selected"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        else:
            print(self.idx_curr_file, len(self.file_paths))
            # self.file_paths.extend(file_paths)
            for file_path in file_paths:
                if file_path not in self.file_paths[self.idx_curr_file:]:
                    self.file_paths.append(file_path)
            print("files: ", len(self.file_paths))
            self.img_viewer()

    def open_dir_adv(self):
        dir_path = QFileDialog.getExistingDirectory(self.ui,
                                                    "Select one dir to open to get all files, include all "
                                                    "subdirectory files",
                                                    self.configurator.using_conf_dict['root for file dialog init open'])
        if dir_path == '':
            self.infos_dict['fd_info'] = "No dir selected"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        else:
            fd_tree = os.walk(dir_path)
            for path, dirs, files in fd_tree:
                for file in files:
                    file_path = os.path.join(path, file)
                    if file_path not in self.file_paths[self.idx_curr_file:]:
                        self.file_paths.append(file_path)
            print("files: ", len(self.file_paths))
            print(self.file_paths)
            self.img_viewer()

    def export_tagging_results(self):
        log_dir = self.configurator.using_conf_dict['root for tagging results'] + "/logs/"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path, _ = QFileDialog.getSaveFileName(self.ui, "Save tagging result log",
                                                  log_dir + "/image-annotation-log-" + time.strftime(
                                                      "%y%m%d-%H%M%S") + ".csv",
                                                  "Files (*.txt *.csv)")
        if log_path != '':
            self.infos_dict['fd_info'] = "Log saved at " + log_path
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
            QApplication.processEvents()
            df_tagging_results = pd.DataFrame(self.undo_op_stack,
                                              columns=['Source Path', 'Tag', 'Tagging Result Path',
                                                       'Processing Mode'])
            df_tagging_results.to_csv(log_path, index=False)

    def img_viewer(self, undo_op=False):
        if self.idx_curr_file >= len(self.file_paths) or len(self.file_paths) == 0:
            self.infos_dict['fd_info'] = "No img"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
            self.ui.img_show_label.setText(" ")
        else:
            while self.idx_curr_file < len(self.file_paths):
                QApplication.processEvents()
                img_path = self.file_paths[self.idx_curr_file]
                if img_path.endswith(".gif"):
                    movie = QMovie(img_path)
                    self.ui.img_show_label.setMovie(movie)
                    movie.start()
                    self.infos_dict['fd_info'] = "%d/%d: %s" % (
                        self.idx_curr_file, len(self.file_paths), self.file_paths[self.idx_curr_file])
                    self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
                    break
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    self.ui.img_show_label.setPixmap(pixmap.scaled(600, 600, aspectMode=Qt.KeepAspectRatio))
                    # QApplication.processEvents()
                    self.infos_dict['fd_info'] = "%d/%d: %s" % (
                        self.idx_curr_file, len(self.file_paths), self.file_paths[self.idx_curr_file])
                    self.ui.status_bar.showMessage(self.infos_dict['fd_info'])

                    break
                elif not undo_op:
                    self.idx_curr_file = self.idx_curr_file + 1
                else:
                    self.idx_curr_file = self.idx_curr_file - 1
                    if self.idx_curr_file < 0:
                        self.idx_curr_file = 0
                        break

    def choose_img_tag(self):
        num_files = len(self.file_paths)
        if self.idx_curr_file < num_files and num_files > 0:
            curr_tag_btn = self.ui.tag_btn_group.checkedButton()
            curr_tag_btn.setChecked(False)
            if curr_tag_btn is not None:
                curr_img_tag = curr_tag_btn.text()
                self.processing_img_to_tag_dir(self.file_paths[self.idx_curr_file], curr_img_tag)
                self.idx_curr_file = self.idx_curr_file + 1
                self.redo_op_stack.clear()
                self.img_viewer()
                print("- Redo num ", len(self.redo_op_stack))
                print("- Undo num ", len(self.undo_op_stack))

    def change_processing_mode(self):
        QApplication.processEvents()
        if self.ui.processing_mode_btn.text() == "Tag Only":
            self.ui.processing_mode_btn.setText("Move")
        elif self.ui.processing_mode_btn.text() == "Move":
            self.ui.processing_mode_btn.setText("Copy")
        else:
            self.ui.processing_mode_btn.setText("Tag Only")

    def processing_img_to_tag_dir(self, img_path, img_tag):
        processing_mode = self.ui.processing_mode_btn.text()
        if (img_tag != "Skip" and processing_mode != "Tag Only") or img_tag == "Delete":
            if img_tag == 'Delete':
                processing_mode = "Delete"
            img_path = os.path.abspath(img_path)
            img_dst_path = os.path.abspath(self.tag_dir_dict[img_tag] + "/" + os.path.basename(img_path))
            if img_path != img_dst_path:
                while os.path.exists(img_dst_path):
                    filename, extname = os.path.splitext(os.path.basename(img_path))
                    img_dst_path = self.tag_dir_dict[img_tag] + "/" + filename + "-rn" + time.strftime(
                        "%M%S") + extname
                if processing_mode != "Copy":  # = Move or Delete
                    shutil.move(img_path, img_dst_path)
                else:
                    shutil.copy2(img_path, img_dst_path)
                self.infos_dict['processed_info'] = "Ok. " + processing_mode + ": " + img_path + " -> " + \
                                                    img_dst_path
                self.undo_op_stack.append([img_path, img_tag, img_dst_path, processing_mode])
            else:
                self.infos_dict[
                    'processed_info'] = "Skip no changed file. " + processing_mode + ": " + img_path
                self.undo_op_stack.append([img_path, '', '', "Skip"])
        elif img_tag != "Skip" and processing_mode == "Tag Only":
            self.infos_dict[
                'processed_info'] = "Ok. " + processing_mode + ": " + img_path + " =tag=> " + img_tag
            self.undo_op_stack.append([img_path, img_tag, img_path, processing_mode])
        else:
            self.undo_op_stack.append([img_path, '', '', "Skip"])
            self.infos_dict['processed_info'] = "Ok. " + img_tag + ": " + img_path
        self.ui.processed_info_label.setText(self.infos_dict['processed_info'])

    def undo_op(self):
        self.undo_redo_processing_op("Undo")
        print("-> Undo num ", len(self.undo_op_stack))
        print("Redo num ", len(self.redo_op_stack))

    def redo_op(self):
        self.undo_redo_processing_op("Redo")
        print("-> Redo num ", len(self.redo_op_stack))
        print("Undo num ", len(self.undo_op_stack))

    def undo_redo_processing_op(self, mode):
        QApplication.processEvents()
        if mode == "Undo":
            curr_op_stack = self.undo_op_stack
            left_op_stack = self.redo_op_stack
        else:
            curr_op_stack = self.redo_op_stack
            left_op_stack = self.undo_op_stack

        if len(curr_op_stack) > 0:
            prev_op_src_path, prev_img_tag, prev_op_tagging_result, prev_processing_mode = curr_op_stack.pop()
            if mode == "Undo":
                self.prev_op_src_path = prev_op_src_path
            left_op_stack.append([prev_op_tagging_result, prev_img_tag, prev_op_src_path, prev_processing_mode])
            self.infos_dict[
                'processed_info'] = mode + " " + prev_processing_mode + ": " + prev_op_tagging_result + " -> " + prev_op_src_path
            if prev_processing_mode == "Skip":
                if mode == "Redo":
                    prev_op_src_path = prev_op_tagging_result
                self.infos_dict[
                    'processed_info'] = mode + " " + prev_processing_mode + ": " + prev_op_src_path
            elif prev_processing_mode == "Move":
                shutil.move(prev_op_tagging_result, prev_op_src_path)
            elif prev_processing_mode == "Copy":  # Copy
                if mode == "Undo":
                    os.remove(prev_op_tagging_result)
                else:
                    shutil.copy2(prev_op_tagging_result, prev_op_src_path)
            else:  # Tag Only
                self.infos_dict[
                    'processed_info'] = mode + " " + prev_processing_mode + ": " + prev_op_src_path + " =tag=> " + prev_img_tag

            self.ui.processed_info_label.setText(self.infos_dict['processed_info'])

            if mode == "Undo":
                if self.idx_curr_file > 0:
                    self.idx_curr_file = self.idx_curr_file - 1
                self.img_viewer(undo_op=True)
                if len(self.file_paths) == 0:
                    self.img_show(self.prev_op_src_path)
            else:
                self.idx_curr_file = self.idx_curr_file + 1
                self.img_viewer()
        else:
            self.infos_dict['processed_info'] = "Nothing " + mode
            self.ui.processed_info_label.setText(self.infos_dict['processed_info'])

    def refresh(self):
        QApplication.processEvents()
        # self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        self.ui.processed_info_label.setText(self.infos_dict['processed_info'])
        if self.idx_curr_file >= 0:
            self.img_viewer()
        else:
            self.img_show(self.prev_op_src_path)

    def clear_file_list(self):
        self.file_paths = []
        self.idx_curr_file = 0
        self.refresh()

    def img_show(self, img_path):
        QApplication.processEvents()
        pixmap = QPixmap(img_path)
        self.ui.img_show_label.setPixmap(
            pixmap.scaled(self.configurator.using_conf_dict['image default display size'][1],
                          self.configurator.using_conf_dict['image default display size'][0],
                          aspectMode=Qt.KeepAspectRatio))

    def popup_message_box(self):
        QMessageBox.about(
            self.ui,
            'Tip',
            '待完成')


if __name__ == '__main__':
    app = QApplication([])
    image_annotator = ImageAnnotator()
    image_annotator.ui.show()
    app.exec_()
    image_annotator.save_settings()
