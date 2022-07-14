import slicer
import numpy as np
import vtk
#Class to automatical create LV 17 Seg

class LV17Seg():
    def __init__(self) -> None:
        self.LVepisurf = self.RVepisurf = None
        self.apex_point = self.base_point = self.septmid_point = None
        self.apiseg_point = self.midseg_point = self.centaxis_point = None
    
    #------------Set/Initialize Required Data Nodes-----------------
    def setLVepiSurf(self, LVepisurfNode):
        tmpPoly = LVepisurfNode.GetPolyData()        
        self.LVepisurf = self.vtk_trianglePolySurf(tmpPoly)  

    def setRVepiSurf(self, RVepiSurfNode):
        tmpPoly = RVepiSurfNode.GetPolyData()
        self.RVepisurf = self.vtk_trianglePolySurf(tmpPoly)
    
    #set RV epicardium mesh from segment with additional margin to the segment
    def setRVepiSurf_Segment(self, segmentationNode, segmentID, refVolumeNode, margin = [4,4,3]):
        tmpmodelNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
        if any(r > 1 for r in margin):  #need margin
            self.slicer_segmentDilate(segmentationNode, segmentID, refVolumeNode, kernelSize=margin, dillatemodelNode=tmpmodelNode)
        else:
            self.slicer_segment2model(segmentationNode, segmentID, tmpmodelNode)
        
        self.RVepisurf = self.vtk_trianglePolySurf(tmpmodelNode.GetPolyData())

        #clean tmpnode
        slicer.mrmlScene.RemoveNode(tmpmodelNode)

    #set LV coordinate system Long Axis from apex and base mark points
    def setLongAxisMarks(self, apexmarkupNode, basemarkupNode):
        pos = [0,0,0]
        apexmarkupNode.GetNthControlPointPosition(0,pos)  #single markup point
        ap = np.array(pos)
        basemarkupNode.GetNthControlPointPosition(0,pos)
        bp = np.array(pos)
        self.longaxis = (bp-ap)/np.linalg.norm(bp-ap) #Z
        #divide Apex to Base
        self.apex_point = ap
        self.base_point = bp
        self.apiseg_point = ap + 1/3*(bp - ap)
        self.midseg_point = ap + 2/3*(bp - ap)
        self.centaxis_point   = ap + 1/2*(bp - ap)

    #set septal middle point from a markup point
    def setSeptMidpoint(self, midmarkupNode):
        pos = [0,0,0]
        midmarkupNode.GetNthControlPointPosition(0, pos)  #single markup point
        self.septmid_point = np.array(pos)

    #------------Generate Coordinate System----------------------
    #determine septalmidpt by RV, LV surface
    def genSeptMidpt_LvRvCollide(self):
        #use expand RVepisurf for surf collision
        #collide to get cutting line for septal surface patch 
        collidepts = self.vtk_collideSurfs(self.LVepisurf, self.RVepisurf)
        #generate and smooth cutline
        septalcurve = self.vtk_polyCardinalInterp(collidepts, intp=2, closed=True)
        #get septal surface by cutting LV with above closed collide curve
        septalsurf = self.vtk_clipsurfbycurve(self.LVepisurf, septalcurve.GetPoints())
        #get septal cut points
        septmidcutpts = self.vtk_cutlineSurfPlane(septalsurf, self.centaxis_point, self.longaxis)
        #get cut middle line, not closed
        septmidline = self.vtk_polyCardinalInterp(septmidcutpts, intp=3, closed=False)
        #get septal midpoint
        septalmidpt = self.vtk_midpolycurve(septmidline)

        self.septmid_point = septalmidpt #get the middle point
        return septalmidpt  #np.aray([])
    
    #build LV Coordinate System
    def buildLVcoordinate(self):
        #...setLongAxis First
        #apex/base/sept(center septum) points on LV endocrium surface
        sept_point = self.septmid_point
        #project sept_point to longaxis 
        sp = np.array(sept_point)
        self.sept_point = sp
        asl = self.sept_point - self.apex_point
        abl = self.base_point - self.apex_point
        self.septprj_point = self.apex_point + np.dot(asl, abl) / np.dot(abl, abl) * abl

        #build LV coordinate vector
        tmpt = self.sept_point - self.septprj_point
        self.shortaxis  = tmpt/np.linalg.norm(tmpt)  #Y
        normaxis = np.cross(self.shortaxis, self.longaxis)
        self.normaxis = normaxis / np.linalg.norm(normaxis) #X

        #reformat as column vector
        longaxis  = np.reshape(self.longaxis,  (3,1)) #Z
        shortaxis = np.reshape(self.shortaxis, (3,1)) #Y
        normaxis  = np.reshape(self.normaxis,  (3,1)) #X
        self.coordmat = np.concatenate((normaxis, shortaxis, longaxis), axis=1)
    
    #-----------Main Output Function---------------------
    #save generate LVSegment to the segmentationNode
    #..assume all setting is done
    def GenerateLV17Seg(self, segmentationNode, endoLVsegmentID, refVolumeNode, result_segmentationNode=None):
        #create result segmentationNode
        #resultsegmentationNode=slicer.mrmlScene.AddNode(slicer.vtkMRMLSegmentationNode())
        #resultsegmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(refVolumeNode)
        if result_segmentationNode is None:  # use segmentationNode as result
            result_segmentationNode = segmentationNode
        #else: result_segmentationNode has been created before calling

        #build LV coordinate
        #self.genSeptMidpt_LvRvCollide()  # create septmidpt by collision, this should be ready prior to this call
        self.buildLVcoordinate()

        #prepare endoLV for subtraction
        endoLVlabelmapNode = slicer.mrmlScene.AddNode(
            slicer.vtkMRMLLabelMapVolumeNode)
        self.slicer_segment2labelmap(
            segmentationNode, endoLVsegmentID, refVolumeNode, endoLVlabelmapNode)
        # tranform to Not for subtract
        self.slicer_labelmapLogicNot(endoLVlabelmapNode)

        #generate subSegment Models
        lvsegs  = self.getbasalclosedsegs()
        lvsegs += self. getmiddleclosedsegs()
        lvsegs += self.getapicalclosedsegs()
        #subtract endo-lV and create subSegment
        for item in lvsegs:   #[{'segName', 'segID''closedSeg'}]
            segName = item['segName'] + '_' + str(item['segID'])
            segpoly = item['ClosedSeg']
            #subtract to get LV-subSegment
            segmentID = self.slicer_poly2segment(
                segpoly, result_segmentationNode, segName+'_ext')  #model to segment
            self.slicer_segmentsLogicAnd(
                endoLVlabelmapNode, result_segmentationNode, segmentID, refVolumeNode, segName)  # remove LVpart
            #smoothing segments
            #......

        #clean and return
        slicer.mrmlScene.RemoveNode(endoLVlabelmapNode)
        return True

    #---------------Get closeSegs---------------
    def getbasalclosedsegs(self):
        #no toppt need, get all to LV base
        #botpt: top and bottom point along apex-base 
        #LVcordmat: LV coordinate matrix 
        #...related to sept_point defined short_axis (Y)
        #...apex-base define long_axis (Z)
        #...Y-Z norm: x
        segAngles = np.array((240, 300, 0, 60, 120, 180)) #seg 1-6
        normAngles = (segAngles+90)*np.pi/180  #norm vector angles, in randial
        #angles norm to seg in 60 degree interval from 1-6
        vectx = np.cos(normAngles)
        vecty = np.sin(normAngles)
        AN = len(normAngles)
        nvectors = np.zeros((3, AN)) #Norm Vectors
        for i in range(AN):
            nvectors[:,i] = np.matmul(self.coordmat, np.array((vectx[i], vecty[i],0)).reshape(3,1))
        
        #long axis cutting plane
        nbt_plane = vtk.vtkPlane()
        nbt_plane.SetOrigin(self.midseg_point) #from bottom(apex) point
        nbt_plane.SetNormal(self.longaxis)  #toward base
        basalsegs = []
        for i in range(AN):
            nlt_plane = vtk.vtkPlane()
            nlt_plane.SetOrigin(self.septprj_point)  #always use this point
            nlt_plane.SetNormal(nvectors[:,i])   #Norm for n225_vect plane

            nr_norm = nvectors[:,(i+1)%AN] * (-1)    #norm but to inside
            nrt_plane = vtk.vtkPlane()
            nrt_plane.SetOrigin(self.septprj_point)  #always use this point
            nrt_plane.SetNormal(nr_norm)  #norm for n315_vect but to inside

            planes = vtk.vtkPlaneCollection()
            planes.AddItem(nbt_plane)
            planes.AddItem(nlt_plane)
            planes.AddItem(nrt_plane)

            basseg = self.clipclosedsurface(self.LVpolydata, planes)

            basalsegs.append({'segName': 'basal', 'segID':i+1, 'closedSeg': basseg})

        return basalsegs
    
    def getmiddleclosedsegs(self):
        #botpt: top and bottom point along apex-base 
        #longaxis: axis vector from botpt (apex) to topppt (1/3) apex-base
        #LVcordmat: LV coordinate matrix 
        #...related to sept_point defined short_axis (Y)
        #...apex-base define long_axis (Z)
        #...Y-Z norm: x
        segAngles = np.array((240, 300, 0, 60, 120, 180)) #seg 7-12
        normAngles = (segAngles+90)*np.pi/180 #norm vector angles, in randial
        #angles norm to seg in 60 degree interval from 1-6
        vectx = np.cos(normAngles)
        vecty = np.sin(normAngles)
        AN = len(normAngles)
        nvectors = np.zeros((3, AN)) #Norm Vectors
        for i in range(AN):
            nvectors[:,i] = np.matmul(self.coordmat, np.array((vectx[i], vecty[i],0)).reshape(3,1))
        
        #long axis cutting plane
        nbt_plane = vtk.vtkPlane()
        nbt_plane.SetOrigin(self.apiseg_point)     #from bottom(apex) point
        nbt_plane.SetNormal(self.longaxis) #toward base

        ntp_plane = vtk.vtkPlane()                 #toppt
        ntp_plane.SetOrigin(self.midseg_point)     #from toppt
        ntp_plane.SetNormal(self.longaxis*(-1)) #get below surface

        midsegs = []
        for i in range(AN):
            nlt_plane = vtk.vtkPlane()
            nlt_plane.SetOrigin(self.septprj_point)  #always use this point
            nlt_plane.SetNormal(nvectors[:,i])  #Norm for n225_vect plane

            nr_norm = nvectors[:,(i+1)%AN] * (-1)    #norm but to inside
            nrt_plane = vtk.vtkPlane()
            nrt_plane.SetOrigin(self.septprj_point)  #always use this point
            nrt_plane.SetNormal(nr_norm)  #norm for n315_vect but to inside

            planes = vtk.vtkPlaneCollection()
            planes.AddItem(nbt_plane)
            planes.AddItem(nlt_plane)
            planes.AddItem(nrt_plane)

            midseg = self.clipclosedsurface(self.LVpolydata, planes)

            midsegs.append({'segName': 'middle', 'segID':i+7, 'closedSeg': midseg})

        return midsegs
    
    def getapicalclosedsegs(self):
        #toppt, botpt: top and bottom point along apex-base 
        #longaxis: axis vector from botpt (apex) to topppt (1/3) apex-base
        #LVcordmat: LV coordinate matrix 
        #...related to sept_point defined short_axis (Y)
        #...apex-base define long_axis (Z)
        #...Y-Z norm: x
        segAngles = np.array((225, 315, 45, 135)) #seg 13-16
        normAngles = (segAngles+90)*np.pi/180 #norm vector angles, in randial
        #angles norm to seg in 60 degree interval from 1-6
        vectx = np.cos(normAngles)
        vecty = np.sin(normAngles)
        AN = len(normAngles)
        nvectors = np.zeros((3, AN)) #Norm Vectors
        for i in range(AN):
            nvectors[:,i] = np.matmul(self.coordmat, np.array((vectx[i], vecty[i],0)).reshape(3,1))

        nbt_plane = vtk.vtkPlane()
        nbt_plane.SetOrigin(self.apex_point)  #from bottom(apex) point
        nbt_plane.SetNormal(self.longaxis)    #toward base

        ntp_plane = vtk.vtkPlane()         #toppt
        ntp_plane.SetOrigin(self.apiseg_point)  #from toppt
        ntp_plane.SetNormal(self.longaxis*(-1)) #get below surface

        apisegs=[]
        for i in range(AN):  #rotate through to get segment 13, 14, 15, 16
            nlt_plane = vtk.vtkPlane()
            nlt_plane.SetOrigin(self.septprj_point)  #always use this point
            nlt_plane.SetNormal(nvectors[:,i])    #Norm for n225_vect plane

            nrt_norm = nvectors[:, (i+1)%AN]*(-1) #norm for next vect but to inside
            nrt_plane = vtk.vtkPlane()
            nrt_plane.SetOrigin(self.septprj_point)  
            nrt_plane.SetNormal(nrt_norm)  

            planes = vtk.vtkPlaneCollection()
            planes.AddItem(ntp_plane)
            planes.AddItem(nbt_plane)
            planes.AddItem(nlt_plane)
            planes.AddItem(nrt_plane)

            apiseg = self.__clipclosedsurface(self.LVpolydata, planes)

            apisegs.append({'segName': 'apical', 'SegID': i+13, 'closedSeg': apiseg})
        
        return apisegs

    #-------------Slicer Segment and Model tool Functions-----------------
    #segment --> labelmap :::single segment to labelmap.
    def slicer_segment2labelmap(self, segmentationNode, segmentId, refVolumeNode, seglabelmapNode):
        #segmentationNode=slicer.mrmlScene.AddNode(slicer.vtkMRMLSegmentationNode())
        segmentIDs = vtk.vtkStringArray()
        segmentIDs.InsertNextValue(segmentId)
        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(
            segmentationNode, segmentIDs, seglabelmapNode, refVolumeNode)

    #labelmap --> segment; return segmentID
    def slicer_labelmap2segment(self, labelmapNode, segmentationNode, segmentName):
        segment = slicer.vtkSlicerSegmentationsModuleLogic.CreateSegmentFromLabelmapVolumeNode(labelmapNode, segmentationNode)
        segment.SetName(segmentName)
        segment.SetColor(0, 1, 1)
        segmentationNode.GetSegmentation().AddSegment(segment)
        segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegment(segment) 
        return segmentId

    #segment --> model
    def slicer_segment2model(self, segmentationNode, segmentID, modelNode):
        segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentToRepresentationNode(
                    segment, modelNode)
        if (modelNode.GetPolyData() is None):
            return False
        else:
            return True

    #model   --> segment; return segmentID
    def slicer_model2segment(self, modelNode, segmentationNode, refVolumeNode, segmentName):
        #transfer model to segment in new segmentation, so only 1 segment 
        tmpsegmentationNode=slicer.mrmlScene.AddNode(slicer.vtkMRMLSegmentationNode()) 
        tmpsegmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(refVolumeNode)
        slicer.vtkSlicerSegmentationsModuleLogic.ImportModelToSegmentationNode(
            modelNode, tmpsegmentationNode)
        tmpsegmentationNode.CreateBinaryLabelmapRepresentation()        #for show in 3D

        #transfer to labelmap
        tmpsegmentId = tmpsegmentationNode.GetSegmentation().GetNthSegmentID(0)  #only one segmentation
        tmplabelmapNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLLabelMapVolumeNode)
        self.slicer_segment2labelmap(tmpsegmentationNode, tmpsegmentId, refVolumeNode, tmplabelmapNode)
        
        #transfer to segment with return
        segmentID = self.slicer_labelmap2segment(tmplabelmapNode, segmentationNode, segmentName)

        #clean
        slicer.mrmlScene.RemoveNode(tmpsegmentationNode)
        slicer.mrmlScene.RemoveNode(tmplabelmapNode)
        
        #Not use because can not get segment
        #slicer.vtkSlicerSegmentationsModuleLogic.ImportModelToSegmentationNode(modelNode, segmentationNode)
        #segmentationNode.CreateBinaryLabelmapRepresentation()  #for show in 3D
        return segmentID
    
    #polydata --> segment
    def slicer_poly2segment(self, polydata, segmentationNode, segmentName):
        tmpmodel = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
        tmpmodel.SetAndObservePolyData(polydata) #poly-->model
        #model-->segment
        segment = self.slicer_model2segment(tmpmodel, segmentationNode, segmentName)
        slicer.mrmlScene.RemoveNode(tmpmodel)
        return segment

    #dilate segment, transfer as modelNode if modelNode given
    def slicer_segmentDilate(self, segmentationNode, opsegmentId, refVolumeNode, kernelSize = [4,4,3], dillatemodelNode=None):
        #segment to labelmap for vtk dilate
        segname = segmentationNode.GetSegmentation().GetSegment(opsegmentId).GetName()
        segLabelmapNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLLabelMapVolumeNode)
        self.slicer_segment2labelmap(segmentationNode, opsegmentId, refVolumeNode, segLabelmapNode)

        #dilate labelmapvolume
        dilatefilter = vtk.vtkImageDilateErode3D()
        dilatefilter.SetInputData(segLabelmapNode.GetImageData())
        dilatefilter.SetDilateValue(1)
        dilatefilter.SetErodeValue(0)
        dilatefilter.SetKernelSize(kernelSize[0], kernelSize[1], kernelSize[2])
        dilatefilter.Update()

        #get dilated segment to segmentation
        segLabelmapNode.SetAndObserveImageData(dilatefilter.GetOutput())
        newsegname = segname + '_dilate'
        segmentId = self.slicer_labelmap2segment(segLabelmapNode, segmentationNode, newsegname)
        #segment = slicer.vtkSlicerSegmentationsModuleLogic().CreateSegmentFromLabelmapVolumeNode(segLabelmapNode, segmentationNode)
        
        #generate ModelNode
        if dillatemodelNode is not None:
            self.slicer_segment2model(segmentationNode, segmentId, dillatemodelNode)

        return segmentId
    
    #Logic_Not labelmapNode
    def slicer_labelmapLogicNot(self, labelmapNode):
        #labelmapNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLLabelMapVolumeNode)
        
        #logic operation -- And
        logic = vtk.vtkImageLogic()
        logic.SetInput1Data(labelmapNode.GetImageData())
        logic.SetOperationToNot()
        logic.SetOutputTrueValue(True)
        logic.Update()

        #labelmap to segment
        labelmapNode.SetAndObserveImageData(logic.GetOutput())

    #logic_And two segments to generarte new segment
    def slicer_segmentsLogicAnd(self, targetLabelmapNode, segmentationNode, opsegmentID, refVolumeNode, resultsegName):
        #create tmp labelmapvolume
        tmplabelmapNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLLabelMapVolumeNode)
        self.slicer_segment2labelmap(segmentationNode, opsegmentID, refVolumeNode, tmplabelmapNode)
        
        #logic operation -- And
        logic = vtk.vtkImageLogic()
        logic.SetInput1Data(tmplabelmapNode.GetImageData())
        logic.SetInput2Data(targetLabelmapNode.GetImageData())
        logic.SetOperationToAnd()
        logic.SetOutputTrueValue(True)
        logic.Update()

        #labelmap to segment
        tmplabelmapNode.SetAndObserveImageData(logic.GetOutput())
        segmentId = self.slicer_labelmap2segment(tmplabelmapNode, segmentationNode, resultsegName)

        #clean
        slicer.mrmlScene.RemoveNode(tmplabelmapNode)

        return segmentId

    #--------------vtk polydata process-----------------------------
    #trangular polydata : necessary for effective collision
    def vtk_trianglePolySurf(self, polyData):
        #trangular
        tri_converter = vtk.vtkTriangleFilter()
        tri_converter.SetInputDataObject(polyData)
        tri_converter.Update()
        #stripper 
        stripper = vtk.vtkStripper()
        stripper.SetInputConnection(tri_converter.GetOutputPort())
        stripper.Update()

        return stripper.GetOutput()
    
    #clean polydata
    def vtk_cleanPloySurf(self, polyData):
        #connectiveity filter
        connect_filter = vtk.vtkConnectivityFilter()
        connect_filter.SetInputData(polyData)
        connect_filter.Update()

        # clean isolcated points in surface
        clean_filter = vtk.vtkCleanPolyData()
        clean_filter.SetInputConnection(connect_filter.GetOutputPort())
        clean_filter.SetTolerance(0.0)
        clean_filter.PointMergingOn()
        clean_filter.Update()

        #smooth sharp edge
        #normals_filter = vtk.vtkPolyDataNormals()
        #normals_filter.SetInputConnection(clean_filter.GetOutputPort())
        #normals_filter.FlipNormalsOn()
        #normals_filter.Update()

        return clean_filter.GetOutput()
    
    #smooth polydata
    def vtk_smoothPolySurf(self, polyData, NumOfIterate=10, RelaxFactor=0.1):
        #smooth
        smoothingFilter = vtk.vtkSmoothPolyDataFilter()
        smoothingFilter.SetInput(polyData)
        smoothingFilter.SetNumberOfIterations(NumOfIterate)
        smoothingFilter.SetRelaxationFactor(RelaxFactor)
        smoothingFilter.FeatureEdgeSmoothingOn()
        smoothingFilter.Update()
        return smoothingFilter.GetOutput()

    #extrude polysurf
    def vtk_extrudePolySurf(self, polySurf, extrude_thickness = 5.0):
        #...extrude 
        extrude_filter = vtk.vtkLinearExtrusionFilter()
        extrude_filter.SetInputData(polySurf)
        extrude_filter.SetExtrusionTypeToNormalExtrusion()
        extrude_filter.SetScaleFactor(extrude_thickness)  #number of mm
        extrude_filter.CappingOn()
        extrude_filter.Update()

        #triangular the polydata
        tripolysurf = self.trianglePolySurf(extrude_filter.GetOutput())
        #clean ploydata
        extrudepoly = self.cleanSurfPoly(tripolysurf)
    
        return extrudepoly
    
    #get intersection curve between two surface
    def vtk_collideSurfs(self, surfpoly1, surfpoly2):
        #collisionDetector for intersection point
        from vtkSlicerRtCommonPython import vtkCollisonDectectionFilter
        collisionDetector = vtkCollisonDectectionFilter()
        #collisionDetector = vtkSlicerRtCommonPython.vtkCollisionDetectionFilter()
        transform0 = vtk.vtkTransform()
        matrix1 = vtk.vtkMatrix4x4()
        collisionDetector.SetInputData(0, surfpoly1)
        collisionDetector.SetTransform(0, transform0)
        collisionDetector.SetInputData(1, surfpoly2)
        collisionDetector.SetMatrix(1, matrix1)
        collisionDetector.SetCollisionModeToAllContacts()
        collisionDetector.SetBoxTolerance(0)
        collisionDetector.SetCellTolerance(0)
        collisionDetector.SetNumberOfCellsPerNode(2)
        collisionDetector.GenerateScalarsOn()
        collisionDetector.Update() 
        #numberOfCollisions = collisionDetector.GetNumberOfContacts()
        #collisionDetector.GetContactsOutput() ---vtkCommonDataModelPython.vtkPolyData
        #collisionDetector.GetContactsOutput().GetPoints() --- vtkCommonCorePython.vtkPoints
        #collisionDetector.GetContactCells(1) ==>'vtkCommonCorePython.vtkIdTypeArray'
        return collisionDetector.GetContactsOutput().GetPoints()  #vtkPoints

    
    #get cut line of cut open surface using a plane
    def vtk_cutlineSurfPlane(self, surfpoly, planeorigin, planenorm):
        cplane = vtk.vtkPlane()
        cplane.SetOrigin(planeorigin)
        cplane.SetNormal(planenorm)

        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(cplane)
        cutter.SetInput(surfpoly)
        cutter.GenerateTrianglesOn()
        cutter.Update()

        return cutter.GetOutput()
    
    #crop surface from a curvepoints
    def vtk_clipsurfbycurve(self, surfpoly, curvepoints):
        #cal scale in related to loop points
        loop = vtk.vtkSelectPolyData()
        loop.SetInputData(surfpoly)
        loop.SetLoop(curvepoints)
        loop.GenerateSelectionScalarsOn()
        loop.SetSelectionModeToSmallestRegion()
        loop.Update()

        # clips out positive region based on the scale
        clip = vtk.vtkClipPolyData()
        clip.SetInputConnection(loop.GetOutputPort())
        clip.InsideOutOn()
        clip.GenerateClippedOutputOff()
        clip.SetValue(1)
        clip.Update()

        #connectiveity filter then clean isolcated points in surface
        clipPolyData = self.trianglePolySurf(clip.GetOutput())
        clippoly = self.cleanSurfPoly(clipPolyData)
        return clippoly
    
    #crop closed surface polydata with cutting planes
    def vtk_clipclosedsurface(self, clipsurfpoly, planecollection):
        #model should be triangular/stripper and/or smoothed
        clipper = vtk.vtkClipClosedSurface()
        clipper = vtk.vtkClipPolyData()
        clipper.SetInputConnection(clipsurfpoly)
        clipper.SetClippingPlanes(planecollection)
        clipper.Update()

        #connectiveity filter + isolcated points in surface
        clipclosedsurf = self.trianglePolySurf(clipper.GetOutput())
        clippolysurf = self.cleanSurfPoly(clipclosedsurf)
        return clippolysurf
    
    #transfer vtkpoints to curve poly
    def vtk_ptlist2polyline(self, ptlist, closed=False):
        points = vtk.vtkPoints()
        cellArray = vtk.vtkCellArray()

        nOfControlPoints = ptlist.GetNumberOfPoints()
        pos = [0.0, 0.0, 0.0]
        posStartEnd = [0.0, 0.0, 0.0]

        offset = 0
        if not closed:
            points.SetNumberOfPoints(nOfControlPoints)
            cellArray.InsertNextCell(nOfControlPoints)
        else:
            posStart = [0.0, 0.0, 0.0]
            posEnd = [0.0, 0.0, 0.0]
            ptlist.GetPoint(0, posStart)
            ptlist.GetPoint(nOfControlPoints-1, posEnd)
            posStartEnd[0] = (posStart[0]+posEnd[0])/2.0
            posStartEnd[1] = (posStart[1]+posEnd[1])/2.0
            posStartEnd[2] = (posStart[2]+posEnd[2])/2.0
            points.SetNumberOfPoints(nOfControlPoints+2)
            cellArray.InsertNextCell(nOfControlPoints+2)

        points.SetPoint(0, posStartEnd)
        cellArray.InsertCellPoint(0)

        offset = 1
        for i in range(nOfControlPoints):
            ptlist.GetPoint(i,pos)
            points.SetPoint(offset+i,pos)
            cellArray.InsertCellPoint(offset+i)

        offset = offset + nOfControlPoints
        if closed:
            points.SetPoint(offset,posStartEnd)
            cellArray.InsertCellPoint(offset)

        outputPoly = vtk.vtkPolyData()
        outputPoly.Initialize()
        outputPoly.SetPoints(points)
        outputPoly.SetLines(cellArray)

        return outputPoly
    
    #vtransfer tkpoints to curve poly with interpolation
    def vtk_polyCardinalInterp(self, ptlist, interResolution=3, closed=False):
        nOfControlPoints = ptlist.GetNumberOfPoints()
        pos = [0.0, 0.0, 0.0]
        # One spline for each direction.
        aSplineX = vtk.vtkCardinalSpline()
        aSplineY = vtk.vtkCardinalSpline()
        aSplineZ = vtk.vtkCardinalSpline()
        if closed:
            aSplineX.ClosedOn()
            aSplineY.ClosedOn()
            aSplineZ.ClosedOn()
        else:
            aSplineX.ClosedOff()
            aSplineY.ClosedOff()
            aSplineZ.ClosedOff()

        for i in range(0, nOfControlPoints):
            ptlist.GetPoint(i, pos)
            aSplineX.AddPoint(i, pos[0])
            aSplineY.AddPoint(i, pos[1])
            aSplineZ.AddPoint(i, pos[2])
        
        # Interpolate x, y and z by using the three spline filters and create new points
        nInterpolatedPoints = (interResolution+2)*(nOfControlPoints-1) 
        # One section is devided into self.interpResolution segments
        points = vtk.vtkPoints()
        r = [0.0, 0.0]
        aSplineX.GetParametricRange(r)
        t = r[0]
        p = 0
        tStep = (nOfControlPoints-1.0)/(nInterpolatedPoints-1.0)
        nOutputPoints = 0

        if closed:
            while t < r[1]+1.0:
                points.InsertPoint(p, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t))
                t = t + tStep
                p = p + 1
            ## Make sure to close the loop
            points.InsertPoint(p, aSplineX.Evaluate(r[0]), aSplineY.Evaluate(r[0]), aSplineZ.Evaluate(r[0]))
            p = p + 1
            points.InsertPoint(p, aSplineX.Evaluate(r[0]+tStep), aSplineY.Evaluate(r[0]+tStep), aSplineZ.Evaluate(r[0]+tStep))
            nOutputPoints = p + 1
        else:
            while t < r[1]:
                points.InsertPoint(p, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t))
                t = t + tStep
                p = p + 1
            nOutputPoints = p
        
        lines = vtk.vtkCellArray()
        lines.InsertNextCell(nOutputPoints)
        for i in range(0, nOutputPoints):
            lines.InsertCellPoint(i)

        outputPoly = vtk.vtkPolyData()
        outputPoly.Initialize()
        outputPoly.SetPoints(points)
        outputPoly.SetLines(lines)

        return outputPoly
    
    #compute len of a polyline
    def vtk_polycurveLen(self, poly):
        lines = poly.GetLines()
        points = poly.GetPoints()
        pts = vtk.vtkIdList()

        lines.GetCell(0, pts)
        ip = np.array(points.GetPoint(pts.GetId(0)))
        n = pts.GetNumberOfIds()

        # Check if there is overlap between the first and last segments
        # (for making sure to close the loop for spline curves)
        if n > 2:
            slp = np.array(points.GetPoint(pts.GetId(n-2)))
        # Check distance between the first point and the second last point
        if np.linalg.norm(slp-ip) < 0.00001:
            n = n - 1
            
        length = 0.0
        pp = ip
        for i in range(1,n):
            p = np.array(points.GetPoint(pts.GetId(i)))
            length = length + np.linalg.norm(pp-p)
            pp = p

        return length    
    
    #calculate midpoint on a polyline
    def vtk_midpolycurve(self, poly):
        midlen = self.polylineLength(poly)/2.0

        lines = poly.GetLines()
        points = poly.GetPoints()

        pts = vtk.vtkIdList()
        lines.GetCell(0, pts)
        ip = np.array(points.GetPoint(pts.GetId(0)))
        n = pts.GetNumberOfIds()

        length = 0
        pp = ip
        for i in range(1,n):
            p = np.array(points.GetPoint(pts.GetId(i)))
            tlen = np.linalg.norm(pp-p)
            if (length + tlen) >= midlen:  #check midpoint
                tp = (pp + p) /2 
                tlen = np.linalg.norm(pp-tp)
                if(length+tlen)>=midlen:
                    midpt = tp
                else:
                    midpt = p
                break
            else:
                length += tlen
                pp = p

        return midpt

##RUN in Slicer Python 
import sys    #need include the path for slicer to recognize subfunction
sys.path.append('Z:/HW-Research/CardiacRT-EAM-Project/CardiacRT-Slicer-Scripts/') 
import LV17Seg
LVSet = LV17Seg.LV17Seg()

