# Image Annotator

An image annotation tool with GUI.

## Getting Started
```shell script
python image_annotator.py
```



## Bulid your own APP
1. Make a `.qrc` file to define your resources in the app Python files. Like `main.qrc`.
2. Use `pyside2-rcc` to generate a Python binary file from the `.qrc` file. Like:
    ```shell script
    pyside2-rcc -o main_rc.py main.qrc # like this
    ``` 
3. Use `pyinstaller` to packages the app to Win EXE or Mac APP...
    ```shell script
    pyinstaller build_win_app.spec --upx-dir="UPX_DIR_PATH"
    ```
