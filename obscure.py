from Googlebox import API
from skimage.measure import find_contours
from skimage import io
import skimage
import glob
from skimage import color
import os
from tqdm import tqdm
import numpy as np
import random
#1 meter= 0.00000905 didderence in lattitudes
query_points_dir= "/Users/madhav/Documents/RES/Todo/TODO3/query_fragments"
key_list= ["keeeeeeeyyyssss"]
key_index= 0
os.chdir(query_points_dir)
x= lambda x: x.split("/")[-1]
Image_List= list(map(x, glob.glob(query_points_dir+ "/*.png")))
handler= API(key=key_list[0], MapZoom=21, ImageSize="640x640", AreaLatLongBound=(1,1,1,1))
previous_pixel= []
for image in Image_List:
    cordinates= image.split("_")[0: 2]
    Image= color.rgb2gray(io.imread(image))
    contours_in_pixel= find_contours(Image, 0.3)
    centroids_in_pixel= list(map(handler.Centroid, contours_in_pixel))
    centroid_in_cordinates= []
    for centroid in centroids_in_pixel:
        centroid_in_cordinates.append(handler.getPointLatLng(x= centroid[0], y= centroid[1], clat= float(cordinates[0]),clng=float(cordinates[1])))
    #print(centroid_in_cordinates)
    for pixel in centroid_in_cordinates:
        previous_pixel.append(pixel)
        distance= handler.distance_lat_long(previous_pixel[-1], handler.getPointLatLng(x= pixel[0], y= pixel[1], clat= float(cordinates[0]),clng=float(cordinates[1])))
        #print("Distance",distance)
        #add= handler.reversegeocode(localised[0], localised[1])
        if 1:      #and clause for latlong being of ROOFTOP
            try:
                #Adding some noise here about 500 meter distance
                Image= handler.getImage(clat= pixel[0]+ random.uniform(0, 0.0045025),clong= pixel[1]+ random.uniform(0, 0.0045025), save= True)
            except:
                if key_index>= len(key_list):
                    print("Keys Exhausted")
                else:
                    key_index= key_index+ 1
                    print("Using {} key".format(key_index))
                    handler.updatekey(key_list[key_index])
        else:
            #previous_pixel= previous_pixel[:len(previous_pixel)-1]
            pass
