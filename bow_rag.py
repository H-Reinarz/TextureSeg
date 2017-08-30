#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Mon Aug  7 14:25:44 2017

@author: hre070
'''

#Imports
from skimage.future import graph
#import networkx as nx
#from itertools import repeat
import statistics as stats
import numpy as  np
import copy

from bow_diff import weight_wrapper
from bow_container import hist

#Subclass of RAG specified for BOW classification

class BOW_RAG(graph.RAG):
    
    def __init__(self, seg_img, tex_img, color_image, tex_bins, color_bins, **attr):
        
        #Call the RAG constructor
        super().__init__(label_image=seg_img, connectivity=2, data=None, **attr)
                
        #Set node attributes
        for n in self.__iter__():
            #get color values for super pixel
            label_mask = seg_img == n
            masked_color = color_image[label_mask]
            
            #account for color channels: one hist per channel
            if len(masked_color.shape) == 2:
                color_hists = [hist(masked_color[:,dim], bins=color_bins) for dim in range(masked_color.shape[1])]
            else:
                color_hists = hist(masked_color, bins=color_bins)
            
            #Assign attributes to node
            self.node[n].update({'labels': [n],
                              'pixel_count': seg_img[label_mask].size,
                              'tex': hist(set(tex_bins)),
                              'color': color_hists})
    
        #Populate the node attributes with data
        for a, b in np.nditer([seg_img, tex_img]):                       
            #BOW attribute individual bin incrementation
            self.node[int(a)]['tex'].increment(int(b))
            
        
        #Normalize all histograms
        for n in self.__iter__():
            self.node[n]['tex'].normalize(self.node[n]['pixel_count'])
            for c_hist in self.node[n]['color']:
                c_hist.normalize(self.node[n]['pixel_count'])
        
        
        
        #Init edge weight statistics
        self.edge_weight_stats = {}

    
    def deepcopy_node(self, node):       
        #create mutable copy of the node for calculation
        return copy.deepcopy(self.node[node])
        


    def calc_edge_weights(self, attr_dict, attr_label='weight'):
        
        #Iterate over edges and calling weight_func on the nodes
        for n1, n2, d in self.edges_iter(data=True):
            d.update(weight_wrapper(self, n1, n2, attr_dict, attr_label=attr_label))
            
     
    def get_edge_weight_list(self, attr_label='weight'):
        return sorted(list(data[attr_label] for n1,n2,data in self.edges(data=True)))
        
        
    def calc_edge_weight_stats(self, attr_label='weight'):
        weight_list = self.get_edge_weight_list(attr_label)
        
        self.edge_weight_stats['min'] = min(weight_list)
        self.edge_weight_stats['max'] = max(weight_list)
        self.edge_weight_stats['mean'] = stats.mean(weight_list)
        self.edge_weight_stats['median'] = stats.median(weight_list)
        self.edge_weight_stats['stdev'] = stats.stdev(weight_list)

    
    def get_edge_weight_percentile(self, p, attr_label='weight', as_threshhold=False):
        weight_list = self.get_edge_weight_list(attr_label)
        
        index = round(len(weight_list)*(p/100))
        
        if as_threshhold:
           result = (weight_list[index] +  weight_list[index+1]) /2
           return result
        else:
            return weight_list[index]
        
        
        
#Simple merging function
def _bow_merge_simple(graph, src, dst):
    
    #pixel counter
    graph.node[dst]['pixel_count'] += graph.node[src]['pixel_count']
    
    #texture histogram
    graph.node[dst]['tex'] += graph.node[src]['tex']
    graph.node[dst]['tex'].normalize(graph.node[dst]['pixel_count'])
    
    #color histograms
    for ix, h_src in enumerate(graph.node[src]['color']):
        graph.node[dst]['color'][ix] += h_src
        graph.node[dst]['color'][ix].normalize(graph.node[dst]['pixel_count'])
    
    