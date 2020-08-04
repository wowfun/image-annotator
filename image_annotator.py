# idea
# 每组图片若干个，每个图片下面有标签选项；下一组


import os
import time
import shutil

from IPython.core.inputtransformer import tr

os.environ[
    'QT_QPA_PLATFORM_PLUGIN_PATH'] = '/Users/kevin/opt/anaconda3/envs/ml/lib/python3.7/site-packages/PySide2/Qt/plugins'
from PySide2.QtWidgets import QApplication, QFileDialog
from PySide2.QtGui import QPixmap, Qt
from PySide2.QtUiTools import QUiLoader


class ImageAnnotator:
    def __init__(self):
        self.ui = QUiLoader().load('ui/main.ui')
        self.dst_root_dir = "./test_imgs/"
        self.init_or_reset_state()
        self.processing_op_stack = []

        self.type_dir_dict = dict()
        for type_btn in self.ui.type_btn_group.buttons():
            type_name = type_btn.text()
            self.type_dir_dict[type_name] = self.dst_root_dir + "/" + type_btn.text()

            if not os.path.exists(self.type_dir_dict[type_name]):
                os.makedirs(self.type_dir_dict[type_name])

        self.ui.processing_mode_btn.clicked.connect(self.change_processing_mode)
        self.ui.open_dir_btn.clicked.connect(self.open_dir)
        self.ui.open_files_btn.clicked.connect(self.open_files)
        self.ui.type_btn_group.buttonClicked.connect(self.choose_img_type)
        self.ui.undo_btn.clicked.connect(self.undo_processing_op)

    def init_or_reset_state(self):
        self.files = []
        self.dir_path = ''
        self.idx_curr_file = 0
        self.ui.img_show_label.setText(" ")

    def open_dir(self):
        self.dir_path = QFileDialog.getExistingDirectory(self.ui, "Select one dir to open", './test_imgs')
        if self.dir_path == '':
            self.ui.fd_info_label.setText("No dir selected")
            self.init_or_reset_state()
        else:
            self.files = os.listdir(self.dir_path)
            print(self.files)
            self.idx_curr_file = 0
            self.img_viewer()

    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.ui,
                                                "Select one or more files to open",
                                                ".", "*")
        if files == []:
            self.ui.fd_info_label.setText("No files selected")
            self.init_or_reset_state()
        else:
            self.files = files
            self.ui.fd_info_label.setText("%s : %d/%d %s" % (self.dir_path ,self.idx_curr_file,len(self.files),self.files[self.idx_curr_file]))
            self.img_viewer()

    def img_viewer(self,undo_op=False):
        QApplication.processEvents()
        if self.idx_curr_file >= len(self.files) or len(self.files) == 0:
            self.ui.fd_info_label.setText("No img")
            self.ui.img_show_label.setText(" ")
        else:
            while self.idx_curr_file < len(self.files):
                curr_file_path = self.dir_path + '/' + self.files[self.idx_curr_file]
                # self.ui.img_show_label.setScaledContents(True)
                pixmap = QPixmap(curr_file_path)
                if not pixmap.isNull():
                    self.ui.img_show_label.setPixmap(pixmap.scaled(600, 600, aspectMode=Qt.KeepAspectRatio))
                    self.ui.fd_info_label.setText(
                        "%s : %d/%d %s" % (
                        self.dir_path, self.idx_curr_file, len(self.files), self.files[self.idx_curr_file]))
                    break
                elif not undo_op:
                    self.idx_curr_file = self.idx_curr_file + 1
                else:
                    self.idx_curr_file = self.idx_curr_file - 1




    def choose_img_type(self):
        QApplication.processEvents()
        if self.idx_curr_file < len(self.files):
            self.img_viewer()
            curr_type_btn = self.ui.type_btn_group.checkedButton()
            curr_type_btn.setChecked(False)
            if curr_type_btn is not None:
                curr_img_type = curr_type_btn.text()
                curr_file_path = self.dir_path + '/' + self.files[self.idx_curr_file]
                self.processing_img_to_type_dir(curr_file_path, curr_img_type)
                self.idx_curr_file = self.idx_curr_file + 1
                self.img_viewer()


    def change_processing_mode(self):
        if self.ui.processing_mode_btn.text() == "Move":
            self.ui.processing_mode_btn.setText("Copy")
        else:
            self.ui.processing_mode_btn.setText("Move")

    def processing_img_to_type_dir(self, img_path, img_type):
        QApplication.processEvents()

        img_dst_path = self.type_dir_dict[img_type] + "/" + os.path.basename(img_path)
        i = 0
        while os.path.exists(img_dst_path):
            filename, extname = os.path.splitext(os.path.basename(img_path))
            img_dst_path = self.type_dir_dict[img_type] + "/" + filename + "-rn" + str(i) + time.strftime(
                "%M%S") + extname
            i = i + 1
        processing_mode = self.ui.processing_mode_btn.text()
        self.img_viewer()
        if processing_mode == "Move":
            shutil.move(img_path, img_dst_path)  #
        else:
            shutil.copy2(img_path, img_dst_path)
        self.processing_op_stack.append([processing_mode, img_path, img_dst_path])

        self.ui.processed_info_label.setText(
            "Ok. " + self.ui.processing_mode_btn.text() + ": " + img_path + " -> " + img_dst_path)


    def undo_processing_op(self):
        QApplication.processEvents()
        if len(self.processing_op_stack) > 0:
            processing_mode, prev_op_src_path, prev_op_dst_path = self.processing_op_stack.pop()
            if processing_mode == "Move":
                shutil.move(prev_op_dst_path, prev_op_src_path)  #
            else:
                os.remove(prev_op_dst_path)
            self.idx_curr_file = self.idx_curr_file - 1
            self.img_viewer(undo_op=True)
            self.ui.processed_info_label.setText(
                "Undo. " + processing_mode + ": " + prev_op_dst_path + " -> " + prev_op_src_path)
        else:
            self.ui.processed_info_label.setText(
                "Nothing Undo.")

app = QApplication([])
image_annotator = ImageAnnotator()
image_annotator.ui.show()
app.exec_()

'''
   dialog = QFileDialog()  # 生成文件对话框对象
        dialog.setFileMode(QFileDialog.Directory)  # 设置文件过滤器，这里是任何文件，包括目录
        dialog.setViewMode(QFileDialog.List)  # 设置显示文件的模式，这里是详细模式

        if dialog.exec_():
            fd_path = dialog.selectedFiles()
            if len(fd_path) == 1 and os.path.isdir(fd_path[0]):
                for f in os.listdir(fd_path[0]):
                    print(f)
            else:
                print(fd_path)





'''
