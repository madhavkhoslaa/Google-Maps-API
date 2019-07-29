from requests.utils import quote
from skimage import color
import numpy as np
from skimage.measure import find_contours, points_in_poly, approximate_polygon
import math
import skimage
import cv2
from area import area
from skimage import io
from tqdm import tqdm
import requests

class API():
    def __init__(self, key, AreaLatLongBound, MapZoom, ImageSize):
        assert isinstance(key, str), "Invalid Key"
        assert isinstance(
            AreaLatLongBound,
            tuple) or isinstance(
            AreaLatLongBound,
            list)
        assert isinstance(ImageSize, str)
        """AreaLatLongBound=(topLeftLat, topLeftLong, bottomRightLat, bottomRightLong)"""
        self.key= key
        self.AreaLatLongBound= tuple(AreaLatLongBound)
        self.MapZoom = str(MapZoom)
        self.ImageSize = ImageSize
        self.UniqueContours = list()
        self.RejectedContours = list()
        self.AllContour = list()
        self.SmallContours = list()
        self.query_pts = self.createQueryFragments(self.AreaLatLongBound[0], self.AreaLatLongBound[1], self.AreaLatLongBound[2], self.AreaLatLongBound[3])
        self.faddr= []
        self.geo= []
        self.centroids = []
        self.unique_all_contours = []
        self.all_contours_list= []
        self.clat_clong_contours= dict()


    def createQueryFragments(self, topLeftLat, topLeftLong, bottomRightLat, bottomRightLong):
        down = 0.005900
        right = 0.006600
        mar = 0.0002
        return np.mgrid[topLeftLat - (down/2):bottomRightLat:-0.005700, topLeftLong + (right/2):bottomRightLong:0.006400].reshape(2, -1).T

    def white_image(self, im):
        # returns a white image of the shape input image
        return cv2.bitwise_not(np.zeros(im.shape, np.uint8))
    def reversegeocode(self, lat, long_):
        base= "https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}".format(str(lat), str(long_), self.key)
        r = requests.get(base).json()
        return r
    def distance_lat_long(self, point1, point2):
        R = 6373.0
        point1= list(map(math.radians, point1))
        point2= list(map(math.radians, point2))
        dlat= math.radians(point1[0]- point2[0])
        dlon= math.radians(point1[1]- point2[1])
        a = math.sin(dlat / 2)**2 + math.cos(point1[0]) * math.cos(point2[0]) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R* c* 1000

    def area_frm_cnt(self, cnt):
        # finds the area of a contour
        c = np.expand_dims(cnt.astype(np.float32), 1)
        c = cv2.UMat(c)
        return cv2.contourArea(c)

    def drawShape(self, img, coordinates, clr):
        """Takes Image as Input and draws the co-ordinates on it
            clor is inputed as [R, G, B] Values"""
        img = color.gray2rgb(img)
        coordinates = np.array(coordinates)
        img[coordinates[:, 0], coordinates[:, 1]] = clr
        arr = coordinates.sum(axis = 0).reshape((2, 1))/coordinates.shape[0]
        img[int(arr[0]), int(arr[1])] = clr
        return img

    @classmethod
    def is_arr_in_list(self, myarr, list_arrays):
        return next((True for elem in list_arrays if elem is myarr), False)
    @classmethod
    def arrayCnt2area(self,l):
        # l is the name of nX2 array
        return area({'type':'Polygon','coordinates':[l.tolist()]})
    
    def Centroid(self, arr):
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr)
        else:
            pass
        return (arr.sum(axis=0)) / (arr.shape[0])

    def sampleMeDown(self, arr):
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr)
        else:
            pass
        if(arr.shape[0] <= 90):
            return arr
        factor = int(np.floor(arr.shape[0] / 90)) + 1
        ret = arr[::factor, :]
        return ret

    def getPointLatLng(self, x, y, clat, clng):
        h, w = map(int, self.ImageSize.split("x"))
        zoom = int(self.MapZoom)
        parallelMultiplier = math.cos(clat * math.pi / 180)
        degreesPerPixelX = 360 / math.pow(2, zoom + 8)
        degreesPerPixelY = 360 / math.pow(2, zoom + 8) * parallelMultiplier
        pointLat = clat - degreesPerPixelY * (y - h / 2)
        pointLng = clng + degreesPerPixelX * (x - w / 2)
        return (pointLat, pointLng)

    def contours2latLong(self, arr, center_latitude, center_longitude):
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr)
        else:
            pass
        for ix in range(arr.shape[0]):
            arr[ix] = np.asarray(
                self.getPointLatLng(
                    arr[ix][1],
                    arr[ix][0],
                    center_latitude,
                    center_longitude))
        return arr
        
    def updatekey(self, key):
        assert isinstance(key, str)
        self.key= key

    def getboundries(self, center_latitude, center_longitude, save=True):
        self.center_latitude= center_latitude
        self.center_longitude= center_longitude
        str_Center = str(center_latitude) + ',' + str(center_longitude)
        safeURL_Style = quote(
            'feature:landscape.man_made|element:geometry.stroke|visibility:on|color:0xffffff|weight:1')
        urlBuildings = "http://maps.googleapis.com/maps/api/staticmap?center=" + str_Center + "&zoom=" + self.MapZoom + "&format=png32&sensor=false&size=" + self.ImageSize + "&maptype=roadmap&style=visibility:off&style=" + safeURL_Style + '&key='+ str(self.key)
        boundry_image = skimage.color.rgb2gray(skimage.io.imread(urlBuildings))
        self.Img = boundry_image
        boundry_image = np.where(
            boundry_image > np.mean(boundry_image), 0.0, 1.0)
        boundry_image_raw = boundry_image
        contoursBuildings = find_contours(boundry_image, 0.1)
        # keep only the closed contours
        contoursBuildings = [ks for ks in contoursBuildings if (
            ks[0, 1] == ks[-1, 1]) and (ks[0, 0] == ks[-1, 0])]
        # keep only those contours which have length more than 10
        contoursBuildings = [k for k in contoursBuildings if len(k) > 10]
        self.AllContour.extend(contoursBuildings)
        if save:
            skimage.io.imsave(
                "Skel/CentreLatLong:{}MapZoom:{}.png".format(
                    str_Center,
                    self.MapZoom),
                boundry_image_raw)
        else:
            pass
        self.clat_clong_contours.update({(center_latitude, center_longitude): contoursBuildings})
        return boundry_image_raw

    def getImage(self, clat, clong, save= True):
        base= "https://maps.googleapis.com/maps/api/staticmap?center={},+{}6&zoom={}&scale=1&size={}&maptype=satellite&format=png&visual_refresh=true&key={}".format(clat, clong, self.MapZoom, self.ImageSize, self.key)
        print(base)
        Img= skimage.io.imread(base)
        if save== True:
            skimage.io.imsave(fname= "Sat/satellite Lat:{} Long:{}.png".format(clat, clong), arr= Img)
        return Img
