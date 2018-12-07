#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018                                                    *
#*   Efficient Power Conversion Corporation, Inc.  http://epc-co.com       *
#*                                                                         *
#*   Developed by FastFieldSolvers S.R.L. under contract by EPC            *
#*   http://www.fastfieldsolvers.com                                       *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************


__title__="FreeCAD E.M. Workbench FastHenry Node Class"
__author__ = "FastFieldSolvers S.R.L."
__url__ = "http://www.fastfieldsolvers.com"

# defines
#
# default node color
EMFHNODE_DEF_NODECOLOR = (1.0,0.0,0.0)
EMFHNODE_DEF_NODESIZE = 10

import FreeCAD, FreeCADGui, Mesh, Part, MeshPart, Draft, DraftGeomUtils, os
from FreeCAD import Vector

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt,txt, utf8_decode=False):
        return txt
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    # \endcond

__dir__ = os.path.dirname(__file__)
iconPath = os.path.join( __dir__, 'Resources' )

def makeFHNode(baseobj=None,X=0.0,Y=0.0,Z=0.0,color=None,size=None,name='FHNode'):
    '''Creates a FastHenry node ('N' statement in FastHenry)
    
    'baseobj' is the point object whose position is used as base for the FNNode
        If no 'baseobj' is given, X,Y,Z are used as coordinates
    
    Example:
    TBD
'''
    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
    obj.Label = translate("EM", name)
    # this adds the relevant properties to the object 
    #'obj' (e.g. 'Base' property) making it a _FHNode 
    _FHNode(obj)
    # manage ViewProvider object
    if FreeCAD.GuiUp:
        _ViewProviderFHNode(obj.ViewObject)
        # set base ViewObject properties to user-selected values (if any)
        if color:
            obj.ViewObject.PointColor = color
        else:
            obj.ViewObject.PointColor = EMFHNODE_DEF_NODECOLOR
        if size:
            obj.ViewObject.PointSize = size
        else:
            obj.ViewObject.PointSize = EMFHNODE_DEF_NODESIZE
    # check if 'baseobj' is a point (only base object allowed)
    if baseobj:
        if Draft.getType(baseobj) == "Point":
            # get the absolute coordinates of the Point
            X = baseobj.Shape.Point.x
            Y = baseobj.Shape.Point.y
            Z = baseobj.Shape.Point.z
        else:
            FreeCAD.Console.PrintWarning(translate("EM","FHNodes can only take the position from Point objects"))
    # set the node coordinates
    obj.Proxy.setAbsCoord(Vector(X,Y,Z))
    # force recompute to show the Python object
    FreeCAD.ActiveDocument.recompute()
    # return the newly created Python object
    return obj

class _FHNode:
    '''The EM FastHenry Node object'''
    def __init__(self, obj):
        ''' Add properties '''
        obj.addProperty("App::PropertyDistance","X","EM",QT_TRANSLATE_NOOP("App::Property","X Location"))
        obj.addProperty("App::PropertyDistance","Y","EM",QT_TRANSLATE_NOOP("App::Property","Y Location"))
        obj.addProperty("App::PropertyDistance","Z","EM",QT_TRANSLATE_NOOP("App::Property","Z Location"))
        obj.Proxy = self
        self.Type = "FHNode"
        # save the object in the class, to store or retrieve specific data from it
        # from within the class
        self.Object = obj
        
    def execute(self, obj):
        ''' this method is mandatory. It is called on Document.recompute() 
'''
        #FreeCAD.Console.PrintWarning("\n_FHNode execute\n") #debug
        # set the shape as a Vertex at relative position obj.X, obj.Y, obj.Z
        # The vertex will then be adjusted according to the FHNode Placement
        obj.Shape = Part.Vertex(self.getRelCoord())
                
    def onChanged(self, obj, prop):
        ''' take action if an object property 'prop' changed
'''
        #FreeCAD.Console.PrintWarning("\n_FHNode onChanged(" + str(prop)+")\n") #debug
        if not hasattr(self,"Object"):
            # on restore, self.Object is not there anymore (JSON does not serialize complex objects
            # members of the class, so __getstate__() and __setstate__() skip them);
            # so we must "re-attach" (re-create) the 'self.Object'
            self.Object = obj           

    def serialize(self,fid,extension=""):
        ''' Serialize the object to the 'fid' file descriptor
        
        'fid': the file descriptor
        'extension': any extension to add to the node name, in case of a node
            belonging to a conductive plane. If not empty, it also changes
            the way the node is serialized, according to the plane node definition.
            Defaults to empty string.
'''
        pos = self.getAbsCoord()
        if extension == "":
            fid.write("N" + self.Object.Label)
            fid.write(" x=" + str(pos.x) + " y=" + str(pos.y) + " z=" + str(pos.z))
        else:
            fid.write("+         N" + self.Object.Label + extension)
            fid.write(" (" + str(pos.x) + "," + str(pos.y) + "," + str(pos.z) + ")")
        fid.write("\n")

    def getAbsCoord(self):
        ''' Get a FreeCAD.Vector containing the absolute node coordinates
'''
        # should be "self.Object.Placement.multVec(Vector(self.Object.X, self.Object.Y, self.Object.Z))"
        # but as the shape is always a Vertex, this is a shortcut
        return self.Object.Shape.Point

    def getRelCoord(self):
        ''' Get a FreeCAD.Vector containing the relative node coordinates w.r.t. the Placement
        
        These coordinates correspond to (self.Object.X, self.Object.Y, self.Object.Z),
        that are the same as self.Object.Placement.inverse().multVec(self.Object.Shape.Point))
'''
        return Vector(self.Object.X,self.Object.Y,self.Object.Z)

    def setRelCoord(self,rel_coord,placement=None):
        ''' Sets the relative node position w.r.t. the placement
        
        'rel_coord': FreeCAD.Vector containing the relative node coordinates w.r.t. the Placement
        'placement': the new placement. If 'None', the placement is not changed
        
        Remark: the function will not recalculate() the object (i.e. change of position is not visible
        just by calling this function)
'''
        if placement:
            # validation of the parameter
            if isinstance(placement, FreeCAD.Placement):
                self.Object.Placement = placement
        self.Object.X = rel_coord.x
        self.Object.Y = rel_coord.y
        self.Object.Z = rel_coord.z

    def setAbsCoord(self,abs_coord,placement=None):
        ''' Sets the absolute node position, considering the object placement, and in case forcing a new placement
        
        'abs_coord': FreeCAD.Vector containing the absolute node coordinates
        'placement': the new placement. If 'None', the placement is not changed

        Remark: the function will not recalculate() the object (i.e. change of position is not visible
        just by calling this function)
'''
        if placement:
            # validation of the parameter
            if isinstance(placement, FreeCAD.Placement):
                self.Object.Placement = placement
        rel_coord = self.Object.Placement.inverse().multVec(abs_coord)
        self.Object.X = rel_coord.x
        self.Object.Y = rel_coord.y
        self.Object.Z = rel_coord.z
       
    def __getstate__(self):
        return self.Type

    def __setstate__(self,state):
        if state:
            self.Type = state
    
class _ViewProviderFHNode:
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        obj.Proxy = self
        self.Object = obj.Object

    def attach(self, obj):
        ''' Setup the scene sub-graph of the view provider, this method is mandatory '''
        # on restore, self.Object is not there anymore (JSON does not serialize complex objects
        # members of the class, so __getstate__() and __setstate__() skip them);
        # so we must "re-attach" (re-create) the 'self.Object'
        self.Object = obj.Object
        return

    def updateData(self, fp, prop):
        ''' Print the name of the property that has changed '''
        #FreeCAD.Console.PrintMessage("ViewProvider updateData(),  property: " + str(prop) + "\n")
        ''' If a property of the handled feature has changed we have the chance to handle this here '''
        return

    def getDefaultDisplayMode(self):
        ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
        return "Flat Lines"

    def onChanged(self, vp, prop):
        ''' Print the name of the property that has changed '''
        #FreeCAD.Console.PrintMessage("ViewProvider onChanged(), property: " + str(prop) + "\n")

    def getIcon(self):
        ''' Return the icon in XMP format which will appear in the tree view. This method is optional
        and if not defined a default icon is shown.
        '''
        return os.path.join(iconPath, 'node_icon.svg')

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None
            
class _CommandFHNode:
    ''' The EM FastHenry Node (FHNode) command definition
'''
    def GetResources(self):
        return {'Pixmap'  : os.path.join(iconPath, 'node_icon.svg') ,
                'MenuText': QT_TRANSLATE_NOOP("EM_FHNode","FHNode"),
                'Accel': "E, N",
                'ToolTip': QT_TRANSLATE_NOOP("EM_FHNode","Creates a FastHenry Node object from scratch or from a selected object (point)")}
                
    def IsActive(self):
        return not FreeCAD.ActiveDocument is None

    def Activated(self):
        # get the selected object(s)
        sel = FreeCADGui.Selection.getSelectionEx()
        done = False
        # if selection is not empty
        if sel:
            # automatic mode
            import Draft
            if Draft.getType(sel[0].Object) == "Point":
                FreeCAD.ActiveDocument.openTransaction(translate("EM","Create FHNode"))
                FreeCADGui.addModule("EM")
                for selobj in sel:
                    FreeCADGui.doCommand('obj=EM.makeFHNode(FreeCAD.ActiveDocument.'+selobj.Object.Name+')')
                # autogrouping, for later on
                #FreeCADGui.addModule("Draft")
                #FreeCADGui.doCommand("Draft.autogroup(obj)")
                FreeCAD.ActiveDocument.commitTransaction()
                FreeCAD.ActiveDocument.recompute()
                done = True
        # if no selection, or nothing good in the selected objects
        if not done:
            #FreeCAD.DraftWorkingPlane.setup()
            # get a 3D point via Snapper, setting the callback functions
            FreeCADGui.Snapper.getPoint(callback=self.getPoint)

    def getPoint(self,point=None,obj=None):
        "this function is called by the snapper when it has a 3D point"
        if point == None:
            return
        #coord = FreeCAD.DraftWorkingPlane.getLocalCoords(point)
        coord = point
        FreeCAD.ActiveDocument.openTransaction(translate("EM","Create FHNode"))
        FreeCADGui.addModule("EM")
        FreeCADGui.doCommand('obj=EM.makeFHNode(X='+str(coord.x)+',Y='+str(coord.y)+',Z='+str(coord.z)+')')
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        # might improve in the future with continue command
        #if self.continueCmd:
        #    self.Activated()

if FreeCAD.GuiUp:
    FreeCADGui.addCommand('EM_FHNode',_CommandFHNode())

