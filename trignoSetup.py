import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import shutil

def dialog(key):
    file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Select " + key + " File", "", "All Files (*);; License Files (*.lic)")
    if check:
        print(file)
        if key == "License":
            dest = "./config/license.lic"
        else:
            dest = "./config/key"
        shutil.copyfile(file, dest)


if __name__ == "__main__":

    setup = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    w.setGeometry(300,150,850,400)
    w.setWindowTitle("Configuration")

    licButton = QtWidgets.QPushButton(w)
    licButton.setText("Select License")
    licButton.setGeometry(100,100,300,100)
    licButton.clicked.connect(lambda: dialog("License"))
    # licButton.move(50,50)

    keyButton = QtWidgets.QPushButton(w)
    keyButton.setText("Select Key")
    keyButton.setGeometry(450,100,300,100)
    keyButton.clicked.connect(lambda: dialog("Key"))
    # keyButton.move(50,50)   

    okButton = QtWidgets.QPushButton(w)
    okButton.setGeometry(100, 250, 100, 75)
    okButton.setText("Okay")
    okButton.clicked.connect(QtCore.QCoreApplication.instance().quit)

    w.show()
    sys.exit(setup.exec_())



    