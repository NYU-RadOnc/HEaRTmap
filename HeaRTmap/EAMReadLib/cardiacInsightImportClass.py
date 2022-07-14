import vtk, slicer
import os
import xml.etree.ElementTree as ET 
import numpy as np

#Read cardiacInsight export directory
class cardiacInsightImport():
    def mkVtkIdList(self, it):
        vil = vtk.vtkIdList()
        for i in it:
            vil.InsertNextId(int(i))
        return vil
    
    def CreateMesh(self, modelNode, arrayVertices, arrayVertexNormals, arrayTriangles, labelsScalars, arrayScalars):
        # based on https://vtk.org/Wiki/VTK/Examples/Python/DataManipulation/Cube.py
        # modelNode : a vtkMRMLModelNode in the Slicer scene which will hold the mesh
        # arrayVertices : list of triples [[x1,y1,z2], [x2,y2,z2], ... ,[xn,yn,zn]] of vertex coordinates
        # arrayVertexNormals : list of triples [[nx1,ny1,nz2], [nx2,ny2,nz2], ... ] of vertex normals
        # arrayTriangles : list of triples of 0-based indices defining triangles
        # labelsScalars : list of strings such as ["bipolar", "unipolar"] to label the individual scalars data sets
        # arrayScalars : list of n m-tuples for n vertices and m individual scalar sets

        # HW: all array in [number_vertex x number_features]
        
        # create the building blocks of polydata including data attributes.
        mesh    = vtk.vtkPolyData()
        points  = vtk.vtkPoints()
        normals = vtk.vtkFloatArray()
        polys   = vtk.vtkCellArray()
        
        # load the array data into the respective VTK data structures
        #self.addLog("  Initializing vertices.")
        for i in range(len(arrayVertices)):
            points.InsertPoint(i, arrayVertices[i])
        
        #if self.abortRequested: 
        #    return False
        
        #self.addLog("  Initializing triangles.")
        for i in range(len(arrayTriangles)):
            polys.InsertNextCell(self.mkVtkIdList(arrayTriangles[i]))
        
        #if self.abortRequested: 
        #    return False
        
        # Normals: http://vtk.1045678.n5.nabble.com/Set-vertex-normals-td5734525.html
        # First pre-allocating memory for the vtkDataArray using vtkDataArray::SetNumberOfComponents() and vtkDataArray::SetNumberOfTuples()
        # and then setting the actual values through SetTuple() is orders of magnitude faster than inserting them one-by-one (and allocating memory dynamically)
        # with InsertTuple() 
        normals.SetNumberOfComponents(3)
        normals.SetNumberOfTuples(len(arrayVertexNormals))
        #self.addLog("  Initializing normals.")
        for i in range(len(arrayVertexNormals)):
            normals.SetTuple3(i, arrayVertexNormals[i][0], arrayVertexNormals[i][1], arrayVertexNormals[i][2])
            #if self.abortRequested: 
            #    return False
        
        # put together the mesh object
        # self.addLog("  Building mesh.")
        mesh.SetPoints(points)
        mesh.SetPolys(polys)
        if(len(arrayVertexNormals) == len(arrayVertices)):
            mesh.GetPointData().SetNormals(normals)
        
        #if self.abortRequested: 
        #    return False
        
        # self.addLog("  Adding scalar data.")
        
        # Add scalars
        scalars = []
        for j in range(len(labelsScalars)):  #j scale index
            scalars.append(vtk.vtkFloatArray())
            scalars[j].SetNumberOfComponents(1)
            scalars[j].SetNumberOfTuples(len(arrayScalars))
            for i in range(len(arrayScalars)): #i vertex index
                scalars[j].SetTuple1(i,arrayScalars[i][j])
                #if self.abortRequested: 
                #    return False
            scalars[j].SetName(labelsScalars[j])
            mesh.GetPointData().AddArray(scalars[j])
        
        #if self.abortRequested: 
        #    return False

        #---HW: higher resolution if NumberOfPoints() is less than 5120
        #CardiacInsight Heart typically low resolution, leading to color interpolation artifacts
        #High Mesh Resolution by subdivision
        if len(arrayVertices) < 5120:
            subfilter = vtk.vtkLinearSubdivisionFilter() 
            subfilter.SetNumberOfSubdivisions(2)
            subfilter.SetInputData(mesh)
            #subfilter.SetInputConnection(modelNode.GetPolyDataConnection())
            subfilter.Update()
            #newnode = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
            #newnode.SetAndObservePolyData(subfiler.GetOutput())
            modelNode.SetAndObservePolyData(subfilter.GetOutput())
        else:
            modelNode.SetAndObservePolyData(mesh)

        #self.addLog("Model created.")

        return True
    
    def transformNode(self, node, matrix):
        transform = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        transformMatrix = vtk.vtkMatrix4x4()
        transformMatrix.Zero()
        
        for row in range(4):
            for col in range(4): 
                transformMatrix.SetElement(row, col, matrix[row][col])
        
        transform.SetMatrixTransformToParent(transformMatrix) 
        
        # Apply transform to node... 
        node.SetAndObserveTransformNodeID(transform.GetID())    
        # ... and harden it
        transformLogic = slicer.vtkSlicerTransformLogic()
        transformLogic.hardenTransform(node)
        # delete transform node
        slicer.mrmlScene.RemoveNode(transform)
       
    ################################################################################
    # CardiacInsight import
    def readInsight(self, dirname):
        meshlist, pointlist, beatmaplist = self.readInsightDir(dirname)
        if len(meshlist) == 0 or len(beatmaplist) ==0:
            return False
            
        #LPS to slicer RAS coordinate system
        matrixLPStoRAS = [[-1, 0, 0, 0], [ 0,-1, 0, 0], [ 0, 0, 1, 0], [ 0, 0, 0, 1]] 
        
        #export all mesh as model export heart. heart will have scales for each study
        for mesh in meshlist:
            if mesh['MeshType'] == 'Heart':
                continue  #Heart will import with maps of each study
            vertices = mesh['vertexArr']
            vertexnormals = mesh['vertexNormArr']
            triangles = mesh['faceArr'] 

            modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
            if not self.CreateMesh(modelNode, vertices, vertexnormals, triangles, [], []):
                slicer.mrmlScene.RemoveNode(modelNode) 
                return False

            self.transformNode(modelNode, matrixLPStoRAS)
            modelNode.SetName(mesh['MeshType'])
            modelNode.CreateDefaultDisplayNodes() 
        
        #for heart includes maps
        heartmesh = next((f for f in meshlist if f['MeshType']=='Heart'), False)
        if not heartmesh:  #messageBox('No Heart')
            return False

        vertices = heartmesh['vertexArr']
        vertexnormals = heartmesh['vertexNormArr']
        triangles = heartmesh['faceArr'] 
        for beat in beatmaplist:
            map1dnames  = beat['Map1dTypes']
            map1darrays = beat['Map1dArrays']
            #create heart map
            modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
            if not self.CreateMesh(modelNode, vertices, vertexnormals, triangles, map1dnames, map1darrays):
                slicer.mrmlScene.RemoveNode(modelNode) 
                return False
            self.transformNode(modelNode, matrixLPStoRAS)
            modelNode.SetName(beat['BeatName'].replace(" ", "") + "_" + heartmesh['MeshType'])
            modelNode.CreateDefaultDisplayNodes() 
        return True

    #-----------------------------------------------------------------
    def readInsightDir(self, dirname):
        #read and undertand Insight export directory
        #read the datadir, spearate them 
        files = [f for f in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, f))]
        ufiles = [f for f in files if f.endswith('.xml')]  
        #only .xml be considered, ecgdata no xml file, so .dat also be ignored

        #separate files based on xml for 'TriangularMesh', 'PointGroup' and 'Map'
        meshlist, pointlist, maplist = [], [], []
        for f in ufiles:
            xmlfile = os.path.join(dirname, f)
            tree = ET.parse(xmlfile)
            root = tree.getroot()  #root.tag ('TriangularMesh')  
            if root.tag == 'TriangularMesh':
                meshnote = root.attrib['description']
                if f.endswith('_Heart.xml'):
                    meshtype = 'Heart'
                elif f.endswith('_ValveHole.xml'):
                    meshtype = 'ValveHole'
                elif f.endswith('_Torso.xml'):
                    meshtype = 'Torso'
                elif f.endswith('_ValveLandmark.xml'):
                    meshtype = 'ValveLandmark'
                elif '_Landmark_' in f:
                    meshtype = 'Landmark_' + meshnote.replace(" ", "")
                else:
                    meshtype = 'Unknown'
                    print(f + ' is not recognized Mesh!')

                meshlist.append({'MeshType': meshtype, 
                                'description': meshnote,
                                'xmlfilename': xmlfile})

            elif root.tag == 'PointGroup':
                meshtype = 'PointGroup'
                marktype = root.find('Label').text
                marknote = root.find('Notes').text

                pointlist.append({'PointName': marktype, 
                                'PointNote': marknote,
                                'xmlfilename': xmlfile})

            elif root.tag == 'Map':
                MapName = root.find('MapName').text  #has map study
                MapType = root.find('MapType').text  #has every MapType
                NumNodes = int(root.find('NumberOfNodes').text)
                #if (MapName not in f) or (MapType not in f):
                #    print(f + ' Name not include Name:' + MapName + ' or Type:' + MapType)
                #get matlab map file as .dat 
                datfile = os.path.join(dirname, f.replace('.xml','.dat'))
                if not os.path.isfile(datfile):
                    print(f + ' Has no corresponding .dat file:' + datfile)

                maplist.append({'MapName': MapName, 
                                'MapType': MapType, 
                                'NumNodes': NumNodes,
                                'xmlfilename': xmlfile,
                                'datfilename': datfile})
            else:
                print(f + ' is not recognized xml root. Ignored!')

        #re-orangize Maplist based on (study) MapName 
        mapnames = [f['MapName'] for f in maplist]
        unimapnames = list(set(mapnames)) #get unique map names
        beatmaplist = []   #map list per mapname
        for name in unimapnames:
            cbeammap = {'BeatName': name, 'Maps':[]}
            cbeammap['Maps'] = [f for f in maplist if f['MapName']==name]
            beatmaplist.append(cbeammap)
            #MapType: potential, activation, voltage, propagation, directionalactivation
        #Final:::: meshlist, pointlist, beatmaplist 

        #-----------Data Reading-------------------------------
        #Read Mesh vertex data to each mesh
        for mesh in meshlist:
            vertexArr, vertexNormArr, faceArr = self.readInsightMesh(mesh['xmlfilename'])
            mesh['vertexArr']  = vertexArr
            mesh['vertexNormArr'] = vertexNormArr
            mesh['faceArr']  = faceArr
        #Read PointGroup data to each point
        for ptgroup in pointlist:
            pointArr = self.readInsightPointGroup(ptgroup['xmlfilename'])
            ptgroup['pointArr'] = pointArr
        #Read Map data to each beatmap
        #..as begining, only map for scale of heart vertex (activation and voltage) organized
        # map1d = ['activation' , 'voltage']    #1D directionalActivation not process now
        # map2d = ['potential', 'propagation']  #2D scale consider late
        for beat in beatmaplist:  
            #first: read All Map Array in Maps
            for map in beat['Maps']:  
                map['MapArr'] = self.readInsightMap(map['xmlfilename'], map['datfilename'])
            #second: extra and oragnize heart 1D map for scale for each beat study
            map1dtype, map1darr = [], []
            #.......voltage
            voltagemap = next((map for map in beat['Maps'] if map['MapType'].lower()=='voltage'), False)
            if not voltagemap: #no  voltage, calculte from potentials by max-min of 2D array along time
                potentialmap = next((map for map in beat['Maps'] if 'potential' in map['MapType'].lower()), False)
                if potentialmap:
                    potentialArr = potentialmap['MapArr']  #MapArr is [n_nodes x n_time point]
                    voltageArr = np.amax(potentialArr, axis=1) - np.amin(potentialArr, axis=1)
                    map1dtype.append('voltage')
                    map1darr.append(np.reshape(voltageArr, (len(voltageArr),1)))  
            else:
                map1dtype.append('voltage')
                map1darr.append(voltagemap['MapArr'])

            #......activation        
            activationmap = next((map for map in beat['Maps'] if map['MapType'].lower()=='activation'), False)
            if activationmap:
                    map1dtype.append('activation')
                    map1darr.append(activationmap['MapArr'])

            #add to beat list, separate 1d and 2d maps, now 1d only       
            beat['Map1dTypes']  = map1dtype  
            beat['Map1dArrays'] = np.hstack(map1darr)   #concentrate list of array as 2d array
        return meshlist, pointlist, beatmaplist     

    def readInsightMesh(self, filename):
        #output vertexArr, vertexNormArr, faceArr in unit of mm
        tree = ET.parse(filename)
        root = tree.getroot()  #root.tag ('TriangularMesh')
        #root.atribe: origin_unit=“mm”; origin=“1,2,3”; units=“cm”; description=“epicardium"
        description = root.attrib['description']   
        units = root.attrib['units']  #cm
        origin = root.attrib['origin'].split(',')  #DICOM origin separated
        origin_units = root.attrib['origin_units']  #mm
        if origin_units == 'mm':
            if units == 'cm':
                utr = 10.0  #from file unit to DICOM unit for display
            elif units == 'mm':
                utr = 1.0
            else:
                print('File Saptial Unit must be cm or mm')
                return False
        else:
            print('DCIOM Orgin Unit only can be mm')
            return False

        #read vertices
        vertices = root.find('Vertices')
        vertexlist = vertices.findall('Vertex')
        nvert = len(vertexlist)
        vertexArr = np.zeros((nvert,3), dtype = float)
        #if '_Heart' in filename:
        #    print('Debug')
        for vertex in vertexlist:
            attrib = vertex.attrib #v.attrib {id, x, y, z}; v.tag 'Vertex', v.tail '\n'
            id =  int(attrib['id'])
            x  = float(attrib['x'])*utr + float(origin[0]) #File cm to  DICOM mm
            y  = float(attrib['y'])*utr + float(origin[1])
            z  = float(attrib['z'])*utr + float(origin[2])
            vertexArr[id,:] = [x, y, z] 
            #check to ensure 'x/y/z' or "X/Y/Z"

        #record face ids to each vertex 
        #for average triangle normals to get vertex normals
        vertFaceInds = []  #one-to-one indexed corresponds to vertexlist
        for i in range(nvert):
            vertFaceInds.append({'vId': i, 'fIds':[]})

        #read face : v1/v2/v3 index to vertexArr index   
        faces = root.find('Faces')
        facelist = faces.findall('Face')
        nface = len(facelist)
        faceArr = np.zeros((nface, 3), dtype = int)
        for i, face in enumerate(facelist):
            attrib = face.attrib
            v1 = int(attrib['v1'])
            v2 = int(attrib['v2'])
            v3 = int(attrib['v3'])
            faceArr[i,:] = [v1, v2, v3]
            #set to corresponding vertex
            vertFaceInds[v1]['fIds'].append(i)
            vertFaceInds[v2]['fIds'].append(i)
            vertFaceInds[v3]['fIds'].append(i)

        #calcuate Norm for each face
        faceNormArr = np.zeros((nface, 3), dtype = float)
        for i in range(nface):
            tri = faceArr[i]
            p1 = vertexArr[tri[0]]
            p2 = vertexArr[tri[1]]
            p3 = vertexArr[tri[2]]
            line1 = p1-p2
            line2 = p3-p2
            faceNormArr[i,:] = -1 * np.cross(line1, line2) 
            #X(-1) make normals point to outside, based on triangule points rotation
            #this is important, need checked on display

        #Assign face index to corresponding vertex to calcualte average of plane norm calculation
        vertexNormArr = np.zeros((nvert, 3), dtype = float)
        for id in range(nvert):
            faceids = vertFaceInds[id]['fIds']
            fsum = np.zeros((1, 3))
            for fid in faceids:
                fsum += faceNormArr[fid,:]
            fnorm = np.linalg.norm(fsum)
            if (fnorm<1e-4) or np.isnan(fnorm) or np.isinf(fnorm):
                fnorm = 1e-4  #!!Attention: Landmark_LAD.xml has same vertex position for a face
            vertexNormArr[id, :] = fsum / fnorm #Normlize as Normals
       
        return vertexArr, vertexNormArr, faceArr  #vertexArr, vertexNormArr, faceArr  #in unit of mm

    def readInsightMap(self, mapxmlfile, mapdatfile):
        #read map corresponding to mesh
        #mapfile.dat and mapfile.xml for data and information
        #.xml for map information
        tree = ET.parse(mapxmlfile)
        root = tree.getroot()  #root.tag ('Map') 
        #MapName = root.find('MapName').text
        #MapType = root.find('MapType').text
        NumNodes = int(root.find('NumberOfNodes').text)
        #IntLen = int(root.find('IntervalLength').text)

        #.dat matlab data files; NumNodes = int(2002)
        matarr = np.fromfile(mapdatfile, dtype=np.float32) #(2002,)
        assert(matarr.shape[0] % NumNodes == 0),  'must be divisible'
        NumTimes = int(matarr.shape[0]//NumNodes) #[nrow(time point) x ncol(node point)]
        mapArr = np.transpose(matarr.reshape((NumTimes, NumNodes))) #transpose as [n_node x n_time point]
        #this transpose makes mapArr has same array format as vertex along column
        #ensure n_nodes X 1 if only 1 colum
        return mapArr     #return mapArr for vertex in column

    def readInsightPointGroup(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()  #root.tag ('PointGroup') 
        #get unit from file to DICOM unit
        #root.atribe: origin_unit=“mm”; origin=“1,2,3”; units=“cm”; 
        units = root.attrib['units']  #cm
        origin = root.attrib['origin'].split(',')  #DICOM origin separated
        origin_units = root.attrib['origin_units']  #mm
        if origin_units == 'mm':
            if units == 'cm':
                utr = 10.0  #from file unit to DICOM unit for display
            elif units == 'mm':
                utr = 1.0
            else:
                print('File Saptial Unit must be cm or mm')
                return False
        else:
            print('DCIOM Orgin Unit only can be mm')
            return False
        #read points
        points = root.find('Points')
        pointlist = points.findall('Point')
        npoint = len(pointlist)
        pointArr = np.zeros((npoint,3), dtype = float)
        for i, point in enumerate(pointlist):
            attrib = point.attrib #point.attrib {x, y, z}; tag 'Point', v.tail '\n'
            x  = float(attrib['X'])*utr + float(origin[0])  #File cm to  DICOM mm
            y  = float(attrib['Y'])*utr + float(origin[1])
            z  = float(attrib['Z'])*utr + float(origin[2])
            pointArr[i,:] = [x, y, z] 

        return pointArr    #Point locations in unit of mm


#datadir = 'C:/Users/wangh15/Desktop/Cardiac_NYUSBRT01/'
#cardiacimport = cardiacInsightImport()
#cardiacimport.readInsight(datadir)
