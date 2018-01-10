# -*- coding: utf-8 -*-
"""
Created on Sat Nov  4 10:38:45 2017

@author: Jannik
"""

import sys
sys.path.append("C:/Users/janni/Documents/Masterarbeit/src/github")
sys.path.append("C:/Users/janni/Documents/Masterarbeit/src/github/_LBP")

from skimage import io
from skimage import data, segmentation
import rgb_indices as rgb
import utils as u
import numpy as np
from skimage.util import img_as_float
from skimage.segmentation import slic, felzenszwalb
from skimage.segmentation import quickshift
from skimage.segmentation import mark_boundaries
from skimage.transform import rescale

from skimage.color import rgb2gray, rgb2hsv, hsv2rgb, rgb2lab
from matplotlib import pyplot as plt

import lbp
from skimage.transform import rotate
from skimage.color import label2rgb

from sklearn.feature_extraction.image import grid_to_graph
from sklearn.cluster import AgglomerativeClustering
import scipy as sp

import networkx as nx

#from bowrag import BOW_RAG, cumu_diff
import bow_rag
import bow_diff

import pandas as pd
from sklearn.decomposition import PCA

import agglomerativ_clustering as ac

#def AgglCluster(g, attr_name, fs_spec, n_clusters=2, pixel_min=-1, superpixel_min=2, ):
#    if isinstance(fs_spec, bow_rag.BOW_RAG.fs_spec):
#        connectivity = nx.adjacency_matrix(g, weight=None)
#        g.clustering(attr_name, 'AgglomerativeClustering', fs_spec, n_clusters=n_clusters, linkage="ward", connectivity=connectivity)
#    
#    elif isinstance(fs_spec, list):
#        print("New Cascade Step")
#        for node in g.__iter__():
#                g.node[node][attr_name] = None
#        for fs in fs_spec:
#            if not isinstance(fs, bow_rag.BOW_RAG.fs_spec):
#                raise TypeError("Must be BOW_RAG.fs_spec!")
#            
#            if len(fs[1]) < superpixel_min:
#                #print("Cluster too small")
#                g.node[fs[1][0]][attr_name] = str(fs.label)# + str(3)
#                continue
#            
#            subset = g.subgraph(nbunch=list(fs[1]))
#            
#            pixel_count = 0
#            
#            if pixel_min >= 0:
#                for n in subset:
#                    pixel_count += subset.node[n]['pixel_count']
#                if pixel_count <= pixel_min:
#                    #print("In FS ", fs.label, " are ", pixel_count, " Pixel. It gets Name ", fs.label)
#                    for n in subset:
#                        g.node[n][attr_name] = str(fs.label)# + str(4)
#                    continue
#            
#            connectivity = nx.adjacency_matrix(subset, weight=None)
#                        
#            cluster_obj = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward',
#                               connectivity=connectivity).fit(fs.array)       
#            for node, label in zip(fs.order, cluster_obj.labels_):
#                g.node[node][attr_name] = str(fs.label) + str(label)
#
#
#def AgglCluster_Cascade(g, fs_attr, attr_name, n_cascade=2, automatic=False, pixel_min=-1):
#    runs = 0
#    cascade = True
#    fs1 = g.basic_feature_space_array(fs_attr)
#    
#    if not automatic:
#        for run in range(0, n_cascade):
#            AgglCluster(g, attr_name+str(run), fs1, 2, pixel_min)        
#            fs1 = g.attribute_divided_fs_arrays(fs_attr, attr_name+str(run))
#        runs = n_cascade
#    else:
#        while cascade:            
#            AgglCluster(g, attr_name+str(runs), fs1, 2, pixel_min)        
#            fs1 = g.attribute_divided_fs_arrays(fs_attr, attr_name+str(runs))
#            if runs > 0:
#                for n in g:
#                    if g.node[n][attr_name+str(runs-1)] != g.node[n][attr_name+str(runs)]:
#                        cascade = True
#                        break
#                    else:
#                        cascade = False
#            runs += 1
#    return runs            
#            

####################################
#image = io.imread("C:/Users/janni/Documents/Masterarbeit/Data/ra_neu/ra3/ra3_small_contrast.jpg")
image = io.imread("C:/Users/janni/Documents/Masterarbeit/Data/ResearchArea/RA1/orthoRA.jpg")
#image = io.imread("C:/Users/janni/Desktop/forest.jpg")
height = io.imread("C:/Users/janni/Documents/Masterarbeit/Data/ResearchArea/RA1/dsmRA1_test16_resampled.png")
#height = io.imread("C:/Users/janni/Documents/Masterarbeit/Data/ra_neu/ra3/ra3_height_small.png")


im_gray = rgb2gray(image)
im_gray = img_as_float(im_gray)

image = u.ZerosToOne(image, 1)
image = img_as_float(image)
height = img_as_float(height)

image = rescale(image, .3)
im_gray = rescale(im_gray, .3)
height = rescale(height, .3)


gli = rgb.GLI(image)
vvi = rgb.VVI(image)
ntdi = rgb.NDTI(image)
ci = rgb.CI(image)
bi = rgb.BI(image)
si = rgb.SI(image)
tgi = rgb.TGI(image)
ngrdi = rgb.NGRDI(image)

gli = u.NormalizeImage(gli)
vvi = u.NormalizeImage(vvi)
ntdi = u.NormalizeImage(ntdi)
ci = u.NormalizeImage(ci)
bi = u.NormalizeImage(bi)
si = u.NormalizeImage(si)
tgi = u.NormalizeImage(tgi)
ngrdi = u.NormalizeImage(ngrdi)

df = pd.DataFrame({'gli':gli.flatten(), 'vvi':vvi.flatten(), 'ntdi':ntdi.flatten(), 
                   'ci':ci.flatten(), 'bi':bi.flatten(), 'si':si.flatten(), 
                   'tgi':tgi.flatten(), 'ngrdi':ngrdi.flatten(),
                   'r':image[:,:,0].flatten(), 'g':image[:,:,1].flatten(), 'b':image[:,:,2].flatten()})

pca = PCA(n_components=3).fit(df)
pca_reduced = pca.transform(df)

dim1 = u.ImageFromArray(pca_reduced[:,0], image)

dim1 = u.NormalizeImage(dim1)
dim1Inverted = 1-dim1

comp1 = u.MergeChannels([dim1Inverted,vvi,tgi])

segments_slic = slic(image, n_segments=800, compactness=12, sigma=1)
#segments_slic = felzenszwalb(image, scale=70, sigma=1, min_size=2500)
#segments_slic = quickshift(image, kernel_size=12, max_dist=12, ratio=0.5)
print('SLIC number of segments: {}'.format(len(np.unique(segments_slic))))
f, ax = plt.subplots(figsize=(10, 10))
ax.imshow(mark_boundaries(image, segments_slic));

# settings for LBP
import frequency

test = frequency.FrequencySetup(im_gray, 5, 80, 10, 1.0, 0.1)

print(test.cut_value, test.lbp_radius)

#plt.imshow(test.result(), cmap="gray")


METHOD = 'default'
radius = 8

n_points = 8 

#nilbp = lbp.ni_lbp(im_gray, n_points, test.lbp_radius)
radlbp = lbp.radial_lbp(im_gray, n_points, test.lbp_radius*2, test.lbp_radius, 'ror')
anglbp = lbp.angular_lbp(im_gray, 4, test.lbp_radius)
nilbp = lbp.local_binary_pattern(im_gray, None, test.lbp_radius, radius, method='ror', nilbp = True)

from bow_container import hist
import lbp_bins

rad_lbp_BINS = lbp_bins.lbp_bins(n_points, "ror")
ang_lbp_BINS = lbp_bins.lbp_bins(4, "default")
ni_lbp_BINS = lbp_bins.lbp_bins(n_points, "ror")



######################################
imageLab = rgb2lab(image)

Graph = bow_rag.BOW_RAG(segments_slic)
print(nx.info(Graph))
Graph.add_attribute('color', u.NormalizeImage(imageLab), np.mean)
#Graph.add_attribute('height', height, np.median)
#Graph.normalize_attribute('color', value=255)
Graph.add_attribute('var', u.NormalizeImage(im_gray), np.var)
Graph.add_attribute("pc1", dim1Inverted, np.mean)
Graph.add_attribute("pc1var", dim1Inverted, np.var)

Graph.add_attribute('ni_lbp', nilbp, hist, vbins=ni_lbp_BINS)
Graph.normalize_attribute('ni_lbp')
Graph.add_attribute('rad_lbp', radlbp, hist, vbins=rad_lbp_BINS)
Graph.normalize_attribute('rad_lbp')
Graph.add_attribute('ang_lbp', anglbp, hist, vbins=ang_lbp_BINS)
Graph.normalize_attribute('ang_lbp')

lbp_config = {'ni_lbp':0.01, 'rad_lbp':0.01, 'ang_lbp':0.01}
#lbp_config = {'ni_lbp':0.01}
lbp_fs = Graph.hist_to_fs_array(lbp_config)

Graph.cluster_affinity_attrs("texture", "KMeans", lbp_fs, n_clusters=5)


fs_attrs = {'color':1.2, 'var':.3, 'pc1': .7, 'pc1var': .7, "texture": .7}
fs1 = Graph.basic_feature_space_array(fs_attrs)



connectivity = nx.adjacency_matrix(Graph, weight=None)

n_clusters = 2  # number of regions

#nr = ac.AgglCluster_Cascade(Graph, fs_attrs, "cluster", automatic = True, pixel_min =  10000, superpixel_min = 2, variance=True, limit_percent=5)

Graph.clustering("cluster", 'KMeans', fs1, n_clusters=2)
#Graph.clustering('clusterbla', 'AgglomerativeClustering', fs1, n_clusters=40, linkage="ward", connectivity=connectivity)
fs2 = Graph.attribute_divided_fs_arrays(fs_attrs, 'cluster')
Graph.clustering("cluster1", 'KMeans', fs2, n_clusters=2)

fs3 = Graph.attribute_divided_fs_arrays(fs_attrs, 'cluster1')
Graph.clustering("cluster2", 'KMeans', fs3, n_clusters=2)

#Graph.clustering("k", 'KMeans', fs1, n_clusters=3)

from skimage import color
cluster_img = Graph.produce_cluster_image('cluster1')
f, ax = plt.subplots(figsize=(10, 10))
ax.imshow(cluster_img, cmap=plt.cm.spectral)

import single_feature
single_feature.SingleFeature(Graph, fs3, "cluster1")

cluster_img2 = Graph.produce_cluster_image('cluster1')
f2, ax2 = plt.subplots(figsize=(10, 10))
ax2.imshow(cluster_img2, cmap=plt.cm.spectral)