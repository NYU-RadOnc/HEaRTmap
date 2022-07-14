from contextlib import redirect_stderr
import os
import vtk
import datetime 

import slicer
from   slicer.ScriptedLoadableModule import *
from   slicer.util import VTKObservationMixin
import DicomRtImportExportPlugin  #DICOM RT export
import qt
#............
import EAMReadLib
import cardiacSlicerLib

# cardiacRT
class cardiacRT(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "NYU CardiacRT 2022"
        self.parent.categories = ["NYU CardiacRT"]  # ["Examples"]
        self.parent.dependencies = []
        self.parent.contributors = ["Hesheng Wang (Radiation Oncology, NYU)"]
        self.parent.helpText = """ Development """
        self.parent.acknowledgementText = """ Clinical Implementation """

        # Additional initialization step after application startup is complete
        # slicer.app.connect("startupCompleted()", registerSampleData)

def registerSampleData():
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    #import SampleData
    iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # ImgEAMWorkflow
    """
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='ImgEAMWorkflow',
        sampleName='ImgEAMWorkflow',
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, 'ImgEAMWorkflow.png'),

        # Download URL and target file name
        # uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        # fileNames='RTWorkflow1.nrrd',
        # Checksum to ensure file integrity. Can be computed by this command:
        # import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        # checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
        # This node name will be used when the data set is loaded
        # nodeNames='ImgEAMRTWorkflow'
    )
    """

#cardiacRTWidget
class cardiacRTWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        # needed for parameter node observation
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._updatingGUIFromParameterNode = False

    # Called when the user opens the module the first time and the widget is initialized.
    def setup(self):
        #un-parent setup to allow debug    
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/cardiacRT.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets.
        # Make sure that in Qt designer the top-level qMRMLWidget's "mrmlSceneChanged(vtkMRMLScene*)" signal in
        # is connected to each MRML widget's "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = cardiacRTLogic()

        # ^^^Connections with event handles
        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        #connections for each collapsibleButton
        #.....loaddataCollapsibleButton
        self.ui.carto3_pushButton.connect(
            'clicked(bool)', self.oncarto3Button)
        self.ui.rhythmia_pushButton.connect(
            'clicked(bool)', self.onrhythmiaButton)
        self.ui.velocity_pushButton.connect(
            'clicked(bool)', self.onvelocityButton)
        self.ui.insight_pushButton.connect(
            'clicked(bool)', self.oninsightButton)
        #self.ui.loadpfile_pushButton.connect(
        #   'clicked(bool)', self.onloadpfileButton)

        #.....DisplayCollapsibleButton
        self.ui.DisplayCollapsibleButton.connect(
            "toggled(bool)", self.initDisplayCollapsibleButton)
        self.ui.show3DView_pushButton.connect(
            'clicked(bool)', self.onshow3dviewButton)
        self.ui.mapNode_MRMLNodeComboBox.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.updateScalarfromModelNode)
        self.ui.scalarMap_comboBox.connect(
            "currentTextChanged(QString)", self.updateRangeAfterMapSelect)
        self.ui.showSurfmap_pushButton.connect(
            'clicked(bool)', self.onshowsurfmapButton)
        self.ui.hideColorbar_pushButton.connect(
            'clicked(bool)', self.onhidecolorbarButton)

        #.....RegistrationCollapsibleButton
        self.ui.RegistrationCollapsibleButton.connect(
            "toggled(bool)", self.initRegistrationCollapsibleButton)
        self.ui.newtransName_pushButton.connect(
            "clicked(bool)", self.onnewtransNameButton)
        self.ui.regactiontype_comboBox.connect(
            "currentTextChanged(QString)", self.updateregtypeforNewTransform)
        self.ui.refreshsurfList_pushButton.connect(
            "clicked(bool)", self.onrefreshsurfListButton)
        self.ui.register_pushButton.connect(
            "clicked(bool)", self.onregisterButton)
        self.ui.createmarkpair_pushButton.connect(
            "clicked(bool)", self.oncreatemarkpairButton)

        #.....segmodelToolsCollapsibleButton
        self.ui.segmodelToolsCollapsibleButton.connect(
            "toggled(bool)", self.initsegmodelToolsCollapsibleButton)
        self.ui.transImg_MRMLNodeComboBox.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.initsegmodelToolsCollapsibleButton)
        self.ui.transSegmentation_MRMLNodeComboBox.connect(
            "currentNodeChanged(vtkMRMLNode*)", self.toolsegmentationselected)

        #update list
        self.ui.transUpdate_pushButton.connect(
            'clicked(bool)', self.initsegmodelToolsCollapsibleButton)
       
        #segment/model tools
        self.ui.toolcopySeg_pushButton.connect(
            'clicked(bool)', self.ontoolcopySegButton)
        self.ui.toolcopyModel_pushButton.connect(
            'clicked(bool)', self.ontoolcopyModelButton)
        self.ui.toolrenameSeg_pushButton.connect(
            'clicked(bool)', self.ontoolrenameSegButton)
        self.ui.toolrenameModel_pushButton.connect(
            'clicked(bool)', self.ontoolrenameModelButton)
        self.ui.tooldelSeg_pushButton.connect(
            'clicked(bool)', self.ontooldelSegButton)
        self.ui.tooldelModel_pushButton.connect(
            'clicked(bool)', self.ontooldelModelButton)
        self.ui.transSeg2Model_pushButton.connect(
            'clicked(bool)', self.ontoolSeg2ModelButton)
        self.ui.transModel2Seg_pushButton.connect(
            'clicked(bool)', self.ontoolModel2SegButton)

        #create landmark and curve
        self.ui.newSegmentation_pushButton.connect(
            'clicked(bool)', self.ontoolNewSegmentationButton)
        self.ui.toolCreateLandmark_pushButton.connect(
            'clicked(bool)', self.ontoolCreateLandmarkButton)
        self.ui.toolCreateCurve_pushButton.connect(
            'clicked(bool)', self.ontoolCreateCurveButton)

        #cut to get partial surface
        self.ui.toolCutSurface_pushButton.connect(
            'clicked(bool)', self.ontoolCutSurfaceButton)

        #......genVolumeCollapsibleButton
        self.ui.genVolumeCollapsibleButton.connect(
            "toggled(bool)", self.initgenVolumeCollapsibleButton)
        self.ui.genSegmentation_MRMLNodeComboBox.connect(
            "currentNodeChanged(vtkMRMLNode*)", 
            self.initgenVolumeCollapsibleButton)

        self.ui.genIntVolume_pushButton.connect(
            'clicked(bool)', self.ongenIntVolumeButton)

        #.......ExportDCMCollapsibleButton
        self.ui.exportDCM_pushButton.connect(
            'clicked(bool)', self.onexportDCMButton)

        #......drawEAMCollapsibleButton
        self.ui.initEAMcurve_pushButton.connect(
            'clicked(bool)', self.oninitEAMcurveButton)
        self.ui.genEAMscar_pushButton.connect(
            'clicked(bool)', self.ongenEAMscarButton)

        #.....gentLV17SegmentCollapsibleButton
        self.ui.gentLV17SegmentCollapsibleButton.connect(
            "toggled(bool)", self.initgentLV17SegmentCollapsibleButton)
        self.ui.seg17SegmentationNode_ComboBox.connect(
            "currentNodeChanged(vtkMRMLNode*)", 
            self.initgentLV17SegmentCollapsibleButton)
        
        self.ui.gentSeptMidPt_pushButton.connect(
            'clicked(bool)', self.ongentSeptMidPtButton)

        self.ui.gentLV17Modelcut_pushButton.connect(
            'clicked(bool)', self.ongentLV17ModelcutButton)
        
        self.ui.gentLV17Segment_pushButton.connect(
            'clicked(bool)', self.ongentLV17SegmentButton)

        # connections ensure that whenever user changes some settings on the GUI,
        # that is saved in the MRML scene in the selected parameter node.

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    # Called when the application closes and the module widget is destroyed.
    def cleanup(self):
        self.removeObservers()

    # Called each time the user opens this module.
    def enter(self):
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    # Called each time the user opens a different module.
    def exit(self):
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        if hasattr(self, '_parameterNode'):
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Called just before the scene is closed.
    def onSceneStartClose(self, caller, event):
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    # Called just after the scene is closed.
    def onSceneEndClose(self, caller, event):
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    # ....Ensure parameter node exists and observed.
    def initializeParameterNode(self):
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.
        self.setParameterNode(self.logic.getParameterNode())
    # Set and observe parameter node

    def setParameterNode(self, inputParameterNode):
        # Observation is needed because when the parameter node is changed then the GUI must be updated immediately.

        # set default parameters in ParameterNode, ending call updateGUIFromParameterNode() update GUI
        if inputParameterNode:  # initial logging parameter
            self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI by calling self.updateGUIFromParameterNode()
        if hasattr(self, '_parameterNode') and self._parameterNode is not None:
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        # set _parameterNode as inputParameterNode, then observe it change
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent,
                             self.updateGUIFromParameterNode)
        # if observe modify in _parameterNode, call self.updateGUIFromParameterNode
        # Initial GUI update
        self.updateGUIFromParameterNode()

    # update module GUI whenever parameter node is change due to setted observer
    def updateGUIFromParameterNode(self, caller=None, event=None):
        # This method is called whenever parameter node is changed.
        # The module GUI is updated to show the current state of the parameter node.
        #if self._parameterNode is None: #or self._updatingGUIFromParameterNode:
        #    return
        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        #self._updatingGUIFromParameterNode = True
        # Update logging information
        #self.ui.Logging_listWidget.clear()
        #loginfo = self._parameterNode.GetParameter("ProgressLogging")
        #loglist = loginfo.split(':')  # split by : for list display
        #for item in loglist:
        #    self.ui.Logging_listWidget.addItem(item)
        # All the GUI updates are done
        #self._updatingGUIFromParameterNode = False
        return

    # upate ParameterNode when users makes any change in GUI
    def updateParameterNodeFromGUI(self, logstr=None, caller=None, event=None):
        # This method is called when the user makes any change in the GUI.
        # The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        if (logstr is None) or (self._parameterNode is None): #or (self._updatingGUIFromParameterNode):
            return

        # Modify all properties in a single batch
        #wasModified = self._parameterNode.StartModify()
        loginfo = self._parameterNode.GetParameter("ProgressLogging")
        loginfo += logstr + ':'  # ':' for split show
        self._parameterNode.SetParameter("ProgressLogging", loginfo)
        #self._parameterNode.EndModify(wasModified)
    
    #*****************************************************************************
    
    #---------------load data Buttons-------------
    def oncarto3Button(self):
        filename = qt.QFileDialog.getOpenFileName(
                        self.parent, "Open CARTO 3 file", "", 
                        "ZIP archives (*.zip);;All files (*.*)", 
                        qt.QFileDialog.ExistingFile)
        if len(filename)>0:
            if not self.logic.readCarto(filename):
                slicer.util.messageBox('EAM Reading Failed!')
            else:
                slicer.util.messageBox('To Modolue/.Data check loaded data')

    def onrhythmiaButton(self):
        filename = qt.QFileDialog.getOpenFileName(
            self.parent, "Open RHYTHMIA file", "", 
            "RHYTHMIA exported archive (*.000);;All files (*.*)", 
            qt.QFileDialog.ExistingFile)
        if len(filename)>0:
            if not self.logic.readRhythemia(filename):
                slicer.util.messageBox('EAM Reading Failed!')
            else:
                slicer.util.messageBox('To Modolue/.Data check loaded data')

    def onvelocityButton(self):
        filename = qt.QFileDialog.getOpenFileName(
                self.parent, "Open Ensite file", "", 
                "XML files (*.xml);;All files (*.*)", 
                qt.QFileDialog.ExistingFile)
        if len(filename)>0:
            if not self.logic.readEnsiteVelocity(filename):
                slicer.util.messageBox('EAM Reading Failed!')
            else:
                slicer.util.messageBox('To Modolue/.Data check loaded data')

    def oninsightButton(self):
        dirname = qt.QFileDialog.getExistingDirectory(
                self.parent, "Open CardiacInsight Data Directory")
        if len(dirname)>0:
            if not self.logic.readcardiacInsight(dirname):
                slicer.util.messageBox('cardiacInsight Reading Failed!')
            else:
                slicer.util.messageBox('To Modolue/.Data check loaded data')
    
    #----------DisplayCollapsibleButton: Display3DView--------------------
    #inital to ensure ColorTable of different Map crated.
    def initDisplayCollapsibleButton(self):
        ColorTableNode = self.ExistSingletNodeByName(
            self.logic.SetNodeNames['InsightMV_ColorTable'])
        if ColorTableNode is None:
            self.logic.createCardiacColorTable(
                self.logic.SetNodeNames['InsightMV_ColorTable'])
        ColorTableNode = self.ExistSingletNodeByName(
            self.logic.SetNodeNames['InsightMS_ColorTable'])
        if ColorTableNode is None:
            self.logic.createCardiacColorTable(
                self.logic.SetNodeNames['InsightMS_ColorTable'])
        ColorTableNode = self.ExistSingletNodeByName(
            self.logic.SetNodeNames['EnsiteEAM_ColorTable'])
        if ColorTableNode is None:
            self.logic.createCardiacColorTable(
                self.logic.SetNodeNames['EnsiteEAM_ColorTable'])
        #set colorbar list
        if self.ui.colorNode_comboBox.count == 0:
            self.ui.colorNode_comboBox.addItem(
                self.logic.SetNodeNames['InsightMV_ColorTable'])
            self.ui.colorNode_comboBox.addItem(
                self.logic.SetNodeNames['InsightMS_ColorTable'])
            self.ui.colorNode_comboBox.addItem(
                self.logic.SetNodeNames['EnsiteEAM_ColorTable'])
        #update scalar names for selected modelNode 
        self.updateScalarfromModelNode() 
        #update map range for selected scalar names
        self.updateRangeAfterMapSelect()

    def onshow3dviewButton(self):
        layoutManager = slicer.app.layoutManager()
        layoutManager.setLayout(1)  #conventional 3D View Layout

    #update scalar names list based on selected model
    def updateScalarfromModelNode(self):
        self.ui.scalarMap_comboBox.clear()
        selModelNode = self.NodeofNodeID(
            self.ui.mapNode_MRMLNodeComboBox.currentNodeID)
        if selModelNode is None:
            return
        scalarmapNames = self.logic.getScalarMapNames(selModelNode)
        if len(scalarmapNames)==0:
            return
        for name in scalarmapNames:
            self.ui.scalarMap_comboBox.addItem(name)

    #update scalars range based on selected model and scalar map
    def updateRangeAfterMapSelect(self):
        selModelNode = self.NodeofNodeID(
            self.ui.mapNode_MRMLNodeComboBox.currentNodeID)
        selmapName = self.ui.scalarMap_comboBox.currentText
        if (selModelNode is None) or (len(selmapName)==0):
            return 
        range = self.logic.getScalarRange(selModelNode, selmapName)
        if not range:
            return
        lowvalue, uprvalue = range[0], range[1]
        #set to rangeWidget
        rangeWidget = self.ui.mapRange_MRMLRangeWidget
        rangeWidget.minimum = lowvalue
        rangeWidget.maximum = uprvalue
        rangeWidget.singleStep = (uprvalue-lowvalue)/100
        rangeWidget.minimumValue = lowvalue
        rangeWidget.maximumValue = uprvalue
        
    def onshowsurfmapButton(self):
        selModNode = self.NodeofNodeID(
            self.ui.mapNode_MRMLNodeComboBox.currentNodeID)
        selScalarName = self.ui.scalarMap_comboBox.currentText
        colorName = self.ui.colorNode_comboBox.currentText
        if (len(selScalarName)==0) or (len(colorName)==0):
            return
        selColorNode = self.ExistSingletNodeByName(colorName)
        if (not selColorNode) or (not selColorNode):
            return
        #get range
        rangeWidget = self.ui.mapRange_MRMLRangeWidget
        lowvalue = rangeWidget.minimumValue
        uprvalue = rangeWidget.maximumValue
        #with all parameters
        self.logic.showCardiacMap(
            selModNode, selScalarName, selColorNode, lowvalue, uprvalue)

    def onhidecolorbarButton(self):
        self.logic.hideColorbarinView()

    #----------RegistrationCollapsibleButton-----
    #init model lists and comboBox items
    def initRegistrationCollapsibleButton(self):
        if not self.ui.RegistrationCollapsibleButton.collapsed:
            self.ui.regMovSurfs_listWidget.clear()
            nodetypelist=["vtkMRMLScalarVolumeNode", "vtkMRMLSegmentationNode",
                            "vtkMRMLModelNode", "vtkMRMLMarkupsFiducialNode"]
            nodelist = self.getNodeList(nodetypelist)
            for item in nodelist:  
                self.ui.regMovSurfs_listWidget.addItem(item.GetName())
            #self.ui.regactiontype_comboBox.setCurrentIndex(1)
            #self.ui.newregtype_comboBox.setEnabled(False)  
            #disable New if regactiontype is "Use Existing Transform"
            self.updateregtypeforNewTransform() 

    #enable Auto/Manual selection if new/overwrite transformation
    def updateregtypeforNewTransform(self):
        if self.ui.regactiontype_comboBox.currentIndex == 0:
            self.ui.newregtype_comboBox.setEnabled(True)
            self.ui.newregtype_comboBox.setCurrentIndex(0)
        else: #as regactiontype is "Use Existing Transform"
            self.ui.newregtype_comboBox.setEnabled(False)  

    def onnewtransNameButton(self):
        setname = self.GenerateSingletNodeName('Liear Transform')
        if setname is None:
            return
        transNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        transNode.SetName(setname)
        transNode.SetSingletonOn()
        transNode.SetAttribute('MatrixSet','F')  #New transform, no transform yet

    def oncreatemarkpairButton(self):
        refmarkname = str(self.ui.referlandmarkName_lineEdit.text).strip()
        movmarkname = str(self.ui.movlandmarkName_lineEdit.text).strip()
        marksnumstr = str(self.ui.reglandmarkNum_lineEdit.text).strip()
        if len(refmarkname)==0 or len(movmarkname)==0 or len(marksnumstr)==0:
            slicer.util.messageBox('Invalid names or num of marks')
            return
        marknum = int(marksnumstr)
        if marknum<3:
            slicer.util.messageBox('Number of Marks Less than 3')
            return
        #check singleton 
        refmarksNode = self.ExistSingletNodeByName(refmarkname)
        movmarksNode = self.ExistSingletNodeByName(movmarkname)
        if refmarksNode is not None:
            slicer.util.messageBox(refmarkname + ' Node exists')
            return
        if movmarksNode is not None:
            slicer.util.messageBox(movmarkname + ' Node exists')
            return

        #create LandmarkSet 
        refmarksNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        refmarksNode.SetName(refmarkname)
        refmarksNode.SetSingletonOn()
        self.logic.createLandmarkSet(refmarksNode, marknum, prestr='fix', xypos=(50,0), color=(0,0,1))

        movmarksNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        movmarksNode.SetName(movmarkname)
        movmarksNode.SetSingletonOn()
        self.logic.createLandmarkSet(movmarksNode, marknum, prestr='mov',xypos=(0,50), color=(1,0,0))

        self.initRegistrationCollapsibleButton()
        slicer.util.messageBox('Go Modules(Markups) to Edit Landmarkpoints pair:'
                               + refmarkname + ' and ' + movmarkname)
                               
    def onrefreshsurfListButton(self):
        self.initRegistrationCollapsibleButton()

    def onregisterButton(self):
        refdataNode   = self.NodeofNodeID(self.ui.referNode_MRMLNodeComboBox.currentNodeID)
        movdataNode   = self.NodeofNodeID(self.ui.movNode_MRMLNodeComboBox.currentNodeID)
        transformNode = self.NodeofNodeID(self.ui.transformNode_MRMLNodeComboBox.currentNodeID)
        if (refdataNode is None) or (movdataNode is None) or (transformNode is None):
            slicer.util.messageBox('Check Ref/Mov/Transform Defined!')
            return
        if refdataNode.GetClassName() != movdataNode.GetClassName():
            slicer.util.messageBox('Ref and Mov Nodes are different data type')
            return
        #ensure registration set if applying the transform
        regact  = self.ui.regactiontype_comboBox.currentIndex
        newtype = self.ui.newregtype_comboBox.currentIndex
        if (regact == 1) and (transformNode.GetAttribute('MatrixSet')=='F'):
            slicer.util.messageBox('Selected Transform Not Set Yet')
            return
        #do registration 
        #show Model/LandMark data in 3D View First
        if refdataNode.GetClassName() != 'vtkMRMLScalarVolumeNode':
            refdataNode.GetDisplayNode().SetVisibility(True)
            movdataNode.GetDisplayNode().SetVisibility(True)
            #displayNode.SetViewNodeIDs(["vtkMRMLSliceNodeRed", "vtkMRMLViewNode1"])
        if regact == 0:  #New or overwrite current transform
            if newtype == 0: #Auto registration
                transNode = self.logic.cardiacRegister(refdataNode, movdataNode, transformNode)
                if transNode is None:
                    transformNode.SetAttribute('MatrixSet', 'F')  
                    slicer.util.messageBox('New Registration Failed.'
                                 + '\n Selected transform becomes invalid' )
                    return
                else:
                    transformNode.SetAttribute('MatrixSet', 'T')
            else:  #Manual Registration
                transformNode.SetAttribute('MatrixSet', 'T')   
                slicer.util.messageBox('Go Modules(Transform)' 
                                + '\n Select Transform '+ transformNode.GetName()
                                + '\n Perform manual registration'
                                + '\n Go here to Apply the transform on Data')
                return
        #regact=1, or tranform generated, apply transform on selected data
        #if volume selected for tranform, but reference is not volume, No transform
        self.applyTransformtoNodes(refdataNode, transformNode)
        self.initRegistrationCollapsibleButton() #Update list

    #apply transform to selected volume/model/landmarks     
    def applyTransformtoNodes(self, refdataNode, transformNode):
        if len(self.ui.regMovSurfs_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No Models Selected for Registration")
            return

        nVol = 0  #check VolumeNode for register
        for item in self.ui.regMovSurfs_listWidget.selectedItems():
            nodename = item.text()
            selnode = self.ExistSingletNodeByName(nodename)
            if selnode is None:
                slicer.util.messageBox('Selected ' + nodename + ' NOT Exist')
                return
            if selnode.GetClassName() == 'vtkMRMLScalarVolumeNode':
                nVol += 1

        if (nVol > 0) and (refdataNode.GetClassName() != 'vtkMRMLScalarVolumeNode'):
            slicer.util.messageBox('reference Not Volume but volumes selected for transform.'
                                + '\n Please Either unselect Volumes for transform'
                                + '\n OR choose volume as reference')
            return
        #specific transform Name
        tName = transformNode.GetName().replace(" ","")
        tName = tName.replace('_','').replace('-','')
        #transform selected volumes
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene) 
        for item in self.ui.regMovSurfs_listWidget.selectedItems():
            nodename = item.text()
            selnode = slicer.util.getNode(nodename)  #above has checked node valid

            #remove any transform from the node 
            if selnode.GetParentTransformNode() is not None:
                selnode.SetAndObserveTransformNodeID(None) 

            #copy the node then apply transform
            regnodename = tName + '_' + nodename   #transformed Node Name 
            regNode = self.ExistSingletNodeByName(regnodename)
            if regNode is not None:  #remove if the node already exists
                slicer.mrmlScene.RemoveNode(regNode)
            #Now RegNode is None
            if selnode.GetClassName() == 'vtkMRMLScalarVolumeNode':
                regNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
                self.logic.transformVolume(refdataNode, selnode, transformNode, regNode)
                regNode.SetName(regnodename)
                regNode.SetSingletonOn()
            else:
                itemIDToClone = shNode.GetItemByDataNode(selnode)
                clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode,itemIDToClone)
                regNode = shNode.GetItemDataNode(clonedItemID)
                regNode.SetName(regnodename)
                regNode.SetSingletonOn()
                #apply and harden transformation
                regNode.SetAndObserveTransformNodeID(transformNode.GetID())
                slicer.vtkSlicerTransformLogic.hardenTransform(regNode) #harden transformation
                regNode.GetDisplayNode().SetColor(0.0, 0.0, 1.0)
                #to refresh the copied node by clone then delete (seems work, although unnecessary)
                clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode,itemIDToClone)
                slicer.mrmlScene.RemoveNode(shNode.GetItemDataNode(clonedItemID))
    
        slicer.util.messageBox(transformNode.GetName() + ' Registration on Selected Data DONE!')
    
    #---------------segmodelToolsCollapsibleButton----------- 
    def initsegmodelToolsCollapsibleButton(self):
        if not self.ui.segmodelToolsCollapsibleButton.collapsed:
            self.ui.transModel_listWidget.clear()
            # ..model and Markup list, must be detail Markups class, not general vtkMRMLMarkupsNode
            nodetypelist = ["vtkMRMLModelNode",
                            "vtkMRMLMarkupsClosedCurveNode",
                            "vtkMRMLMarkupsFiducialNode"]
            nodelist = self.getNodeList(nodetypelist)
            for item in nodelist:
                self.ui.transModel_listWidget.addItem(item.GetName())

            #check initial volume and segmentation consistency
            refVolNode = self.NodeofNodeID(
                        self.ui.transImg_MRMLNodeComboBox.currentNodeID)
            if refVolNode is None:
                if self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID is not None:
                    self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID=None
                    return  #automatically call self.toolsegmentationselected()
            #if refVolume and segmentation not match, reset
            segmentationNode = self.NodeofNodeID(
                    self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID)
            if segmentationNode is not None:
                refvolID = segmentationNode.GetNodeReferenceID('ReferVolumeID')
                if (refvolID is None) or (refvolID != refVolNode.GetID()):
                    self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID=None
                    return #automatically call self.toolsegmentationselected()
            #if all matched, update segment list by call
            self.toolsegmentationselected()

    def ontoolNewSegmentationButton(self):
        refVolNode = self.NodeofNodeID(
            self.ui.transImg_MRMLNodeComboBox.currentNodeID,
            'No Reference Volume Selected')
        if refVolNode is None:
            return
        setname = self.GenerateSingletNodeName('Segmentation')
        if setname is None:  # Name not given, or the node already exists
            return
        yn = slicer.util.confirmYesNoDisplay(
            "New segementation refer to volume " + refVolNode.GetName() + " ?",
            windowTitle='Refer Volume for Segmentation')
        if not yn:
            return
        #create segmentation
        #segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode = slicer.vtkMRMLSegmentationNode()
        segmentationNode.CreateDefaultDisplayNodes()  # needed for display
        segmentationNode.SetName(setname)
        segmentationNode.SetNodeReferenceID(
            'ReferVolumeID', refVolNode.GetID())
        # automatically signal toolsegmentationselected()
        slicer.mrmlScene.AddNode(segmentationNode)
        segmentationNode.SetSingletonOn()

        currentsegmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID)
        if (currentsegmentationNode is None) or (currentsegmentationNode.GetName() is not setname):
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID = segmentationNode.GetID()
        return  # automatically call self.toolsegmentationselected()
    
    #when segmentation selection changed, update list accordingly
    def toolsegmentationselected(self):
        self.ui.transSegment_listWidget.clear()

        segmentationNode = self.NodeofNodeID(
                self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID)
        if segmentationNode is None:
            return

        refVolNode = self.NodeofNodeID(
                self.ui.transImg_MRMLNodeComboBox.currentNodeID, 
                'No Reference Volume Selected')
        if refVolNode is None:
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID=None
            return

        #check volume and segmentation matching
        refvolID = segmentationNode.GetNodeReferenceID('ReferVolumeID')
        if (refvolID is None) or (refvolID != refVolNode.GetID()):
            yn = slicer.util.confirmYesNoDisplay(
                    "Segmentation not refer to select volume."
                    + "\n Set Selected volume as reference?",
                    windowTitle='Segmentation Reference Volume')
            if yn:
                segmentationNode.SetNodeReferenceID(
                    'ReferVolumeID', refVolNode.GetID())
            else:
                self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID=None
                return
        #refVolume and Segmentation match here; otherwise already return
        for i in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
            segment = segmentationNode.GetSegmentation().GetNthSegment(i)
            self.ui.transSegment_listWidget.addItem(segment.GetName())

    def ontoolcopySegButton(self):
        refVolNode = self.NodeofNodeID(
            self.ui.transImg_MRMLNodeComboBox.currentNodeID, 'No Reference Volume Selected')
        if refVolNode is None:
            return
        segmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID, 'No Segmentation Selected')
        if segmentationNode is None:
            return
        #selected segment to copy
        if len(self.ui.transSegment_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No Segments Selected for Copy")
            return
        segmentation = segmentationNode.GetSegmentation()
        for item in self.ui.transSegment_listWidget.selectedItems():
            segname = item.text()
            srsegmentId = segmentation.GetSegmentIdBySegmentName(segname)
            #check copied segment name
            cpsegname = segname + '_copy'
            cpsegmentId = segmentation.GetSegmentIdBySegmentName(cpsegname)
            if cpsegmentId is not None:  # delete first
                segmentationNode.GetSegmentation().RemoveSegment(cpsegmentId)
            segmentation.CopySegmentFromSegmentation(segmentation, srsegmentId)
            #set copy segment name
            segment = segmentationNode.GetSegmentation().GetSegment(srsegmentId)
            segment.SetName(cpsegname)
            #print(segment.GetName())

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists
            
    def ontoolcopyModelButton(self):
        #selected models to copy
        if len(self.ui.transModel_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No Models Selected for Copy")
            return
        # make copy
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(
            slicer.mrmlScene)
        #transformLogic = slicer.vtkSlicerTransformLogic()
        for item in self.ui.transModel_listWidget.selectedItems():
            modelname = item.text()
            modelNode = self.ExistSingletNodeByName(modelname)
            if modelNode is None:
                slicer.util.messageBox(modelname+' Not Exist')
                return

            cpnodename = modelname + '_copy'
            cpNode = self.ExistSingletNodeByName(cpnodename)
            if cpNode is not None:
                slicer.util.messageBox(cpnodename+' Exists, Be OverWritten.')
                slicer.mrmlScene.RemoveNode(cpNode)
            #Make a copy
            itemIDToClone = shNode.GetItemByDataNode(modelNode)
            clonedItemID = slicer.modules.subjecthierarchy.logic(
            ).CloneSubjectHierarchyItem(shNode, itemIDToClone)
            clonedNode = shNode.GetItemDataNode(clonedItemID)
            clonedNode.SetName(cpnodename)
            #transformLogic.hardenTransform(clonedNode)

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

    def ontoolrenameSegButton(self):
        segmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID, 'No Segmentation Given')
        if segmentationNode is None:
            return
        if len(self.ui.transSegment_listWidget.selectedItems()) != 1:
            slicer.util.messageBox("Select One Segment for Rename")
            return

        selectname = self.ui.transSegment_listWidget.selectedItems()[0].text()
        mw = slicer.util.lookupTopLevelWidget('qSlicerMainWindow')
        setname = qt.QInputDialog.getText(mw,'Segment Rename','Rename Segment As')
        setname = setname.strip()  #remove empty before and after
        if len(setname) == 0:
            slicer.util.messageBox('New Name Not Given. Quit!')
            return
        segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(selectname)
        segment = segmentationNode.GetSegmentation().GetSegment(segmentId)
        segment.SetName(setname)
        
        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

    def ontoolrenameModelButton(self):
        if len(self.ui.transModel_listWidget.selectedItems()) != 1:
            slicer.util.messageBox("Select One Model for Name Change")
            return
        selectname = self.ui.transModel_listWidget.selectedItems()[0].text()

        mw = slicer.util.lookupTopLevelWidget('qSlicerMainWindow')
        setname = qt.QInputDialog.getText(mw,'Model Rename','Rename Model As')
        setname = setname.strip()  #remove empty before and after
        if len(setname)==0:
            slicer.util.messageBox('New Name Not Given. Quit!')
            return
        cmodelnode = self.ExistSingletNodeByName(selectname)
        if cmodelnode is not None:
            cmodelnode.SetName(setname)

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

    def ontooldelSegButton(self):
        segmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID, 'No Segmentation Given')
        if segmentationNode is None:
            return
        if len(self.ui.transSegment_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No segments selected for delete")
            return
        for item in self.ui.transSegment_listWidget.selectedItems():
            segmentname = item.text()
            segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentname)
            segmentationNode.GetSegmentation().RemoveSegment(segmentId)

        self.initsegmodelToolsCollapsibleButton()

    def ontooldelModelButton(self):
        if len(self.ui.transModel_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No Models selected for delete")
            return
        
        for item in self.ui.transModel_listWidget.selectedItems():
            modelname = item.text()
            cmodelnode = self.ExistSingletNodeByName(modelname)
            if cmodelnode is not None:
                slicer.mrmlScene.RemoveNode(cmodelnode)

        self.initsegmodelToolsCollapsibleButton()

    def ontoolSeg2ModelButton(self):
        segmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID, 'No Segmentation Given')
        if segmentationNode is None:
            return
        if len(self.ui.transSegment_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No segments selected for convert")
            return

        # ask if overwritten
        yn = slicer.util.confirmYesNoDisplay(
                    "Model will be overwriten if alreay exists", 
                    windowTitle='Overwrite Information')
        if not yn:
            return

        for item in self.ui.transSegment_listWidget.selectedItems():
            segmentname = item.text()
            newnodename = segmentname + '_model'
            #..use SingletonOn() for automatic overwriten
            newModelNode = self.ExistSingletNodeByName(newnodename)
            if newModelNode is None:
                newModelNode = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLModelNode")
                newModelNode.SetSingletonOn()  # to overwrite

            # segmentName --> segmentID --> segment
            segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentname)
            csegment = segmentationNode.GetSegmentation().GetSegment(segmentId)
            result = slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentToRepresentationNode(
                csegment, newModelNode)
            if (not result) or (newModelNode.GetPolyData() is None):
                slicer.mrmlScene.RemoveNode(newModelNode)
                slicer.util.messageBox(
                    'Convert (' + segmentname + ') to surface model failed')

            # segment export change name automatically, reset here
            newModelNode.SetName(newnodename)

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

    def ontoolModel2SegButton(self):
        refVolNode = self.NodeofNodeID(
            self.ui.transImg_MRMLNodeComboBox.currentNodeID, 'No Reference Volume Selected')
        if refVolNode is None:
            return
        segmentationNode = self.NodeofNodeID(
            self.ui.transSegmentation_MRMLNodeComboBox.currentNodeID, 'No Segmentation Selected')
        if segmentationNode is None:
            return

        #selected models to convert
        if len(self.ui.transModel_listWidget.selectedItems()) == 0:
            slicer.util.messageBox("No models selected for convert")
            return
        yn = slicer.util.confirmYesNoDisplay(
            "segments will be overwriten if alreay exists", windowTitle='Overwrite Information')
        if not yn:
            return
        # convert
        for item in self.ui.transModel_listWidget.selectedItems():
            modelname = item.text()
            cmodelNode = self.ExistSingletNodeByName(modelname)
            if cmodelNode is None:
                slicer.util.messageBox(modelname+' Not Exist')
                return
            if cmodelNode.GetClassName() != 'vtkMRMLModelNode':
                slicer.util.messageBox("Selected (" + modelname + ") not surface. Ignored!")
                continue
            segname = modelname.replace('_Model', '')  #remove '_Model'
            done = self.logic.addModeltoSegmentation(cmodelNode, segmentationNode, refVolNode, segname, color=(0,1,1))
            if done is None:
                slicer.util.messageBox('Convert (' + cmodelNode.GetName() + ') to segment FAILED!'
                + '\n Check Model and Reference Volume/Segmentation Matching')

        self.initsegmodelToolsCollapsibleButton() #update node list

    def ontoolCreateLandmarkButton(self):
        setname = self.GenerateSingletNodeName('Landmark')
        if setname is None: #Name not given, or the node already exists
            return 
        markupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        markupNode.SetName(setname)
        markupNode.SetSingletonOn()

        markdisplaynode = markupNode.GetDisplayNode()
        markdisplaynode.SetTextScale(3)
        markdisplaynode.SetGlyphScale(2)  # relative
        markdisplaynode.SetGlyphSize(8)   # absolute
        markdisplaynode.SetColor(0.0, 1.0, 0.0)
        markdisplaynode.SetSelectedColor(0.0, 1.0, 0.0)
        
        n = markupNode.AddFiducial(30, 30, 10) #single landmark
        markupNode.SetNthFiducialLabel(n, setname +'_p')
        markupNode.SetNthFiducialVisibility(n, 1)

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

        slicer.util.messageBox('Single Landmark Node (' + setname +  ') created for edit')

    def ontoolCreateCurveButton(self):
        setname = self.GenerateSingletNodeName('Closed Curve')
        if setname is None: #Name not given, or the node already exists
            return 
        curveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
        curveNode.SetName(setname)
        curveNode.SetSingletonOn()
        self.ui.toolcutcurveName_lineEdit.text = setname

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

        slicer.util.messageBox('Curve (' + setname + ') created for manual edit')

    def ontoolCutSurfaceButton(self):
        modeltocut = self.NodeofNodeID(
            self.ui.toolSurfaceforcutNode_ComboBox.currentNodeID, 'No Model Selected to Cut')
        if modeltocut is None:
            return
        cutcurveNode = self.NodeofNodeID(
            self.ui.toolCutCurveNode_ComboBox.currentNodeID, 'No Cut Curve Given')
        if cutcurveNode is None:
            return

        modeltocut.GetDisplayNode().SetVisibility(True)
        
        setname = self.GenerateSingletNodeName('Cut Surface')
        if setname is None: #Name not given, or the node already exists
            return 
        patchnode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        patchnode.CreateDefaultDisplayNodes()
        patchnode.SetName(setname)
        patchnode.SetSingletonOn()  #to overwrite
        self.logic.cropsurface_bycurve(cutcurveNode, modeltocut, patchnode)
        patchnode.GetDisplayNode().SetColor(0.0, 0.5, 0.5)  #set as red
        patchnode.GetDisplayNode().SetOpacity(1.0)

        self.initsegmodelToolsCollapsibleButton() #Update Model Lists

        slicer.util.messageBox('Cutted surface patch created as (' + setname + ')')

    #-------for drawEAMCollapsibleButton--------- 
    def oninitEAMcurveButton(self):
        scaledmodelNode = self.NodeofNodeID(
            self.ui.contourmodel_MRMLNodeComboBox.currentNodeID, 'Not Valid MapModel Selected')
        if scaledmodelNode is None:
            return
        scaledmodelNode.GetDisplayNode().SetVisibility(True)
        self.ontoolCreateCurveButton()  # create closed curve

    def ongenEAMscarButton(self):
        modeltocut = self.NodeofNodeID(
            self.ui.contourmodel_MRMLNodeComboBox.currentNodeID, 'No mapModel to Cut Surface')
        if modeltocut is None:
            return
        cutcurveNode = self.NodeofNodeID(
            self.ui.scarCutlineNode_ComboBox.currentNodeID, 'No CutCurve Given')
        if cutcurveNode is None:
            return
        
        setname = self.GenerateSingletNodeName('Scar Model')
        if setname is None:
            return
        scarNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        scarNode.CreateDefaultDisplayNodes()
        scarNode.SetName(setname)
        scarNode.SetSingletonOn()  #to overwrite
        
        thickness = 2.0
        self.logic.generateEAMScarbyCut(cutcurveNode, modeltocut, scarNode, thickness)
        scarNode.GetDisplayNode().SetColor(1.0, 0.0, 0.0)  #set as red
        scarNode.GetDisplayNode().SetOpacity(1.0)

        #Add to segmentation. check refer Volume/Segmentation First
        refImgNode = self.NodeofNodeID(
            self.ui.scarcutrefImgNode_ComboBox.currentNodeID)
        segmentationNode = self.NodeofNodeID(
            self.ui.scarcutsegmentationNode_ComboBox.currentNodeID)
        if (refImgNode is None) or (segmentationNode is None):
            slicer.util.messageBox("Scar Model Generated. No segment added." 
                    +"\n Due to invalid volume/segmentation given.")
            return 
        else:
            refvolID = segmentationNode.GetNodeReferenceID('ReferVolumeID')
            if (refvolID is None) or (refvolID != refImgNode.GetID()):
                slicer.util.messageBox("Scar Model Generated. No segment added." 
                    +"\n Due to segmentation not refer to given volume.")
                return 
        
        done = self.logic.addModeltoSegmentation(scarNode, segmentationNode, refImgNode, 
                                                setname, color=(1,0,0))
        if done is None:
            slicer.util.messageBox('Convert (' + scarNode.GetName() + ') to segment FAILED!')
            seginfo = ' and Scar Segment Generated'
        else:
            seginfo = ' Without Segment to Img/Segmentation'

        #information
        slicer.util.messageBox('Scar Generated at (' + setname + ') ' + seginfo)

    #--------for genVolumeCollapsibleButton------ 
    # init segment list to select to generate volume
    def initgenVolumeCollapsibleButton(self):
        if not self.ui.genVolumeCollapsibleButton.collapsed:
            self.ui.genSelectedSeg_ComboBox.clear()
            segmentationNode = self.NodeofNodeID(
                self.ui.genSegmentation_MRMLNodeComboBox.currentNodeID)
            if segmentationNode is not None:
                for i in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
                    segment = segmentationNode.GetSegmentation().GetNthSegment(i)
                    self.ui.genSelectedSeg_ComboBox.addItem(segment.GetName())

    #get one segment as int volume for check
    def ongenIntVolumeButton(self):
        #create VolumeNode with name of self.logic.SetNodeNames['EAMcardiac_IntVolume']
        refvolNode = self.NodeofNodeID(
            self.ui.genRefVol_MRMLNodeComboBox.currentNodeID, 'Invalid Reference Volume')
        if refvolNode is None:
            return
        segmentationNode = self.NodeofNodeID(
            self.ui.genSegmentation_MRMLNodeComboBox.currentNodeID, 'Invalid Segmentation')
        if segmentationNode is None:
            return
        #evaluate segmentation and volume matching
        refvolID = segmentationNode.GetNodeReferenceID('ReferVolumeID')
        if (refvolID is None) or (refvolID != refvolNode.GetID()):
            slicer.util.messageBox("Segmentation not refer to select volume. Need reset!")
            return 

        segmentname = self.ui.genSelectedSeg_ComboBox.currentText
        if not segmentname:
            slicer.util.messageBox('No segment selected')
            return
        setname = self.GenerateSingletNodeName('Binary Volume')
        if setname is None:
            return
        IntVolNode = slicer.mrmlScene.AddNewNodeByClass(
                                "vtkMRMLScalarVolumeNode")
        IntVolNode.SetName(setname)
        IntVolNode.SetSingletonOn()
        self.logic.Segment2IntVolume(
            segmentationNode, segmentname, refvolNode, IntVolNode)
        slicer.util.messageBox('Volume created as (' + setname + ') Volume Node')

    #--------for ExportDCMCollapsibleButton--------
    def onexportDCMButton(self):
        #save DICOM RT
        expvolNode = self.NodeofNodeID(
            self.ui.exportVolume_MRMLNodeComboBox.currentNodeID, 'No exportVolume Given')
        if expvolNode is None:
            return
        expsegNode = self.NodeofNodeID(
            self.ui.exportSegmentation_MRMLNodeComboBox.currentNodeID, 'No exportSegmentation Given')
        if expsegNode is None:
            return
        #check volume and segmentation matching    
        refvolID = expsegNode.GetNodeReferenceID('ReferVolumeID')
        if (refvolID is None) or (refvolID != expvolNode.GetID()):
            yn = slicer.util.confirmYesNoDisplay(
                    "Segmentation not refer to select volume." + "\n Continue export?", 
                    windowTitle='DICOM Export')
            if not yn:
                return 
                
        #export
        expPtName = str(self.ui.exportPtName_lineEdit.text).strip()
        expPtID = str(self.ui.exportPtID_lineEdit.text).strip()
        expPtDate = str(self.ui.exportPtBirth_lineEdit.text).strip()
        expPtSex = str(self.ui.exportPtSex_lineEdit.text).strip()
        expDataDir = self.ui.exportDCM_PathLineEdit.currentPath
        if (not expPtName) or (not expPtID) or (not expPtDate) or (not expPtSex):
            slicer.util.messageBox('Invalid Export Patient Inforamtion')
            return
        if not os.path.isdir(expDataDir):
            slicer.util.messageBox('Invalid Directory to Export DICOM')
            return
        ptinfostr = '{:<20}'.format('Pt Name:') + expPtName + '\n' + \
            '{:<20}'.format('Pt ID:') + expPtID + '\n' + '{:<20}'.format('Pt BirthDate:') + \
            expPtDate + '\n' + '{:<20}'.format('Pt Sex:') + expPtSex + '\n' + \
            ' <CONFIRM> The Patient Information is Correct?(Y/N) '
        yn = slicer.util.confirmYesNoDisplay(
            ptinfostr, windowTitle='Confirm Patient information')
        if not yn:
            return

        ptdcmhead = {'PatientBirthDate' : expPtDate, 'PatientName' : expPtName,  
                    'PatientID' :  expPtID,   'PatientSex' : expPtSex,
                    'StudyDescription' : 'EAM Scar',  
                    'StudyDate' : datetime.datetime.today().strftime('%Y%m%d')}
        imgdcmhead = {'Modality' : 'CT',  'KVP': '120', 'SeriesDescription' : 'Binary EAMCardiacVolume', 'SeriesNumber' : '10'}
        segdcmhead = {'Modality' : 'RTSTRUCT',  'SeriesDescription' : 'EAMCardiac',    'SeriesNumber' : '20'}
        self.logic.savectsegDICOMRT(expvolNode, expsegNode, expDataDir, ptdcmhead, imgdcmhead, segdcmhead)

        slicer.util.messageBox('DICOM RT Save Volume and Segmentation DONE!')

    #--------gentLV17SegmentCollapsibleButton-------
    def initgentLV17SegmentCollapsibleButton(self):
        if not self.ui.gentLV17SegmentCollapsibleButton.collapsed:
            self.ui.epiLVsegment_ComboBox.clear()
            self.ui.endoLVsegment_ComboBox.clear()
            self.ui.endoRVsegment_ComboBox.clear()
            if self.ui.seg17SegmentationNode_ComboBox.currentNodeID is not None:
                segmentationNode = slicer.mrmlScene.GetNodeByID(
                    self.ui.seg17SegmentationNode_ComboBox.currentNodeID)
                if segmentationNode is not None:
                    for i in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
                        segment = segmentationNode.GetSegmentation().GetNthSegment(i)
                        self.ui.epiLVsegment_ComboBox.addItem(segment.GetName())
                        self.ui.endoLVsegment_ComboBox.addItem(segment.GetName())
                        self.ui.endoRVsegment_ComboBox.addItem(segment.GetName())

    def ongentSeptMidPtButton(self):
        cardiacImgNode = self.NodeofNodeID(
            self.ui.seg17RefImgNode_ComboBox.currentNodeID, 'No cardiac Volume Given')
        if cardiacImgNode is None:
            return
        cardiacsegmentationNode = self.NodeofNodeID(
            self.ui.seg17SegmentationNode_ComboBox.currentNodeID, 'Invalid Segmentation')
        if cardiacsegmentationNode is None:
            return
        epiLVsegment = self.ui.epiLVsegment_ComboBox.currentText
        if (not epiLVsegment) or len(epiLVsegment)==0:
            slicer.util.messageBox('No Epi-LV segment selected')
            return
        endoLVsegment = self.ui.endoLVsegment_ComboBox.currentText
        if (not endoLVsegment) or len(endoLVsegment)==0:
            slicer.util.messageBox('No Endo-LV segment selected')
            return
        endoRVsegment = self.ui.endoRVsegment_ComboBox.currentText
        if (not endoRVsegment) or len(endoRVsegment)==0:
            slicer.util.messageBox('No Edno-LV segment selected')
            return
        epiLVNode = self.NodeofNodeID(
            self.ui.epiLVModelNode_ComboBox.currentNodeID, 'Invalid Epi-LV Model')
        if epiLVNode is None:
            return
        
        slicer.util.messageBox('Input Check!')

    def ongentLV17ModelcutButton(self):
        apexNode = self.NodeofNodeID(
            self.ui.endoApexPtNode_ComboBox.currentNodeID, 'Invalid Apex Point')
        if apexNode is None:
            return
        baseNode = self.NodeofNodeID(
            self.ui.endoBasePtNode_ComboBox.currentNodeID, 'Invalid Base Point')
        if baseNode is None:
            return
        septmidNode = self.NodeofNodeID(
            self.ui.septMidPtNode_ComboBox.currentNodeID, 'Invalid Septal Middle Point')
        if septmidNode is None:
            return
        
        slicer.util.messageBox('Input Check!')

    def ongentLV17SegmentButton(self):
        cardiacImgNode = self.NodeofNodeID(
            self.ui.seg17RefImgNode_ComboBox.currentNodeID, 'No cardiac Volume Given')
        if cardiacImgNode is None:
            return
        cardiacsegmentationNode = self.NodeofNodeID(
            self.ui.seg17SegmentationNode_ComboBox.currentNodeID, 'Invalid Segmentation')
        if cardiacsegmentationNode is None:
            return
        endoLVsegment = self.ui.endoLVsegment_ComboBox.currentText
        if (not endoLVsegment) or len(endoLVsegment)==0:
            slicer.util.messageBox('No Endo-LV segment selected')
            return
        
        slicer.util.messageBox('Input Check!')
        
    #^^^^^^^^^^node util functions^^^^^^^^^^^^
    def GenerateSingletNodeName(self, nodetypeinfo):
        mw = slicer.util.lookupTopLevelWidget('qSlicerMainWindow')
        setname = qt.QInputDialog.getText(mw,'Create ' + nodetypeinfo, 'Set '+ nodetypeinfo + ' Name')
        setname = setname.strip()  #remove empty before and after
        if len(setname)==0:
            slicer.util.messageBox('New Name Not Given.')
            return None
        existNode = self.ExistSingletNodeByName(setname)
        if existNode is not None:
            slicer.util.messageBox(setname +  ' Already Exists.')
            return None
        return setname  #named node not exists, will generate 

    def ExistSingletNodeByName(self, nodename):
        # check node of nodename exists, and set as singleton if existing
        # to enhance nodename corresponding to node
        checkNode = slicer.mrmlScene.GetFirstNodeByName(nodename)
        if checkNode and (checkNode is not None):  # if exists
            if not checkNode.IsSingleton():
                checkNode.SetSingletonOn()
        else:
            checkNode = None
        return checkNode

    def NodeofNodeID(self, NodeID, errormessage=''):
        #get Node from given NodeID, if not exists, return None
        cNode = None
        if NodeID and (NodeID is not None):
            cNode = slicer.mrmlScene.GetNodeByID(NodeID)

        if (not cNode) or (cNode is None):
            if len(errormessage)>0:
                slicer.util.messageBox(errormessage)
            return None
        else:
            return cNode

    def getNumberOfNodes(self, nodename):
        availnodes = slicer.util.getNodes(pattern=nodename+'*')
        if (not availnodes):
            nodenum = 0
        else:
            nodenum = len(availnodes)
        return nodenum

    def getNodeList(self, nodetypelist):
        nodelist = vtk.vtkCollection()
        for nodetype in nodetypelist:
            for item in slicer.mrmlScene.GetNodesByClass(nodetype):
                if not slicer.vtkMRMLSliceLogic.IsSliceModelNode(item):
                    nodelist.AddItem(item)
        return nodelist

#cardiacRTLogic
class cardiacRTLogic(ScriptedLoadableModuleLogic):
    # All nodes created outside
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.SetNodeNames = {
            'EnsiteEAM_ColorTable': 'EnsiteEAM Map',
            'InsightMV_ColorTable': 'Insight Voltage',
            'InsightMS_ColorTable': 'Insight Activation',
        }
        self.EAMReader = EAMReadLib.cardiacEAMImport()
        self.InsightReader = EAMReadLib.cardiacInsightImport()
        self.cardiacSlicer = cardiacSlicerLib.slicerCardiac()
        self.modelView = cardiacSlicerLib.slicerModelView()

    # Initialize parameter node with default settings, only logging information
    def setDefaultParameters(self, parameterNode):
        if not parameterNode.GetParameter("ProgessLogging"):
            parameterNode.SetParameter(
                "ProgressLogging", "Start EAM Scar generation for CardiacRT:")

    #------Read EAM data as Models----------------------
    def readCarto(self, filename):
        return self.EAMReader.readCarto(filename)
    
    def readRhythmia(self, filename):
        return self.EAMReader.readRhythmia(filename)

    def readEnsiteVelocity(self, filename):
        return self.EAMReader.readVelocity(filename)
    
    def readcardiacInsight(self, dirname):
        return self.InsightReader.readInsight(dirname)
    
    #-----------3D View Display----------------------------------
    def getScalarMapNames(self, modelNode):
        return self.modelView.getModelScalarsName(modelNode)

    def getScalarRange(self, modelNode, selScalarName):
        return self.modelView.getScalarRange(modelNode, selScalarName)

    def showCardiacMap(self, modelNode, scalarName, colorNode, lowvalue, uppervalue):
        ColorTableName = colorNode.GetName()
        if ColorTableName == self.SetNodeNames['EnsiteEAM_ColorTable']:
            dispNode = self.modelView.showEnsiteMap(modelNode, scalarName, colorNode)
        elif ColorTableName == self.SetNodeNames['InsightMV_ColorTable']:
            dispNode = self.modelView.showInsightMap(modelNode, scalarName, colorNode,
                                        mapTitle='Voltage',
                                        minrange=lowvalue, maxrange=uppervalue)
        elif ColorTableName == self.SetNodeNames['InsightMS_ColorTable']:
            dispNode = self.modelView.showInsightMap(modelNode, scalarName, colorNode,
                                        mapTitle='Activation',
                                        minrange=lowvalue, maxrange=uppervalue)
        else:
            print('Cardiac EAM Data No Support Yet')
        #dispNode.SetViewNodeIDs(["vtkMRMLSliceNodeRed", "vtkMRMLViewNode1"])
        dispNode.SetVisibility(True)
        self.modelView.center3Dview()

    def createCardiacColorTable(self, ColorTableName):
        if ColorTableName == self.SetNodeNames['EnsiteEAM_ColorTable']:
            self.modelView.createEnsiteEAMcolormap(maxvalue=2.0, colorName = ColorTableName)
        elif ColorTableName == self.SetNodeNames['InsightMV_ColorTable']:
            self.modelView.createInsightMVcolormap(colorName = ColorTableName)
        elif ColorTableName == self.SetNodeNames['InsightMS_ColorTable']:
            self.modelView.createInsightMScolormap(colorName = ColorTableName)
        else:
            print(ColorTableName + ' No Support Yet')

    def hideColorbarinView(self):
        self.modelView.hideColorbar()

    #-----------Movel/Volume Registration----------------------------
    def createLandmarkSet(self, marksNode, markNum, prestr='mov', xypos=(50,0), color=(1,0,0)):
        self.cardiacSlicer.createMarkset(marksNode, markNum, prestr, xypos, color)

    def cardiacRegister(self, refdataNode, movdataNode, transformNode):
        dataclass = refdataNode.GetClassName()
        if dataclass == 'vtkMRMLModelNode':
            transNode = self.cardiacSlicer.register_ICPsurfs(
                refdataNode, movdataNode, transformNode)
        elif dataclass == 'vtkMRMLMarkupsFiducialNode':
            transNode = self.cardiacSlicer.register_Landmarkset(
                refdataNode, movdataNode, transformNode)
        elif dataclass == 'vtkMRMLScalarVolumeNode':
            transNode = self.cardiacSlicer.register_Volumes(
                refdataNode, movdataNode, transformNode)
        else:
            transNode = None

        return transNode

    def transformVolume(self, refVolNode, movVolNode, transformNode, resultVolNode):
        done = self.cardiacSlicer.transformVolume(
            refVolNode, movVolNode, transformNode, resultVolNode)
        return done

    # ---------Model and Segment Operation-------------------
    def addModeltoSegmentation(self, modelNode, segmentationNode, refVolumeNode, 
                            segname=None, color=(1, 1, 0)):
        done = self.cardiacSlicer.addModelinSegmentation(
            modelNode, segmentationNode, refVolumeNode, segname, color)
        return done

    #generate EAM scar closed volume
    def cropsurface_bycurve(self, cutcurveNode, modeltocut, patchNode):
        self.cardiacSlicer.cropSurface_bycurve(
            cutcurveNode, modeltocut, patchNode)

    def generateEAMScarbyCut(self, cutcurveNode, sourceNode, solidateNode, thickness=2.0):
        #combine cut and extrude to generate solidate cutted model (solidatenode)
        patchNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        self.cardiacSlicer.cropSurface_bycurve(
            cutcurveNode, sourceNode, patchNode)  # cut
        self.cardiacSlicer.solidateSurfpatch_byextrude(
            patchNode, solidateNode, extrude_thickness=thickness)  # extrude
        slicer.mrmlScene.RemoveNode(patchNode)          #clean and return
        return solidateNode

    #------save Segment into Int Volume
    def Segment2IntVolume(self, segmentationNode, selsegmentname, refVolumeNode, outputScaleNode, scalenum=100):
        self.cardiacSlicer.transSegtoIntVolume(
            segmentationNode, selsegmentname, refVolumeNode, outputScaleNode, scalenum)

    #---------Save DICOMRT
    def savectsegDICOMRT(self, imgNode, segmentationNode, outputDir, ptdcmhead, imgdcmhead, segdcmhead):
        #save one (CT) img node + one segmentation node as DICOMRT

        #...Create Subject HierachyNode
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)  # subject node
        patientItemID = shNode.CreateSubjectItem(shNode.GetSceneItemID(), "patient")  # create patient
        studyItemID = shNode.CreateStudyItem(patientItemID, "Save CT DICOM RT")  # create study

        volNodeShID = shNode.GetItemByDataNode(imgNode)
        shNode.SetItemParent(volNodeShID, studyItemID)  # Set Volume

        segNodeShID = shNode.GetItemByDataNode(segmentationNode)
        shNode.SetItemParent(segNodeShID, studyItemID)  # Set Segmentation

        #...export as DICOM RT   #import DicomRtImportExportPlugin
        exporter = DicomRtImportExportPlugin.DicomRtImportExportPluginClass()
        volexportables = exporter.examineForExport(volNodeShID)
        for exp in volexportables:  # Set Volume Tag after examine
            exp.confidence = 1.0  # set confident as reference
            for key in imgdcmhead:
                exp.setTag(key, imgdcmhead[key])
        segexportables = exporter.examineForExport(segNodeShID)
        for exp in segexportables:  # Set Series Tag after examine
            for key in segdcmhead.keys():
                exp.setTag(key, segdcmhead[key])
        #set common Tags required for each
        exportables = volexportables + segexportables
        for exp in exportables:
            exp.directory = outputDir
            for key in ptdcmhead.keys():
                exp.setTag(key, ptdcmhead[key])

        exporter.export(exportables)


#cardiacRTTest
class cardiacRTTest(ScriptedLoadableModuleTest):
    # Do whatever is needed to reset the state - typically a scene clear will be enough.
    def setUp(self):
        slicer.mrmlScene.Clear()

    # Run as few or as many tests as needed here.
    def runTest(self):
        self.setUp()
        self.test_cardiacRT()

    def test_cardiacRT(self):
        self.delayDisplay("Starting the test")
        # Get/create input data
        #import SampleData
        #registerSampleData()
        #inputVolume = SampleData.downloadSample('RTWorkflow1')
        self.delayDisplay('Loaded test data set')
        # inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        # self.assertEqual(inputScalarRange[0], 0)
        # Test the module logic
        logic = cardiacRTLogic()
        # Test algorithm with non-inverted threshold
        # logic.process(inputVolume, outputVolume, threshold, True)
        # outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        # self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.delayDisplay('Test passed')
