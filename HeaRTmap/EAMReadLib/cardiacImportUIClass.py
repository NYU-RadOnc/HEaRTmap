#NOT USED. Read Whole Directory Instead
import slicer
import qt
from qt import QPushButton, QLineEdit 

#EAMread dialog class
class EAMread_dialog():
    def __init__(self, UIfile=None, filefilter='*.xml'):
        super(EAMread_dialog, self).__init__()
        self.ui = slicer.util.loadUI(UIfile)  #this is already QDialog
        self.filefilter = filefilter
        self.result = []

        self.meshAfile_lineEdit = self.ui.findChild(QLineEdit, 'meshAfile_lineEdit')
        EAMmeshA_pushButton = self.ui.findChild(QPushButton, 'EAMmeshA_pushButton')
        EAMmeshA_pushButton.clicked.connect(self.onMeshAButton)

        self.meshBfile_lineEdit = self.ui.findChild(QLineEdit, 'meshBfile_lineEdit')
        EAMmeshB_pushButton = self.ui.findChild(QPushButton, 'EAMmeshB_pushButton')
        EAMmeshB_pushButton.clicked.connect(self.onMeshBButton)


        ReadEAM_pushButton = self.ui.findChild(QPushButton, 'ReadEAMData_pushButton')
        ReadEAM_pushButton.clicked.connect(self.onReadButton)

        #ReadEAM_pushButton = self.ui.findChild(QPushButton, 'CancelRead_pushButton')
        #ReadEAM_pushButton.clicked.connect(self.onReadButton)  #linked
        #self.ui.exec()  #Run this GUI

    def modalShow(self):
        return self.ui.exec()  #return Accepted/Canceled automatically

    def onMeshAButton(self):
        qfiledialog = qt.QFileDialog() 
        tfile = qfiledialog.getOpenFileName()
        self.meshAfile_lineEdit.setText(tfile)

    def onMeshBButton(self):
        qfiledialog = qt.QFileDialog() 
        tfile = qfiledialog.getOpenFileName()
        #self, ("Open File"), "/home",  ("Images (*.png *.xpm *.jpg)")
        self.meshBfile_lineEdit.setText(tfile)

    def onReadButton(self):
        self.result = {'meshAfile': self.meshAfile_lineEdit.text, 
                    'meshBfile': self.meshBfile_lineEdit.text}

    def GetValue(self):
        return self.result


#Read Insight dialog class
class Insightread_dialog():
    def __init__(self, UIfile=None):
        super(Insightread_dialog, self).__init__()
        self.ui = slicer.util.loadUI(UIfile)  #this is already QDialog
        self.result = []

        self.ctdcmPath_lineEdit = self.ui.findChild(QLineEdit, 'ctdcmPath_lineEdit')
        ctdcmPath_pushButton = self.ui.findChild(QPushButton, 'ctdcmPath_pushButton')
        ctdcmPath_pushButton.clicked.connect(self.onctdcmPathButton)

        self.heartMesh_lineEdit = self.ui.findChild(QLineEdit, 'heartMesh_lineEdit')
        heartMesh_pushButton = self.ui.findChild(QPushButton, 'heartMesh_pushButton')
        heartMesh_pushButton.clicked.connect(self.onheartMeshButton)

        self.valveholeMesh_lineEdit = self.ui.findChild(QLineEdit, 'valveholeMesh_lineEdit')
        valveholeMesh_pushButton = self.ui.findChild(QPushButton, 'valveholeMesh_pushButton')
        valveholeMesh_pushButton.clicked.connect(self.onvalveholeMeshButton)

        self.torsoMesh_lineEdit = self.ui.findChild(QLineEdit, 'torsoMesh_lineEdit')
        torsoMesh_pushButton = self.ui.findChild(QPushButton, 'torsoMesh_pushButton')
        torsoMesh_pushButton.clicked.connect(self.ontorsoMeshButton)

        self.valvemarkMesh_lineEdit = self.ui.findChild(QLineEdit, 'valvemarkMesh_lineEdit')
        valvemarkMesh_pushButton = self.ui.findChild(QPushButton, 'valvemarkMesh_pushButton')
        valvemarkMesh_pushButton.clicked.connect(self.onvalvemarkMeshButton)

        self.usermarkMesh_lineEdit = self.ui.findChild(QLineEdit, 'usermarkMesh_lineEdit')
        usermarkMesh_pushButton = self.ui.findChild(QPushButton, 'usermarkMesh_pushButton')
        usermarkMesh_pushButton.clicked.connect(self.onusermarkMeshButton)

        self.voltageMap_lineEdit = self.ui.findChild(QLineEdit, 'voltageMap_lineEdit')
        voltageMap_pushButton = self.ui.findChild(QPushButton, 'voltageMap_pushButton')
        voltageMap_pushButton.clicked.connect(self.onvoltageMapButton)

        self.potentialMap_lineEdit = self.ui.findChild(QLineEdit, 'potentialMap_lineEdit')
        potentialMap_pushButton = self.ui.findChild(QPushButton, 'potentialMap_pushButton')
        potentialMap_pushButton.clicked.connect(self.onpotentialMapButton)

        self.activationMap_lineEdit = self.ui.findChild(QLineEdit, 'activationMap_lineEdit')
        activationMap_pushButton = self.ui.findChild(QPushButton, 'activationMap_pushButton')
        activationMap_pushButton.clicked.connect(self.onactivationMapButton)

        self.directActivateMap_lineEdit = self.ui.findChild(QLineEdit, 'directActivateMap_lineEdit')
        directActivateMap_pushButton = self.ui.findChild(QPushButton, 'directActivateMap_pushButton')
        directActivateMap_pushButton.clicked.connect(self.ondirectActivateMapButton)

        self.propagateMap_lineEdit = self.ui.findChild(QLineEdit, 'propagateMap_lineEdit')
        propagateMap_pushButton = self.ui.findChild(QPushButton, 'propagateMap_pushButton')
        propagateMap_pushButton.clicked.connect(self.onpropagateMapButton)

        self.slewrateMap_lineEdit = self.ui.findChild(QLineEdit, 'slewrateMap_lineEdit')
        slewrateMap_pushButton = self.ui.findChild(QPushButton, 'slewrateMap_pushButton')
        slewrateMap_pushButton.clicked.connect(self.onslewrateMapButton)

        ReadInsight_pushButton = self.ui.findChild(QPushButton, 'readInsight_pushButton')
        ReadInsight_pushButton.clicked.connect(self.onReadButton)

        #CancelRead_pushButton = self.ui.findChild(QPushButton, 'CancelRead_pushButton')
        #CancelRead_pushButton.clicked.connect(self.onCancelButton)  #linked
 
    def modalShow(self):
        return self.ui.exec()  #return Accepted/Canceled automatically

    def onctdcmPathButton(self):
        tdir = qt.QFileDialog().getExistingDirectory()
        self.ctdcmPath_lineEdit.setText(tdir)

    def onheartMeshButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        #self, ("Open File"), "/home",  ("Images (*.png *.xpm *.jpg)")
        self.heartMesh_lineEdit.setText(tfile)

    def onvalveholeMeshButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.valveholeMesh_lineEdit.setText(tfile)

    def ontorsoMeshButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.torsoMesh_lineEdit.setText(tfile)

    def onvalvemarkMeshButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.valvemarkMesh_lineEdit.setText(tfile)

    def onusermarkMeshButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.usermarkMesh_lineEdit.setText(tfile)

    def onvoltageMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.voltageMap_lineEdit.setText(tfile)

    def onpotentialMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.potentialMap_lineEdit.setText(tfile)

    def onactivationMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.activationMap_lineEdit.setText(tfile)

    def ondirectActivateMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.directActivateMap_lineEdit.setText(tfile)

    def onpropagateMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.propagateMap_lineEdit.setText(tfile)

    def onslewrateMapButton(self):
        tfile = qt.QFileDialog().getOpenFileName()
        self.slewrateMap_lineEdit.setText(tfile)

    def onReadButton(self):
        self.result = {'ctdcmPath': self.ctdcmPath_lineEdit.text, 
                    'heartMesh': self.heartMesh_lineEdit.text,
                    'valveholeMesh': self.valveholeMesh_lineEdit.text,
                    'torsoMesh': self.torsoMesh_lineEdit.text,
                    'valvemarkMesh': self.valvemarkMesh_lineEdit.text,
                    'usermarkMesh': self.usermarkMesh_lineEdit.text,
                    'voltageMap': self.voltageMap_lineEdit.text,
                    'potentialMap': self.potentialMap_lineEdit.text,
                    'activationMap': self.activationMap_lineEdit.text,
                    'directactivateMap': self.directActivateMap_lineEdit.text,
                    'propagateMap': self.propagateMap_lineEdit.text,
                    'slewrateMap': self.slewrateMap_lineEdit.text,
                    }

    def GetValue(self):
        return self.result

        