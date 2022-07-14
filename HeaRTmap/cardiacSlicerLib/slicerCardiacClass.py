#functions of operate Slicer
#...work on slicer node which has been created and evaluated outside
#...caller ensure node singleton and unique name

import slicer
import vtk
import math

#warp slicer functions for cardiacRT
class slicerCardiac:
    def __init__(self) -> None:
        pass
    #--------node creation function--------------
    def createMarkset(self, landmarkNode, markNum, prestr='fix', xypos = (50, 0), color=(0, 0, 1)):
        #xypos: initial xy pos. (50,0) for fix_set; (0,50) for mov_set
        #color: (0,0,1) for fix_set; (1,0,0) for mov_set

        #the Node has created and ensure singleton
        #..markupnode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        #..markupnode.SetName(landmarkName)  #('EAMLV-Landmarks')   

        for i in range(markNum):
            pname = prestr + str(i) + ':'
            n = landmarkNode.AddFiducial(xypos[0], xypos[1], (i-1)*50) 
            landmarkNode.SetNthFiducialLabel(n, pname)    #'EAM-LV-Apex'
            landmarkNode.SetNthFiducialVisibility(n,1)

        #set display
        markdisplaynode = landmarkNode.GetDisplayNode()
        markdisplaynode.SetTextScale(3)
        markdisplaynode.SetGlyphScale(3)   #relative
        markdisplaynode.SetGlyphSize(10)   #absolute
        markdisplaynode.SetColor(color)  
        markdisplaynode.SetSelectedColor(color)  

        return True
    
    def createSegmentation(self, segmentationName):
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode.CreateDefaultDisplayNodes() # needed for display
        segmentationNode.SetName(segmentationName)
        return segmentationNode

    #------- operate model/segment function-------
    def addModelinSegmentation(self, modelnode, segmentationnode, refvolumenode, segname=None, color=(1, 0, 0)):
        #add single model to segmentation, if segname exists, remove the segment, then recreate
        if segname is None:  # use Model Name as segment name in segmentation if not specified
            segname = modelnode.GetName()
        #remove segment if existing
        segmentId = segmentationnode.GetSegmentation().GetSegmentIdBySegmentName(segname)
        if (not segmentId) and (segmentId is not None):  # exists, then remove
            segmentationnode.GetSegmentation().RemoveSegment(segmentId)
        #tranform to segment
        defaultname = modelnode.GetName()  # default saving name
        segmentationnode.SetReferenceImageGeometryParameterFromVolumeNode(
            refvolumenode)

        done = slicer.modules.segmentations.logic(
        ).ImportModelToSegmentationNode(modelnode, segmentationnode)
        if not done:
            return None
        segmentationnode.GetSegmentation().GetSegment(
            defaultname).SetColor(color[0], color[1], color[2])
        segmentationnode.CreateBinaryLabelmapRepresentation()
        #set segname
        segmentId = segmentationnode.GetSegmentation().GetSegmentIdBySegmentName(defaultname)
        newsegment = segmentationnode.GetSegmentation().GetSegment(segmentId)
        newsegment.SetName(segname)  # set given name
        return True

    def addmultiModelinSegmentation(self, segmentationNode, modellist, refVolumeNode):
        #transfer list of models to segment, then add into the segmentation
        #imgsegsNode.SetName('CardiacImg-EAM-Segmentation')
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
            refVolumeNode)
        colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0], [0, 1, 1]]
        for md, umodelnode in enumerate(modellist):
            slicer.modules.segmentations.logic().ImportModelToSegmentationNode(
                umodelnode, segmentationNode)
            m = md % len(colors)
            segmentName = umodelnode.GetName()
            segmentationNode.GetSegmentation().GetSegment(segmentName).SetColor(
                colors[m][0], colors[m][1], colors[m][2])

        segmentationNode.CreateBinaryLabelmapRepresentation()
        return True

    #...cut surface a target patch and solidate for target
    def cropSurface_bycurve(self, cutcurvenode, cutmodelnode, cropSurfnode):
        #Purpose: extract subsurface from a surface using a markupline curve
        #curvenode: closed curve to cut cutmodelnode
        #cutnodename = 'Skin'

        #..set cropping curve
        loop = vtk.vtkSelectPolyData()
        loop.SetInputConnection(cutmodelnode.GetPolyDataConnection())
        loop.SetLoop(cutcurvenode.GetCurvePointsWorld()) 
        loop.GenerateSelectionScalarsOn()
        loop.SetSelectionModeToSmallestRegion()  #negative scalars inside
        loop.Update()                 #loop.GetOutput() 

        #..clips out positive region
        clip = vtk.vtkClipPolyData()
        clip.SetInputConnection(loop.GetOutputPort())
        clip.InsideOutOn()
        clip.GenerateClippedOutputOff()
        clip.SetValue(1)
        clip.Update()

        #these functions to get inside/outside part surface
        #clip.InsideOutOn();   clip.InsideOutOff()
        #clip.GenerateClippedOutputOff();  clip.GenerateClippedOutputOn()
        #clip.GetOutput();  clip.GetClippedOutput()

        #...clean isolcated points in surface
        clean_filter = vtk.vtkCleanPolyData()
        clean_filter.SetInputData(clip.GetOutput())
        clean_filter.SetTolerance(0.0)
        clean_filter.PointMergingOn()
        clean_filter.Update()

        #..connectiveity filter
        connectivity_filter = vtk.vtkConnectivityFilter()
        connectivity_filter.SetInputConnection(clean_filter.GetOutputPort())
        connectivity_filter.Update()

        #...save into new node
        #cropSurfnode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        cropSurfnode.SetAndObservePolyData(connectivity_filter.GetOutput())
        cropSurfnode.CreateDefaultDisplayNodes()
        #cropSurfnode.SetName('Crop-out Surface')
        return cropSurfnode  #return cropped surface

    #...solidate surface patch as closed surface that can be segments
    def solidateSurfpatch_byextrude(self, extmodnode, solidmodelnode, extrude_thickness=5.0):
        #modnodename = 'crop'  #name of the model/surface node to be solidate
        #extmodnode = slicer.mrmlScene.GetFirstNodeByName(surfnodename)
        #polydata = extmodnode.GetPolyData()
        #extrude_thickness = 6.0     #unit mm

        #...clean isolcated points in surface
        clean_filter = vtk.vtkCleanPolyData()
        clean_filter.SetInputData(extmodnode.GetPolyData())
        clean_filter.SetTolerance(0.0)
        clean_filter.PointMergingOn()
        clean_filter.Update()

        #...extrude 
        extrude_filter = vtk.vtkLinearExtrusionFilter()
        extrude_filter.SetInputData(clean_filter.GetOutput())
        extrude_filter.SetExtrusionTypeToNormalExtrusion()
        extrude_filter.SetScaleFactor(extrude_thickness)   #number of mm
        extrude_filter.CappingOn()
        extrude_filter.Update()

        #check consistent surface normals
        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputConnection(extrude_filter.GetOutputPort())
        triangle_filter.Update()

        #smooth sharp edge
        normals_filter = vtk.vtkPolyDataNormals()
        normals_filter.SetInputConnection(triangle_filter.GetOutputPort())
        normals_filter.FlipNormalsOn()
        normals_filter.Update()

        #put into new node
        #solidmodelnode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        solidmodelnode.SetAndObservePolyData(normals_filter.GetOutput())
        solidmodelnode.CreateDefaultDisplayNodes()
        #solidmodelnode.SetName('Solidated Surface')
        return solidmodelnode
    
    def transSegtoIntVolume(self, segmentationNode, selsegname, refVolumeNode, outputScaleNode, scalenum=100):
        #output selected segment into Integer volume
        segLabelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        segLabelNode.SetName('Segmment LabelVolume')
        segmentIds = vtk.vtkStringArray()
        segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(selsegname)
        segmentIds.InsertNextValue(segmentId)
        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(
            segmentationNode, segmentIds, segLabelNode, refVolumeNode)

        #copy labelmap as volumeNode
        #outputScaleNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVolumeNode")
        slicer.modules.volumes.logic().CreateScalarVolumeFromVolume(
             slicer.mrmlScene, outputScaleNode, segLabelNode)  #(outputVolume, inputVolume)
        assert(outputScaleNode is not None)

        #reset as CT number
        imageData = slicer.util.arrayFromVolume(outputScaleNode)
        imageData *= int(scalenum)
        imageData[imageData == 0] = int(-1000)   #set as CT range
        slicer.util.arrayFromVolumeModified(outputScaleNode) #set calenum as inside

        slicer.mrmlScene.RemoveNode(segLabelNode)

        return outputScaleNode

    #-------------Rgistration Functions-----------------
    #transformNode already exits, overwrite it
    def register_Landmarkset(self, refmarknode, movmarknode, transformnode):
        #transformNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        #transformNode.SetName(transformName)  
        parameters = {}
        parameters["saveTransform"]   = transformnode.GetID() 
        parameters["fixedLandmarks"]  = refmarknode.GetID() 
        parameters["movingLandmarks"] = movmarknode.GetID()     
        parameters['transformType']   = 'Rigid' 
        fiduciaReg = slicer.modules.fiducialregistration
        slicer.cli.runSync(fiduciaReg, None, parameters)  #run the registration
        return transformnode

    def register_ICPsurfs(self, refmodelnode, movmodelnode, transformnode, 
                        transformType=0, numIterations=100):
        #Purpose: Rigid surface registration using ICP
        icpTransform = vtk.vtkIterativeClosestPointTransform()
        icpTransform.SetSource(movmodelnode.GetPolyData())
        icpTransform.SetTarget(refmodelnode.GetPolyData())
        if transformType == 0:  # default ICP
            icpTransform.GetLandmarkTransform().SetModeToRigidBody()
        elif transformType == 1:
            icpTransform.GetLandmarkTransform().SetModeToSimilarity()
        elif transformType == 2:
            icpTransform.GetLandmarkTransform().SetModeToAffine()
        else:
            return None

        icpTransform.SetMaximumNumberOfIterations(numIterations)
        icpTransform.Modified()
        icpTransform.Update()

        #transformNode = slicer.vtkMRMLTransformNode()  # Create transform
        transformnode.SetMatrixTransformToParent(icpTransform.GetMatrix())
        transformnode.SetNodeReferenceID(
            slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), movmodelnode.GetID())
        transformnode.SetNodeReferenceID(
            slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), refmodelnode.GetID())

        return transformnode

    def register_Volumes(self, refvolnode, movvolnode, transformnode):
        #..use Elatix, need install Elastix Module
        #from Elastix import ElastixLogic
        #logic = ElastixLogic()
        #RegistrationPresets_ParameterFilenames = 5
        #parameterFilenames = logic.getRegistrationPresets()[0][RegistrationPresets_ParameterFilenames]
        #logic.registerVolumes(fixedVolumeNode,  movingVolumeNode,
        #                      parameterFilenames = parameterFilenames,
        #                      outputVolumeNode = outputVolume)
        #..use Brainfit
        #outputTransform = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        regnode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
        parameters = {
                'fixedVolume':       refvolnode,
                'movingVolume':      movvolnode,
                'linearTransform':   transformnode,
                'outputVolume':      regnode,
                'transformType':     'Rigid',       
                'initializeTransformMode': 'useMomentsAlign',
                'interolationMode':    'Linear', 
                'samplingPercentage':  0.5
            }
            #'maskProcessingMode':  'ROI',     #NOMASK, ROIAUTO, ROI
            #'fixedBinaryVolume':   refvoinode,
            #'movingBinaryVolume':  rthdnode,  #also use this ROI
            #'ROIAutoDilateSize':   10,
        slicer.cli.runSync(slicer.modules.brainsfit, parameters=parameters)
        slicer.mrmlScene.RemoveNode(regnode)  #only generate transform
        return transformnode

    def transformVolume(self, refvolnode, movvolnode, transformnode, resultnode, defaultvalue=-1000):
        parameters = {}
        parameters['referenceVolume'] = refvolnode
        parameters['inputVolume'] = movvolnode
        parameters['outputVolume'] = resultnode
        parameters['pixelType'] = 'float'
        parameters['warpTransform'] = transformnode
        parameters['interpolationMode'] = 'Linear'  #NearestNeighbor, Linear
        parameters['inverseTransform'] = False
        parameters['defaultValue'] = defaultvalue   #-1000 for CT, 0 for other 
        parameters['numberofThreads'] = -1
        done = slicer.cli.run(slicer.modules.brainsresample, None, parameters, True)
        return done

    #...no needed any more
    def CreateEAMvol_asScaledImg(self, imgsegsNode, selsegmentname, scaledmodelNode, refVolumeNode):
        #Purpose: output selsegmentname as volume matching with refVolumeNode
        #   if has scaledmodelNode, use the node scale to color tos volume structure surface
       
        #output selected model labelmap volume
        outputLabelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        segmentIds = vtk.vtkStringArray()
        segmentId = imgsegsNode.GetSegmentation().GetSegmentIdBySegmentName(selsegmentname)
        segmentIds.InsertNextValue(segmentId)
        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(imgsegsNode, segmentIds, outputLabelNode, refVolumeNode)

        #color surface based on model scales
        scaledmodelNode = outputLabelNode
        if scaledmodelNode is not None: 
            surfscales = scaledmodelNode.GetPolyData().GetPointData().GetArray('Map data')
            if surfscales is not None:
                scalelabelvolumenode = self.scaleBinVol_frommodel(outputLabelNode, scaledmodelNode)
            
        return scalelabelvolumenode

    #...transform landmark to sphere model/segmentation 
    def genspheremodel_fromlandmarks(self, landmarknode, radius):
        #markupnode=slicer.util.getNode(landmarknodename) #Get a reference to the markup
        numFids = landmarknode.GetNumberOfFiducials()
        radius = 5  #5mm
        markstr = ''
        markpos = [0.0, 0.0, 0.0]    #position in ras coordinate
        for i in range(numFids):
            landmarknode.GetNthFiducialPosition(i, markpos)
            landmarknode.GetNthFiducialLable(i, markstr)
            #world = [0,0,0,0]
            #markupnode.GetNthFiducialWorldCoordinates(0,world)
            #the world position is the RAS position with any transform matrices applied
            #print(i,": RAS =",ras,", world =",world)
            fidspherenode = self.createspheremodel(markpos, radius, markstr)
    
    def createspheremodel(self, centpointCoord, radius, setname):
        #create sphere model
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(centpointCoord)
        sphere.SetRadius(radius)
        sphere.SetPhiResolution(30)
        sphere.SetThetaResolution(30)
        sphere.Update()
        #Create model node and add to scene
        umodelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        umodelNode.SetAndObservePolyData(sphere.GetOutput())
        umodelNode.SetName(setname)
        umodelNode.CreateDefaultDisplayNodes()
        #a = arrayFromModelPoints(umodelNode)
        #a[:,2] = a[:,2] * 2.5  # change Y scaling
        #arrayFromModelPointsModified(umodelNode)
        #model node to segmentation
        return umodelNode
    
    def computeMeanSurfDistance(self, sourceModel, targetModel, transformNode):
        sourcePolyData = sourceModel.GetPolyData()
        targetPolyData = targetModel.GetPolyData()

        cellId = vtk.mutable(0)
        subId = vtk.mutable(0)
        dist2 = vtk.mutable(0.0)
        locator = vtk.vtkCellLocator()
        locator.SetDataSet(targetPolyData )
        locator.SetNumberOfCellsPerBucket( 1 )
        locator.BuildLocator()

        totalDistance = 0.0
        sourcePoints = sourcePolyData.GetPoints()
        spn = sourcePoints.GetNumberOfPoints()
        m = vtk.vtkMath()
        for sourcePointIndex in range(spn):
            sourcePointPos = [0, 0, 0]
            sourcePoints.GetPoint(sourcePointIndex, sourcePointPos)
            transformedSourcePointPos = [0, 0, 0, 1]
            #transformNode.GetTransformToParent().TransformVector(sourcePointPos, transformedSourcePointPos)
            sourcePointPos.append(1)  #[x, y, z, 1]
            transformNode.GetTransformToParent().MultiplyPoint(sourcePointPos, transformedSourcePointPos)
            #transformedPoints.InsertNextPoint(transformedSourcePointPos)
            #transformedSourcePointPos.pop()
            surfacePoint = [0, 0, 0]
            locator.FindClosestPoint(transformedSourcePointPos, surfacePoint, cellId, subId, dist2 )
            totalDistance = totalDistance + math.sqrt(dist2)

        return ( totalDistance / spn )
    

##RUN in Slicer Python 
#import sys    #need include the path for slicer to recognize subfunction
#sys.path.append('Z:/HW-Research/CardiacRT-EAM-Project/CardiacRT-Slicer-Scripts/') 
#import cardiacRT_slicer_Op
#cardiacRT = cardiacRT_slicer_Op.cardiacRT_slicer_Op()
#EAMmarks = cardiacRT.createmovmarks_fromEAM()
#IMGmarks = cardiacRT.createrefmarks_fromIMG()

