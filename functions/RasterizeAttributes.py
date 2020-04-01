import numpy as np
import json
from utils import ZonalAttributesTable, loadJSON

class RasterizeAttributes():

    def __init__(self):
        self.name = "Rasterize Attributes"
        self.description = ("Enriches a raster through additional bands derived from values of specified attributes "
                            "of an external table or a feature service. You can optionally specify a zone raster "
                            "and the associated zone ID attribute to enable region-based look-up. ")
        self.ztMap = {}                 # zonal thresholds { zoneId:[f1,f2,...,fn], ... }
        self.ztTable = None             # valid only if parameter 'ztable' is not a JSON string (but path or URL)
        self.background = 0
        self.whereClause = None
        self.M = 0                      # number of attribute names == additional bands in the output
        self.zid = None

    def getParameterInfo(self):
        return [
            {
                'name': 'vraster',
                'dataType': 'raster',
                'value': None,
                'required': True,
                'displayName': "Input Raster",
                'description': "The primary input raster."
            },
            {
                'name': 'zraster',
                'dataType': 'raster',
                'value': None,
                'required': False,
                'displayName': "Zone Raster",
                'description': ("An optional single-band zone raster where each pixel contains "
                                "the zone ID associated with the location. The zone ID is used for "
                                "looking up rows in the zonal attributes table for zone-specific ingestion. "
                                "Leave this parameter unspecified to simply import attribute")
            },
            {
                'name': 'ztable',
                'dataType': 'string',
                'value': None,
                'required': False,
                'displayName': "Zonal Attributes Table",
                'description': ("The zonal attributes specified as a JSON string, "
                                "a path to a local feature class or table, or the URL to a feature service layer. "
                                "In JSON, it's described as a collection of mapping from zone IDs to an "
                                "an array of integers, "
                                "like this: { zoneId:[f1,f2,...,fn], ... } ")
            },
            {
                'name': 'zid',
                'dataType': 'string',
                'value': None,
                'required': False,
                'displayName': "Zone ID Field Name",
                'description': ("Name of the field containing the Zone ID values. "
                                "This is only applicable if the 'Zonal Attributes Table' parameter contains path to a table "
                                "or a URL to a feature service.")
            },
            {
                'name': 'attribs',
                'dataType': 'string',
                'value': None,
                'required': False,
                'displayName': "Attribute Field Names",
                'description': ("List of fields in the zonal attributes table separated by a comma. Values in each field will be represented by a band in the output raster.")
            },
            {
                'name': 'background',
                'dataType': 'numeric',
                'value': 0,
                'required': False,
                'displayName': "Background Value",
                'description': ("The initial pixel value of the output raster--before input pixels are remapped.")
            },
            {
                'name': 'where',
                'dataType': 'string',
                'value': None,
                'required': False,
                'displayName': "Where Clause",
                'description': ("Additional query applied on Zonal Attributes table.")
            },
        ]


    def getConfiguration(self, **scalars):
        self.zid = (scalars.get('zid', "") or "").strip()
        self.zid = self.zid if len(self.zid) else None

        return {
          'inheritProperties': 2 | 4 | 8,
          'invalidateProperties': 2 | 4 | 8,        # invalidate statistics & histogram on the parent dataset.
          'inputMask': False                        # Don't need input raster mask in .updatePixels().
        }

    def selectRasters(self, tlc, shape, props):
        return ('vraster', 'zraster') if self.zid else ('vraster',)

    def updateRasterInfo(self, **kwargs):
        self.ztMap = None
        self.whereClause = None

        ztStr = kwargs.get('ztable', None)
        ztStr = ztStr.strip() if ztStr else "{}"

        try:
            self.ztMap = loadJSON(ztStr) if ztStr else {}
        except ValueError as e:
            self.ztMap = None

        attribs = kwargs.get('attribs', "")
        attribs = (attribs if attribs else "").split(",")
        self.M = len(attribs)

        if self.ztMap is None:
            self.ztMap = {}
            self.ztTable = ZonalAttributesTable(tableUri=ztStr,
                                                idField=self.zid,
                                                attribList=attribs)

        self.background = kwargs.get('background', None)
        self.background = int(self.background) if self.background else 0
        self.whereClause = kwargs.get('where', None)

        kwargs['output_info']['bandCount'] = 1 + self.M
        kwargs['output_info']['statistics'] = () 
        kwargs['output_info']['histogram'] = ()
        kwargs['output_info']['colormap'] = ()
        return kwargs


    def updatePixels(self, tlc, shape, props, **pixelBlocks):
        zoneIds = None
        v = pixelBlocks['vraster_pixels'][0]
        z = pixelBlocks.get('zraster_pixels', None) if self.zid else None

        if z is not None:               # zone raster is optional 
            z = z[0]
            zoneIds = np.unique(z)      #TODO: handle no-data and mask in zone raster

        ZT = self.ztTable.query(idList=zoneIds, 
                                where=self.whereClause, 
                                extent=props['extent'], 
                                sr=props['spatialReference']) if self.ztTable else self.ztMap

        # output pixels initialized to background color
        p = np.full(shape=(1 + self.M,) + v.shape,      # band dimension is 1 more than #attributes 
                    fill_value=self.background, 
                    dtype=props['pixelType'])

        np.copyto(p[0], v, casting='unsafe')
        ones = np.ones(v.shape, dtype=bool)
        # use zonal attributes to update output pixels...
        if ZT is not None and len(ZT.keys()):
            for k in (zoneIds if zoneIds is not None else [None]):
                T = ZT.get(k, None)                     # k from z might not be in ztMap
                if not T or not len(T):
                    continue

                I = (z == k) if z is not None else ones
                for b,t in enumerate(T[0], 1):          # first band of p is v, skip it.
                    if t is not None:
                        p[b][I] = t

        pixelBlocks['output_pixels'] = p
        return pixelBlocks
