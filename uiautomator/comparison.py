#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
image comparision module
depend:
<sudo apt-get install python-opencv>
options:
[sudo apt-get install python-numpy]
'''

__version__ = "2.0.1"
__author__ = "bhb"
__all__ = ['isMatch', 'getMatchedCenterOffset']

import os
try:
    import cv2
except ImportError, e:
    print e

def isMatch(subPath, srcPath, threshold=0.01,colormode=1):
    '''
    check wether the subPath image exists in the srcPath image.
    @type subPath: string
    @params subPath: the path of searched template. It must be not greater than the source image and have the same data type.
    @type srcPath: string
    @params srcPath: the path of the source image where the search is running.
    @type threshold: float
    @params threshold: the minixum value which used to increase or decrease the matching threshold. 0.01 means at most 1% difference. default is 0.01. 
    @rtype: boolean
    @return: true if the sub image founded in the src image. return false if sub image not found or any exception.
    '''
    for img in [subPath, srcPath]: assert os.path.exists(img) , 'No such image:  %s' % (img)
    method = cv2.cv.CV_TM_SQDIFF_NORMED #Parameter specifying the comparison method 
    try:
        subImg = cv2.imread(subPath,colormode) #Load the sub image
        srcImg = cv2.imread(srcPath,colormode) #Load the src image
        result = cv2.matchTemplate(subImg, srcImg, method) #comparision
        minVal = cv2.minMaxLoc(result)[0] #Get the minimum squared difference
        if minVal <= threshold: #Compared with the expected similarity
            return True
        else:
            return False
    except:
        return False
    
def getMatchedCenterOffset(subPath, srcPath, threshold=0.01, rotation=0, colormode=1):
    '''
    get the coordinate of the mathced sub image center point.
    @type subPath: string
    @params subPath: the path of searched template. It must be not greater than the source image and have the same data type.
    @type srcPath: string
    @params srcPath: the path of the source image where the search is running.
    @type threshold: float
    @params threshold: the minixum value which used to increase or decrease the matching threshold. 0.01 means at most 1% difference.
                       default is 0.01.
    @type rotation: int
    @params rotation: the degree of rotation. default is closewise. must be oone of 0, 90, 180, 270
    @rtype: tuple
    @return: (x, y) the coordniate tuple of the matched sub image center point. return None if sub image not found or any exception.
    '''
    for img in [subPath, srcPath]: assert os.path.exists(img) , "No such image:  %s" % (img)
    method = cv2.cv.CV_TM_SQDIFF_NORMED #Parameter specifying the comparison method 
    try:
        subImg = cv2.imread(subPath,colormode) #Load the sub image
        srcImg = cv2.imread(srcPath,colormode) #Load the src image
        result = cv2.matchTemplate(subImg, srcImg, method) #comparision
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result) #Get the minimum squared difference
        if minVal <= threshold: #Compared with the expected similarity
            minLocXPoint, minLocYPoint = minLoc
            subImgRow, subImgColumn = subImg.shape[:2]
            centerPointX = minLocXPoint + int(subImgColumn/2)
            centerPointY =  minLocYPoint + int(subImgRow/2)
            #if image is binary format shape return (w, h) else return (w, h, d)
            (height, width) = srcImg.shape[:2]
            centerPoint = (minLocXPoint if centerPointX > width else centerPointX, minLocYPoint if centerPointY > height else centerPointY )
            return adaptRotation(coord=centerPoint, size=(height, width), rotation=rotation)
        else:
            return None    
    except Exception, e:
        return None

def adaptRotation(coord, size, rotation=0):
    if rotation == 0:
        return coord
    elif rotation == 90:
        height, width = size
        x_coord, y_coord = coord
        x = y_coord
        y = width - x_coord
        return (x, y)
    elif rotation == 180:
        height, width = size
        x_coord, y_coord = coord
        x = x_coord
        y = y_coord       
        return (x, y)
    elif rotation == 270:
        height, width = size
        x_coord, y_coord = coord
        x = height - y_coord
        y = x_coord
        return (x, y)
    else:
        return None
