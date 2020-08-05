import os
import time
import shutil

os.environ[
    'QT_QPA_PLATFORM_PLUGIN_PATH'] = '/Users/kevin/opt/anaconda3/envs/ml/lib/python3.7/site-packages/PySide2/Qt/plugins'
from PySide2.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox
from PySide2.QtGui import QPixmap, Qt, QCursor
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QEventLoop


class ImageAnnotator:
    def __init__(self):
        self.ui = QUiLoader().load('ui/main.ui')
        self.src_root_dir = "./test_imgs/"
        self.dst_root_dir = "./test_imgs/"

        self.file_paths = []
        self.idx_curr_file = 0
        self.ui.img_show_label.setText(" ")
        self.img_size = [600, 600]  # h, w

        self.processing_op_stack = []
        self.type_dir_dict = dict()
        for type_btn in self.ui.type_btn_group.buttons():
            type_name = type_btn.text()
            if type_name == "Skip":
                continue
            self.type_dir_dict[type_name] = self.dst_root_dir + "/" + type_btn.text()
            if not os.path.exists(self.type_dir_dict[type_name]):
                os.makedirs(self.type_dir_dict[type_name])
        self.infos_dict = {
            'fd_info': '',
            'processed_info': ''
        }

        # menu bar
        # QApplication.processEvents()
        self.ui.open_dir_act.triggered.connect(self.open_dir)
        self.ui.open_files_act.triggered.connect(self.open_files)
        self.ui.open_dir_adv_act.triggered.connect(self.open_files)
        self.ui.import_file_list_act.triggered.connect(self.popup_message_box)
        self.ui.export_file_list_act.triggered.connect(self.popup_message_box)
        self.ui.clear_file_list_act.triggered.connect(self.clear_file_list)
        self.ui.export_log_act.triggered.connect(self.export_log)
        # menu edit
        # self.ui.edit_menu.exec_()
        self.ui.undo_act.triggered.connect(self.undo_processing_op)
        self.ui.redo_act.triggered.connect(self.popup_message_box)
        self.ui.skip_act.triggered.connect(self.undo_processing_op)
        self.ui.delete_act.triggered.connect(self.popup_message_box)
        self.ui.add_tag_act.triggered.connect(self.popup_message_box)
        self.ui.remove_tag_act.triggered.connect(self.popup_message_box)
        self.ui.rename_tag_act.triggered.connect(self.popup_message_box)

        # self.ui.view_menu.exec_()
        self.ui.refresh_act.triggered.connect(self.refresh)
        # self.ui.window_menu.exec_()
        # self.ui.help_menu.exec_()

        self.ui.processing_mode_btn.setText("Move")
        self.ui.processing_mode_btn.clicked.connect(self.change_processing_mode)
        self.ui.type_btn_group.buttonClicked.connect(self.choose_img_type)
        self.ui.undo_btn.clicked.connect(self.undo_processing_op)


        self.prev_op_src_path = ''


    def popup_message_box(self):
        QMessageBox.about(
            self.ui,
            'Tip',
            '待完成')


    def open_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self.ui,
                                                    "Select one dir to open to get files. (Without subdirectory files)",
                                                    self.src_root_dir)
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
                                                     self.src_root_dir, "*")
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
                                                    self.src_root_dir)
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

    def export_log(self):
        log_dir = self.dst_root_dir + "/logs/"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path, _ = QFileDialog.getSaveFileName(self.ui, "Save Log",
                                                  log_dir + "/image-annotation-log-" + time.strftime(
                                                      "%y%m%d-%H%M%S") + ".txt",
                                                  "Files (*.txt *.log *.csv)")
        self.infos_dict['fd_info'] = "Log saved at " + log_path
        self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
        QApplication.processEvents()
        with open(log_path, 'w') as f:
            for processing_mode, prev_op_src_path, prev_op_dst_path in self.processing_op_stack:
                if processing_mode == "Skip":
                    continue
                line = processing_mode + ":  " + prev_op_dst_path + "\t\t -> \t\t" + prev_op_src_path + "\n"
                f.write(line)

    def img_viewer(self, undo_op=False):
        if self.idx_curr_file >= len(self.file_paths) or len(self.file_paths) == 0:
            self.infos_dict['fd_info'] = "No img"
            self.ui.status_bar.showMessage(self.infos_dict['fd_info'])
            self.ui.img_show_label.setText(" ")
        else:
            while self.idx_curr_file < len(self.file_paths):
                QApplication.processEvents()
                pixmap = QPixmap(self.file_paths[self.idx_curr_file])
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

    def choose_img_type(self):
        num_files = len(self.file_paths)
        if self.idx_curr_file < num_files and num_files > 0:
            curr_type_btn = self.ui.type_btn_group.checkedButton()
            curr_type_btn.setChecked(False)
            if curr_type_btn is not None:
                curr_img_type = curr_type_btn.text()
                self.processing_img_to_type_dir(self.file_paths[self.idx_curr_file], curr_img_type)
                self.idx_curr_file = self.idx_curr_file + 1
                self.img_viewer()

    def change_processing_mode(self):
        QApplication.processEvents()
        if self.ui.processing_mode_btn.text() == "Move":
            self.ui.processing_mode_btn.setText("Copy")
        else:
            self.ui.processing_mode_btn.setText("Move")

    def processing_img_to_type_dir(self, img_path, img_type):
        if img_type != "Skip":
            if img_type != 'Delete':
                processing_mode = self.ui.processing_mode_btn.text()
            else:
                processing_mode = "Delete"

            img_path = os.path.abspath(img_path)
            img_dst_path = os.path.abspath(self.type_dir_dict[img_type] + "/" + os.path.basename(img_path))
            if img_path != img_dst_path:
                while os.path.exists(img_dst_path):
                    filename, extname = os.path.splitext(os.path.basename(img_path))
                    img_dst_path = self.type_dir_dict[img_type] + "/" + filename + "-rn" + time.strftime(
                        "%M%S") + extname
                if processing_mode != "Copy":  # = Move or Delete
                    shutil.move(img_path, img_dst_path)
                else:
                    shutil.copy2(img_path, img_dst_path)
                self.infos_dict['processed_info'] = "Ok. " + processing_mode + ": " + img_path + " -> " + img_dst_path
                self.processing_op_stack.append([processing_mode, img_path, img_dst_path])
            else:
                self.infos_dict[
                    'processed_info'] = "Skip no changed file. " + processing_mode + ": " + img_path
                self.processing_op_stack.append(["Skip", img_path, None])
        else:
            self.processing_op_stack.append(["Skip", img_path, None])
            self.infos_dict['processed_info'] = "Ok. " + img_type + ": " + img_path
        self.ui.processed_info_label.setText(self.infos_dict['processed_info'])

    def undo_processing_op(self):
        QApplication.processEvents()
        if len(self.processing_op_stack) > 0:
            processing_mode, self.prev_op_src_path, prev_op_dst_path = self.processing_op_stack.pop()
            self.infos_dict[
                'processed_info'] = "Undo " + processing_mode + ": " + prev_op_dst_path + " -> " + self.prev_op_src_path
            if processing_mode == "Skip":
                self.infos_dict[
                    'processed_info'] = "Undo " + processing_mode + ": " + self.prev_op_src_path
            elif processing_mode != "Copy":
                shutil.move(prev_op_dst_path, self.prev_op_src_path)
            else:
                os.remove(prev_op_dst_path)

            self.ui.processed_info_label.setText(self.infos_dict['processed_info'])
            if self.idx_curr_file > 0:
                self.idx_curr_file = self.idx_curr_file - 1
            self.img_viewer(undo_op=True)
            if len(self.file_paths) == 0:
                self.img_show(self.prev_op_src_path)
        else:
            self.infos_dict['processed_info'] = "Nothing Undo."
            self.ui.processed_info_label.setText(self.infos_dict['processed_info'])
            self.ui.img_show_label.setText(" ")

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
            pixmap.scaled(self.img_size[1], self.img_size[0], aspectMode=Qt.KeepAspectRatio))


app = QApplication([])
image_annotator = ImageAnnotator()
image_annotator.ui.show()
app.exec_()
