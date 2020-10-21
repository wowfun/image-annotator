import os
import shutil
import time
from PIL import Image, ExifTags
# import multiprocessing
# import main_ui

# for some cases
import PySide2
from PySide2.QtGui import QPixmap, Qt, QMovie, QIcon, QTransform
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog, QLineEdit, QRadioButton

from configurator import Configurator
import main_rc

dirname = os.path.dirname(PySide2.__file__)
qt_plugin_path = os.path.join(dirname, 'Qt', 'plugins')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path


# TODO: 自动保存操作日志（含设置项）; 显示文件列表; 对话路径记忆;


class ImageAnnotator:
    def __init__(self, configurator=None):
        self.about_dict = {
            "version": "6.1.3",
            "source": "https://github.com/wowfun/image-annotator",
            "author": "Sinputer"
        }
        self.ui = QUiLoader().load('ui/main.ui')
        # self.ui=main_ui.Ui_MainWindow.setupUi()
        self.user_config_file = 'user-config.yml'
        self.user_config_name = 'using conf'
        if configurator:
            self.configurator = configurator
        else:
            self.configurator = Configurator(self.user_config_file, self.user_config_name)

        self.setup_ui_add_icons()

        # main ui handle
        # menu bar
        self.ui.open_dir_act.triggered.connect(self.open_dir)
        self.ui.open_dir_adv_act.triggered.connect(self.open_dir_adv)
        self.ui.open_files_act.triggered.connect(self.open_files)
        self.ui.import_file_list_act.triggered.connect(self.import_file_list)
        self.ui.export_file_list_act.triggered.connect(self.export_file_list)
        self.ui.clear_file_list_act.triggered.connect(self.clear_file_list)
        self.ui.save_tagging_results_act.triggered.connect(self.save_tagging_results)
        self.ui.preferences_act.triggered.connect(self.show_preferences)
        # menu edit
        self.ui.undo_act.triggered.connect(self.undo_op)
        self.ui.redo_act.triggered.connect(self.redo_op)
        self.ui.skip_act.triggered.connect(self.skip_act_handler)
        self.ui.delete_act.triggered.connect(self.delete_act_handler)
        self.ui.rotate_right_act.triggered.connect(self.rotate_right)
        self.ui.rotate_left_act.triggered.connect(self.rotate_left)
        self.ui.add_tag_act.triggered.connect(self.add_tag)
        self.ui.remove_tag_act.triggered.connect(self.remove_tag)
        self.ui.rename_tag_act.triggered.connect(self.rename_tag)

        self.ui.refresh_act.triggered.connect(self.refresh)

        self.ui.processing_mode_btn.clicked.connect(self.change_processing_mode)
        self.ui.tag_btn_group.buttonClicked.connect(self.choose_img_tag)
        self.ui.undo_btn.clicked.connect(self.undo_op)
        self.ui.redo_btn.clicked.connect(self.redo_op)

        # help
        self.ui.about_act.triggered.connect(self.show_about)

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

    def show_about(self):
        msg="Version: v"+self.about_dict['version']+"\nSource: "+self.about_dict['source']+"\nAuthor: "+self.about_dict['author']
        QMessageBox.about(self.ui, "About", msg)

    def rotate_right(self):
        self.image_processing("Right", self.file_paths[self.idx_curr_file])
        self.img_viewer()

    def rotate_left(self):
        self.image_processing("Left", self.file_paths[self.idx_curr_file])
        self.img_viewer()

    def image_processing(self, mode, img_path):
        try:
            image = Image.open(img_path)
            if mode == "Right":
                image = image.rotate(270, expand=True)
            elif mode == "Left":
                image = image.rotate(90, expand=True)
            image.save(img_path)
            image.close()
        except Exception:
            pass

    def save_tagging_results(self):
        save_dir = self.configurator.using_conf_dict['root for tagging results'] + "/logs/"
        dialog_title = "Save tagging result log"
        save_init_path = save_dir + "/image-annotation-log-" + time.strftime(
            "%y%m%d-%H%M%S") + ".csv"
        file_filter = "Files (*.txt *.csv)"
        save_path = self.get_save_path(save_dir, dialog_title, save_init_path, file_filter)
        if save_path != '':
            self.infos_dict['fd_info'] = "Tagging result log saved at " + save_path
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
            QApplication.processEvents()
            with open(save_path, 'w') as f:
                f.write('Tagging Result Path,\t\t' + 'Tag,\t\t' + 'Source Path,\t\t' +
                        'Processing Mode\n')
                for source_path, tag, tagging_result_path, processing_mode in self.undo_op_stack:
                    f.write(
                        tagging_result_path + ',\t\t' + tag + ',\t\t' + source_path + ',\t\t' + processing_mode + '\n')

    def get_save_path(self, save_dir, dialog_title, save_init_path, file_filter):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path, _ = QFileDialog.getSaveFileName(self.ui, dialog_title, save_init_path, file_filter)
        return save_path

    def import_file_list(self):
        file_path, _ = QFileDialog.getOpenFileName(self.ui,
                                                   "Select file with file list",
                                                   self.configurator.using_conf_dict[
                                                       'root for tagging results'], "Files (*.txt *.csv)")
        if file_path == '':
            self.infos_dict['fd_info'] = "No file selected"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        else:
            with open(file_path, 'r') as f:
                for line in f.readlines():
                    if line.strip('\n'):
                        self.file_paths.append(line.strip('\n'))
            print(self.file_paths)

    def export_file_list(self):
        save_dir = self.configurator.using_conf_dict['root for tagging results'] + "/logs/"
        dialog_title = "Export file list (contain ALL TYPES of files)"
        save_init_path = save_dir + "/file-list-" + time.strftime(
            "%y%m%d-%H%M%S") + ".csv"
        file_filter = "Files (*.txt *.csv)"
        save_path = self.get_save_path(save_dir, dialog_title, save_init_path, file_filter)
        if save_path != '':
            self.infos_dict['fd_info'] = "File list saved at " + save_path
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
            QApplication.processEvents()
            with open(save_path, 'w') as f:
                for fp in self.file_paths:
                    f.write(fp + '\n')

    def setup_ui_add_icons(self):
        self.ui.setWindowIcon(QIcon(":/icons/resources/images/app-128.png"))
        self.configurator.preferences_ui.setWindowIcon(QIcon(":/icons/resources/images/settings-16.png"))
        self.ui.open_dir_act.setIcon(QIcon(":/icons/resources/images/open-dir-16.png"))
        self.ui.open_dir_adv_act.setIcon(QIcon(":/icons/resources/images/open-dir-adv-16.png"))
        self.ui.open_files_act.setIcon(QIcon(":/icons/resources/images/open-files-16.png"))
        self.ui.clear_file_list_act.setIcon(QIcon(":/icons/resources/images/clear-file-list-16.png"))
        self.ui.save_tagging_results_act.setIcon(QIcon(":/icons/resources/images/save-tagging-results-16.png"))
        self.ui.add_tag_act.setIcon(QIcon(":/icons/resources/images/add-tag-16.png"))
        self.ui.remove_tag_act.setIcon(QIcon(":/icons/resources/images/remove-tag-16.png"))
        self.ui.rename_tag_act.setIcon(QIcon(":/icons/resources/images/rename-tag-16.png"))
        self.ui.preferences_act.setIcon(QIcon(":/icons/resources/images/settings-16.png"))
        self.ui.refresh_act.setIcon(QIcon(":/icons/resources/images/refresh-16.png"))
        self.ui.skip_act.setIcon(QIcon(":/icons/resources/images/skip-16.png"))
        self.ui.delete_act.setIcon(QIcon(":/icons/resources/images/delete-16.png"))
        self.ui.undo_act.setIcon(QIcon(":/icons/resources/images/undo-16.png"))
        self.ui.redo_act.setIcon(QIcon(":/icons/resources/images/redo-16.png"))
        self.ui.rotate_left_act.setIcon(QIcon(":/icons/resources/images/rotate-left-16.png"))
        self.ui.rotate_right_act.setIcon(QIcon(":/icons/resources/images/rotate-right-16.png"))

    def confirm_settings(self):
        self.configurator.using_conf_dict = self.configurator.tmp_conf_dict.copy()
        self.get_and_set_ui()
        self.save_settings()

    def save_settings(self):
        self.configurator.save_conf_file(self.configurator.using_conf_dict, self.user_config_name,
                                         self.user_config_file)

    def get_and_set_ui(self):
        self.tag_dir_dict.clear()
        self.tag_dir_dict['Delete'] = self.configurator.using_conf_dict[
                                          'root for tagging results'] + "/Delete"
        if not os.path.exists(self.tag_dir_dict['Delete']):
            os.makedirs(self.tag_dir_dict['Delete'])
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
                    try:
                        image = Image.open(img_path)
                        rotated_flag = False
                        angle = 0
                        for orientation in ExifTags.TAGS.keys():
                            if ExifTags.TAGS[orientation] == 'Orientation':
                                break
                        exif = dict(image._getexif().items())
                        print(img_path, " exif: ", exif[orientation])
                        if exif[orientation] == 3:
                            angle = 180
                            rotated_flag = True
                        elif exif[orientation] == 6:
                            angle = 270
                            rotated_flag = True
                        elif exif[orientation] == 8:
                            angle = 90
                            rotated_flag = True
                        if rotated_flag:
                            pixmap = pixmap.transformed(QTransform().rotate(-angle))
                            image = image.rotate(angle, expand=True)
                            image.save(img_path)
                            image.close()
                    except (AttributeError, KeyError, IndexError):
                        # cases: image don't have getexif
                        pass

                    max_h = self.ui.img_show_label.height()
                    max_w = self.ui.img_show_label.width()
                    if max_h > self.configurator.using_conf_dict['image default display size'][0]:
                        max_h = self.configurator.using_conf_dict['image default display size'][0]
                    if max_w > self.configurator.using_conf_dict['image default display size'][1]:
                        max_w = self.configurator.using_conf_dict['image default display size'][1]
                    self.ui.img_show_label.setPixmap(
                        pixmap.scaled(max_w,
                                      max_h,
                                      aspectMode=Qt.KeepAspectRatio))
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

    def delete_act_handler(self):
        self.ui.delete_btn.setChecked(True)
        self.choose_img_tag()

    def skip_act_handler(self):
        self.ui.skip_btn.setChecked(True)
        self.choose_img_tag()

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
            elif prev_processing_mode == "Move" or prev_processing_mode == 'Delete':
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


if __name__ == '__main__':
    # multiprocessing.freeze_support()
    app = QApplication([])
    image_annotator = ImageAnnotator()
    image_annotator.ui.show()
    app.exec_()
    image_annotator.save_settings()
