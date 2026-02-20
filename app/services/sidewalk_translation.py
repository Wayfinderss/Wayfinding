# -*- coding: utf-8 -*-

import ogr2osm

class SidewalkTranslation(ogr2osm.TranslationBase):
    
    def filter_tags(self, attrs):
        """
        Filter and transform shapefile attributes to OSM tags.
        Return None to skip the feature, or return a dict of tags.
        """
        if not attrs:
            return None
        
        def sanitize(value):
            """Remove NULL bytes and control characters from strings"""
            if value is None:
                return None
            s = str(value)
            # Remove NULL bytes and control characters
            return ''.join(char for char in s if char >= ' ' or char in '\t\n\r').strip()
        
        tags = {}
        
        # Basic sidewalk tagging
        tags['highway'] = 'footway'
        tags['footway'] = 'sidewalk'
        
        # Surface material mapping
        if 'Material' in attrs and attrs['Material']:
            material = sanitize(attrs['Material']).lower()
            material_mapping = {
                'concrete': 'concrete',
                'asphalt': 'asphalt',
                'brick': 'paving_stones',
                'gravel': 'gravel',
                'dirt': 'unpaved',
                'paved': 'paved'
            }
            for key, value in material_mapping.items():
                if key in material:
                    tags['surface'] = value
                    break
        
        # Width in feet to meters
        if 'Width' in attrs and attrs['Width']:
            try:
                width_feet = float(attrs['Width'])
                width_meters = width_feet * 0.3048
                tags['width'] = f"{width_meters:.1f}"
            except (ValueError, TypeError):
                pass
        
        # Grade/incline
        if 'Grade' in attrs and attrs['Grade']:
            try:
                grade = float(attrs['Grade'])
                tags['incline'] = f"{grade:.1f}%"
            except (ValueError, TypeError):
                pass
        
        # Elevation
        if 'Z_Min' in attrs and attrs['Z_Min'] is not None:
            try:
                tags['ele:min'] = f"{float(attrs['Z_Min']):.1f}"
            except (ValueError, TypeError):
                pass
        
        if 'Z_Max' in attrs and attrs['Z_Max'] is not None:
            try:
                tags['ele:max'] = f"{float(attrs['Z_Max']):.1f}"
            except (ValueError, TypeError):
                pass
        
        # Location (sanitize text fields)
        if 'Municipali' in attrs and attrs['Municipali']:
            clean = sanitize(attrs['Municipali'])
            if clean:
                tags['addr:city'] = clean
        
        if 'County' in attrs and attrs['County']:
            clean = sanitize(attrs['County'])
            if clean:
                tags['addr:county'] = clean
        
        if 'Neighborho' in attrs and attrs['Neighborho']:
            clean = sanitize(attrs['Neighborho'])
            if clean:
                tags['neighbourhood'] = clean
        
        if 'RoadName' in attrs and attrs['RoadName']:
            clean = sanitize(attrs['RoadName'])
            if clean:
                tags['sidewalk:street'] = clean
        
        # Source
        if 'Source' in attrs and attrs['Source']:
            clean = sanitize(attrs['Source'])
            if clean:
                tags['source'] = clean
        else:
            tags['source'] = 'Pittsburgh Sidewalk Data'
        
        # Notes
        if 'Notes' in attrs and attrs['Notes']:
            clean = sanitize(attrs['Notes'])
            if clean:
                tags['note'] = clean
        
        # Date
        if 'Date' in attrs and attrs['Date']:
            tags['survey:date'] = str(attrs['Date'])
        
        return tags
    
    def filter_feature_pre(self, ogrfeature, ogrgeometry, osmtags):
        """
        Pre-processing filter. Return True to keep feature, False to skip.
        """
        # Skip features with no geometry
        if ogrgeometry is None:
            return False
        
        # Skip features that are too short (likely data errors)
        try:
            length = ogrfeature.GetField('Feet')
            if length is not None and length < 1:  # Less than 1 foot
                return False
        except:
            pass
        
        return True