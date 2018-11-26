#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python img deal tools."""
import os,base64,tempfile
from PIL import Image, ImageChops
from find_img import find_img_position

def is_base64(strword):
    try:
        if len(strword) < 200:
            if os.path.exists(strword):
                return False
        else:
            base64.b64decode(strword)
            return True
    except:
        pass
    return False

class ImageUtil:
    '''
    image deal class
    '''
    @staticmethod
    def find_image_positon(query, origin, algorithm='sift', radio=0.75, colormode=1):
        if not os.path.exists(query):
            raise IOError,('No such file or directory:%s'%query)
        position = find_img_position(query, origin, algorithm, radio, colormode)
        return position

    @staticmethod
    def compare_stream(strStream, target_file):
        '''
        file stream compare
        :Args:
         - strStream: strStrem by driver.get_screenshot_as_png.
         - target_file: need compared target file.
        '''
        temp=tempfile.mktemp()
        with open(temp,"wb") as f:
            f.write(strStream)
        simily = ImageUtil.compare(target_file, temp)
        if os.path.exists(temp):os.remove(temp)
        return simily
    
    @staticmethod
    def compare(f1, f2):
        """
        Calculate the similarity  between f1 and f2
        return similarity  0-100
        """
        img1 = Image.open(f1)
        img2 = Image.open(f2,'r')
        # if image size is not equal, return 1
        if img1.size[0] != img2.size[0] or img1.size[1] != img2.size[1]:
            return 0
        size = (256, 256)
        img1 = img1.resize(size).convert('RGB')
        img2 = img2.resize(size).convert('RGB')
        # # get the difference between the two images
        h = ImageChops.difference(img1, img2)
        size = float(img1.size[0] * img1.size[1])
        diff = 0
        for p in list(h.getdata()):
            if p != (0, 0, 0):
                diff += 1
        return round((1 - (diff / size)) * 100, 2)

    @staticmethod
    def crop(startx, starty, endx, endy, scrfile, destfile):
        """
        cut img by the given coordinates and picture, then make target file
        """
        box = (startx, starty, endx, endy)
        img = Image.open(scrfile)
        cut_img = img.crop(box)
        if cut_img:
            cut_img.save(destfile)
            return True
        else:
            return False