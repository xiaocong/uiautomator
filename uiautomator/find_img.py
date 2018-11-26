#coding=utf-8
try:
    import cv2
except ImportError, e:
    print e

import numpy as np


FLANN_INDEX_KDTREE = 1  # bug: flann enums are missing
FLANN_INDEX_LSH    = 6

def _middlePoint(pts):
    '''get center positon by given points'''
    def add(p1, p2):
        return (p1[0]+p2[0], p1[1]+p2[1])
    def distance(p1, p2):
        import math
        l2 = (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
        return math.sqrt(l2)
    length = len(pts) # point set length
    sumx, sumy = reduce(add, pts)
    point = sumx/length, sumy/length
    # filter out ok points
    avg_distance = sum([distance(point, p) for p in pts])/length
    good = []
    sumx, sumy = 0.0, 0.0
    for p in pts:
#         print 'point: %s, distance: %.2f' %(p, distance(p, point))
        if distance(p, point) < 1.2*avg_distance:
            good.append(p)
            sumx += p[0]
            sumy += p[1]
        else:
            pass
#             print 'not good', p
    point = map(long, (sumx/len(good), sumy/len(good)))
    return point

def init_feature(name):
    '''choice algorithm'''
    chunks = name.split('-')
    if chunks[0] == 'sift':
        detector = cv2.SIFT()
        norm = cv2.NORM_L2
    elif chunks[0] == 'surf':
        detector = cv2.SURF(800)
        norm = cv2.NORM_L2
    elif chunks[0] == 'orb':
        detector = cv2.ORB(400)
        norm = cv2.NORM_HAMMING
    else:
        return None, None
    if 'flann' in chunks:
        if norm == cv2.NORM_L2:
            flann_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
        else:
            flann_params= dict(algorithm = FLANN_INDEX_LSH,
                               table_number = 6, # 12
                               key_size = 12,     # 20
                               multi_probe_level = 1) #2
        matcher = cv2.FlannBasedMatcher(flann_params, {})  # bug : need to pass empty dict (#1329)
    else:
        matcher = cv2.BFMatcher(norm)
    return detector, matcher


def filter_matches(kp1, kp2, matches, ratio = 0.75):
    '''过滤匹配点'''
    mkp1, mkp2 = [], []
    for m in matches:
        if len(m) == 2 and m[0].distance < m[1].distance * ratio:
            m = m[0]
            mkp1.append( kp1[m.queryIdx] )
            mkp2.append( kp2[m.trainIdx] )
    p1 = np.float32([kp.pt for kp in mkp1])
    p2 = np.float32([kp.pt for kp in mkp2])
    return p1, p2

def _find_position(img1, H = None):
    '''find img position'''
    h1, w1 = img1.shape[:2]
    corners = np.float32([[0, 0], [w1, 0], [w1, h1], [0, h1]])
    corners = np.int32( cv2.perspectiveTransform(corners.reshape(1, -1, 2), H).reshape(-1, 2))
#     arr = corners < 0
#     if True in arr:
#         return None
    return _middlePoint(corners)

def find_img_position(query, origin, algorithm='sift',radio=0.75, colormode=1):
    '''
      return position of query in origin,by ratio and algorithm
    :Args:
        - origin - raw picture 
        - query -  need search picture
        - ratio -  similarity 
        - algorithm - using algorithm
    :Usage:
      find_img_position('query.png','qq.png','sift', 0.75)  
    '''
    img1 = cv2.imread(query, colormode)
    img2 = cv2.imread(origin, colormode)
    detector, matcher = init_feature(algorithm)
    kp1, desc1 = detector.detectAndCompute(img1, None)
    kp2, desc2 = detector.detectAndCompute(img2, None)
    raw_matches = matcher.knnMatch(desc1, trainDescriptors = desc2, k = 2) #2
    p1, p2 = filter_matches(kp1, kp2, raw_matches)
    if len(p1) >= 4:
        H, status = cv2.findHomography(p1, p2, cv2.RANSAC, 5.0)
        if round(np.sum(status)/float(len(status)),2) < radio:
            return None
        return _find_position(img1, H)
    return None

if __name__ == '__main__':
    print find_img_position("test_black.png", "test1.bmp", algorithm="orb",radio=0.6)

