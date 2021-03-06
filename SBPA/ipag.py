#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Mon Aug  7 14:25:44 2017

@author: hre070
'''
import statistics as stats
from collections import namedtuple, Counter
import copy
import networkx as nx
import numpy as  np
from .histogram import Hist
from skimage.future.graph import RAG
from skimage.measure import regionprops
import sklearn.cluster
from scipy.spatial.distance import euclidean
from ._LBP._sp_neighbors import _count_transitions

def get_internal_distance(feature_space, percentile=100, func=euclidean):
    '''Return a specified percentile of the maximum distance
    computable by func within the given feature space. Returns the maximum distance as default.'''
    
    assert isinstance(feature_space, IPAG.feature_space), 'Must be IPAG.feature_space!'
    
    max_list = [np.max(feature_space.array[:,col]) for col in range(feature_space.array.shape[1])]
    
    min_list = [np.min(feature_space.array[:,col]) for col in range(feature_space.array.shape[1])]
    
    return (percentile/100)*func(np.array(min_list), np.array(max_list))
    

def feature_space_centroid(feature_space, func=np.median):
    '''Returns the centroids of a feature space by averaging out dimensions
    with a given function. Uses median as default'''
    
    assert isinstance(feature_space, IPAG.feature_space), 'Must be IPAG.feature_space!'
    
    centroid_list = [func(feature_space.array[:,col]) for col in range(feature_space.array.shape[1])]
        
    return np.array(centroid_list)




def calc_attr_value(*, array, func, **kwargs):
    '''Helper function to apply a given function to
    a numpy array (i.e. an image) and return the result.
    If the array has multiple dimensions, a list of values is returned.'''
    #account for multi channels: one Hist per channel
    if len(array.shape) == 2:
        result = [func(array[:, dim], **kwargs) for dim in range(array.shape[1])]
    else:
        result = func(array, **kwargs)

    return result



#Subclass of RAG specified for BOW classification
class IPAG(RAG):
    '''Image Patch Adjacency Graph (IPAG):
    Subclass of the 'region adjacency graph' (RAG) in skimage to accomodate for
    dynamic attribute assignment, neighbourhood weighting and node clustering.'''

    attr_config = namedtuple('AttributeConfig', ['img', 'func', 'kwargs'])

    feature_space = namedtuple('feature_space', ['array', 'order', 'label', 'connectivity'])


    def __init__(self, seg_img, **attr):
        '''IPAG is initialized with the parents initializer along
        with additional attributes.'''
        ###DEPRECATED
        #Call the RAG constructor
        #super().__init__(label_image=seg_img, connectivity=1, data=None, **attr)
        ###
        
        #Call the networkx.Graph constructor
        super(RAG, self).__init__(**attr)

        if self.number_of_nodes() == 0:
            self.max_id = 0
        else:
            self.max_id = max(self.nodes_iter())

        transition_array = _count_transitions(seg_img)
        
        rows, columns = transition_array.shape
        
        max_length = 0
        for row in range(rows):
            for col in range(row+1):
                count = transition_array[row, col]
                if count > 0:
                     super().add_edge(row, col, length=count)
                     if count > max_length: max_length = count
                
        for n1, n2, data in self.edges(data=True):
            data.update(norm_length = round(data['length']/max_length, 2))


        #Store seg_img as attribute
        self.seg_img = seg_img


        #Node attribute reference information
        self.attr_func_configs = {}
        self.attr_norm_val = {}

        #Init edge weight statistics
        self.edge_weight_stats = {}

        #dict for storing cluster properties
        self.cluster_centers = {}

        #Setup simple pixel index map
        index_map = np.arange(seg_img.size, dtype=np.int64)
        index_map = index_map.reshape(seg_img.shape)

        #Set indipendent node attributes
        for node in self.__iter__():
            #get color values for super pixel
            label_mask = self.seg_img == node

            #Assign attributes to node
            self.node[node].update({'labels': [node],
                                    'pixels': set(index_map[label_mask]),
                                    'pixel_count': seg_img[label_mask].size})

    def mask(self, *nodes):
        '''Method to produce a index mask for a set
        of nodes to address corresponding pixels in the image.'''
        mask_set = set()
        for node in nodes:
            for pixel in self.node[node]['pixels']:
                mask_set.add(pixel)

        return np.unravel_index(list(mask_set), self.seg_img.shape)


    def deepcopy_node(self, node):
        '''Return a deep copy of a node dictionary.'''
        #create mutable copy of the node for calculation
        return copy.deepcopy(self.node[node])


    def add_attribute(self, name, image, function, **func_kwargs):
        '''Adds an attribute ('name') to each node by calling 'calc_attr_value()'
        on the subset of the image that is represented by the node.'''

        self.attr_func_configs[name] = IPAG.attr_config(image, function, func_kwargs)

        #Set node attributes
        for node in self.__iter__():
            #get color values for super pixel
            masked_image = image[self.mask(node)]

            attr_value = calc_attr_value(array=masked_image, func=function, **func_kwargs)

            #Assign attributes to node
            self.node[node].update({name:attr_value})

    

    def produce_connectivity_matrix(self, subset, weight='norm_length'):
        '''Return a connectivity matrix of a subset of nodes.'''
        subset = set(subset)
        connectivity = nx.adjacency_matrix(self, subset, weight)

        return connectivity


    def add_attribute_from_lookup(self, new_attribute, attribute, lookup_dict):
        '''Assign a new node attribute with values from the provided
        look up dictionary corresponding to an existing attribute.'''

        for node in self.__iter__():
            key = self.node[node][attribute]
            self.node[node].update({new_attribute: lookup_dict[key]})


    def add_regionprops(self):
        '''Function to assign geometric properties of the represented region
        as node attributes. IN DEVELOPMENT!'''

        self.seg_img += 1

        for reg in regionprops(self.seg_img):
            self.node[reg.label-1]["Y"] = round(reg.centroid[0]/self.seg_img.shape[0], 3)
            self.node[reg.label-1]["X"] = round(reg.centroid[1]/self.seg_img.shape[1], 3)

        self.seg_img -= 1


    def normalize_attribute(self, attribute, value=None):
        '''Normalize a node attribute with a given denominator.'''

        self.attr_norm_val[attribute] = value

        for node in self.__iter__():
            if isinstance(self.node[node][attribute], list):
                for index, element in enumerate(self.node[node][attribute]):
                    if isinstance(element, Hist):
                        element.normalize(self.node[node]['pixel_count'])
                    else:
                        self.node[node][attribute][index] = element/value

            else:
                if isinstance(self.node[node][attribute], Hist):
                    self.node[node][attribute].normalize(self.node[node]['pixel_count'])
                else:
                    self.node[node][attribute] /= value


    def delete_attribute(self, attribute):
        '''Delete a given attribute.'''
        for node in self.__iter__():
            if attribute in self.node[node]:
                del self.node[node][attribute]


    def filter_by_attribute(self, attribute, values, subset=None):
        '''Filter the nodes based on their value of a specified attribute.'''

        if subset is None:
            subset = set(self.__iter__())
        else:
            subset = set(subset)

        func = lambda node: self.node[node][attribute] in values

        return list(filter(func, subset))


    def calc_edge_weights(self, weight_func):
        '''Apply a given weighting function to all edges.'''

        #Iterate over edges and calling weight_func on the nodes
        for node1, node2, data in self.edges_iter(data=True):
            data.update(weight_func(self, node1, node2))


    def get_edge_weight_list(self, attr_label='weight'):
        '''Return a sorted value list of a given edge attribute.'''
        return sorted(list(data[attr_label] for node1, node2, data in self.edges(data=True)))


    def calc_edge_weight_stats(self, attr_label='weight'):
        '''Perform descriptive stats on a given edge attribute.
        Result is stored as a graph attribute.'''

        weight_list = self.get_edge_weight_list(attr_label)

        self.edge_weight_stats['min'] = min(weight_list)
        self.edge_weight_stats['max'] = max(weight_list)
        self.edge_weight_stats['mean'] = stats.mean(weight_list)
        self.edge_weight_stats['median'] = stats.median(weight_list)
        self.edge_weight_stats['stdev'] = stats.stdev(weight_list)


    def get_edge_weight_percentile(self, perc, attr_label='weight', as_threshhold=False):
        '''Return the given percentile value for the value list af a specified attribute.
        When 'as_threshhold' is true, the mean of the percentile value
        and the next value is returned.'''

        weight_list = self.get_edge_weight_list(attr_label)

        index = round(len(weight_list)*(perc/100))

        if as_threshhold:
            result = (weight_list[index] +  weight_list[index+1]) /2
            return result
        else:
            return weight_list[index]


    def basic_feature_space_array(self, attr_config, label=[], subset=None, exclude=()):
        '''Arange a specification of attributes into an array that contains
        one row per node. It serves as data points in feature space for clustering operations.
        Nodes are selectable via the 'subset' parameter
        and excludable via the 'exclude' parameter.'''

        if subset is None:
            subset = set(self.__iter__())
        else:
            subset = set(subset)

        exclude = set(exclude)

        weight_list = list()

        for attr, weight in attr_config.items():
            if isinstance(self.node[0][attr], list):
                for element in self.node[0][attr]:
                    weight_list.append(weight)
            else:
                weight_list.append(weight)

        mul_array = np.array(weight_list, dtype=np.float64)

        order_list = list()
        array_list = list()

        for node in self.__iter__():

            if node not in subset or node in exclude:
                continue

            a_row = list()

            for attr in attr_config.keys():
                if isinstance(self.node[node][attr], list):
                    for element in self.node[node][attr]:
                        a_row.append(element)
                else:
                    a_row.append(self.node[node][attr])

            array_list.append(a_row)
            order_list.append(node)
        fs_array = np.array(array_list, dtype=np.float64)
        fs_array *= mul_array

        con_matrix = self.produce_connectivity_matrix((subset - exclude))

        return IPAG.feature_space(fs_array, tuple(order_list), label, con_matrix)


    def feature_space_subset(self, feature_space, subset, label=None):
        '''Returns a feature space subset.'''
        
        filter_func = lambda pair: pair[1] in subset
        
        new_order = []
        index_list = []
        for ix, node_to_keep in filter(filter_func, enumerate(feature_space.order)):
            index_list.append(ix)
            new_order.append(node_to_keep)
        
        
        
        index_array = np.array(index_list, dtype=np.int64)
        
        
        new_array = feature_space.array[index_array, :]
        
        if label is None:
            label = feature_space.label
            
        new_conn_matrix = self.produce_connectivity_matrix(new_order)
            
        return self.feature_space(new_array, tuple(new_order), label, new_conn_matrix)


    def attribute_divided_fs_arrays(self, attr_config, div_attr, max_layer=None, subset=None, exclude=()):
        '''Return a feature space array for every value of a specified attribute.
        Nodes are excludable via the 'exclude' parameter.'''

        temp_attr = 'temp_' + div_attr

        return_list = []

        for node in subset:
            if max_layer is not None:
                self.node[node][temp_attr] = '-'.join(self.node[node][div_attr][:max_layer])
            else:
                self.node[node][temp_attr] = '-'.join(self.node[node][div_attr])

        div_attr_labels = {self.node[node][temp_attr] for node in subset}

        for label in div_attr_labels:
            nodes = self.filter_by_attribute(temp_attr, {label}, subset)
            fs_result = self.basic_feature_space_array(attr_config, label.split('-'), nodes, exclude)

            return_list.append(fs_result)

        self.delete_attribute(temp_attr)
        return return_list


    def hist_to_fs_array(self, attr_config, subset=None, label=[]):
        '''Arange a attribute that is itself a histogram into an array that contains
        one row per node. It serves as data points in feature space for clustering operations.'''

        if subset is None:
            subset = set(self.__iter__())

        array_list = list()
        order_list = list()

        for node in self.__iter__():
            if node in subset:
                row_array = np.array([], dtype=np.float64)
                for attr, factor in attr_config.items():
                    if isinstance(self.node[node][attr], list):
                        for histogramm in self.node[node][attr]:
                            if not isinstance(histogramm, Hist):
                                raise TypeError(f'Wrong type: {type(histogramm)} Must be "Hist"!')
                            part = histogramm(mode='array', normalized=True)
                            part *= factor
                            row_array = np.append(row_array, part)
                    elif isinstance(self.node[node][attr], Hist):
                        part = self.node[node][attr](mode='array', normalized=True)
                        part *= factor
                        row_array = np.append(row_array, part)
                    else:
                        raise TypeError(f'Wrong type: {type(self.node[node][attr])} Must be "Hist"!')

                array_list.append(row_array)
                order_list.append(node)

        fs_array = np.array(array_list, dtype=np.float64)

        con_matrix = self.produce_connectivity_matrix(subset)

        return IPAG.feature_space(fs_array, tuple(order_list), label, con_matrix)


    def clustering(self, attribute, algorithm, feature_space, return_clust_obj=False, **cluster_kwargs):
        '''Perform any clustering operation from sklearn.cluster on a given feature space array
        (as returnd by 'get_feature_space_array()' or 'hist_to_fs_array()').
        Return the cluster label of each node as an attribute.'''

#        #Assert all involved nodes have a list as the given attribute
#        assertion_set = set()
#        for node in feature_space.order:
#            assert(isinstance(self.node[node][attribute], list))
#            assertion_set.add(len(self.node[node][attribute]))
#
#        #Assert all nodes have the same number of cluster layers
#        assert(len(assertion_set) == 1)

        if algorithm == 'AgglomerativeClustering':
            cluster_kwargs['connectivity'] = feature_space.connectivity

        cluster_class = getattr(sklearn.cluster, algorithm)

        if isinstance(feature_space, IPAG.feature_space):
            cluster_obj = cluster_class(**cluster_kwargs)
            cluster_obj.fit(feature_space.array)
            for node, label in zip(feature_space.order, cluster_obj.labels_):
                #print(node, label)
                #Make sure the clustered feature space and the node have the same label
                if attribute in self.node[node]:
                    #print(feature_space.label, " == ", self.node[node][attribute])
                    assert(feature_space.label == self.node[node][attribute])
                    self.node[node][attribute].append(str(label))
                else:
                    self.node[node][attribute] = [str(label)]

            if hasattr(cluster_obj, 'cluster_centers_'):
                new_clusters = cluster_obj.cluster_centers_.shape[0]
                get_center = lambda c: cluster_obj.cluster_centers_[c, :]
                
            else:
                new_clusters = cluster_kwargs['n_clusters']
                
                make_fs = lambda c_layers: self.feature_space_subset(feature_space, \
                                                              self.filter_by_attribute(attribute, [c_layers]))             
                
                get_center = lambda c: feature_space_centroid(make_fs(list(feature_space.label) + [str(c)]))


            for cluster in range(new_clusters):
                center_vector = get_center(cluster)
                
                if attribute not in self.cluster_centers:
                    self.cluster_centers[attribute] = {}
                
                key = list(feature_space.label)
                if key is not None:
                    key.append(str(cluster))
                    key_string = '-'.join(key)
                else:
                    key_string = str(cluster)
                    
                self.cluster_centers[attribute][key_string] = center_vector

            if return_clust_obj:
                return cluster_obj

        elif isinstance(feature_space, list):
            return_clust_obj=False

            for fs in feature_space:
                self.clustering(attribute, algorithm, feature_space, return_clust_obj, **cluster_kwargs)


        else:
            raise TypeError("Must be IPAG.feature_space!")
               
    def cluster_distance(self, attribute, cluster1, cluster2, func=euclidean):
        '''Return a distance measure computed by func of two cluster center vectors
        within the IPAG.cluster_centers dictionary.'''
        
        if attribute not in self. cluster_centers:
            raise KeyError('{} not found in self.cluster_centers!'.format(attribute))
            
        if isinstance(cluster1, list):
            cluster1 = '-'.join(cluster1)

        if isinstance(cluster2, list):
            cluster2 = '-'.join(cluster2)
            
        return func(self.cluster_centers[attribute][cluster1], self.cluster_centers[attribute][cluster2])



    def cluster_affinity_attrs(self, attribute, algorithm, feature_space, stretch=None, limit=None, centralize=1, **cluster_kwargs):
        '''Perform a clustering operation using the clustering() method and store the affinity of the node to each cluster
        (the distance to each )'''

        if stretch is None:
            stretch = (0, 1)
        elif len(stretch) != 2:
            raise ValueError("stretch must contain the two values min and max")
        elif not isinstance(stretch, tuple):
            raise TypeError("stretch must be tuple")

        cluster_obj = self.clustering(attribute, algorithm, feature_space, return_clust_obj=True, **cluster_kwargs)

        n_clusters = cluster_obj.cluster_centers_.shape[0]

        distances = []
        for row, node in enumerate(feature_space.order):

            self.node[node][attribute] = []

            node_vector = feature_space.array[row]

            for cluster in range(n_clusters):
                center_vector = cluster_obj.cluster_centers_[cluster, :]

                distance = np.linalg.norm(center_vector - node_vector)
                distances.append(distance)

                self.node[node][attribute].append(distance)

        min_dist = min(distances)
        stretch_denom = max(distances) - min_dist

        for node in self.__iter__():
            for ix, affinity in enumerate(self.node[node][attribute]):
                affinity -= min_dist
                affinity /= stretch_denom

                affinity *= stretch[1] - stretch[0]
                affinity += stretch[0]
                self.node[node][attribute][ix] = affinity


    def isolate(self, fs, attribute):
        ''' Transforms multifeature clusters to single feature clusters on the graph,
        and adds them to the layer list'''

        if not isinstance(fs, IPAG.feature_space):
            raise TypeError("To Isolate Feature the input must be IPAG.feature_space!")

    

        #center_vector = self.cluster_centers[attribute]['-'.join(fs.label)]
              
        layer_dict = {}

        processed = set() # Keep track which node has already been processed


        for node in fs.order:
            if node in processed:
                continue
            
            # Build up layer_dict
            current_layer_key = '-'.join(self.node[node][attribute])
            if  current_layer_key not in layer_dict:
                layer_dict[current_layer_key] = 0 # new IDs

            neighbour_list = [node]
            neighbour_set = set(neighbour_list)
            for neighbour in neighbour_list:
                equal_neighbours = self.get_equal_neighbors(neighbour, attribute)
                for en in equal_neighbours:
                    if en not in neighbour_set:
                        neighbour_list.append(en) #+= list(neighbour_set.difference(equal_neighbours))
                neighbour_set.update(neighbour_list)

                self.node[neighbour][attribute].append(str(layer_dict[current_layer_key]))

            layer_dict[current_layer_key] += 1 # Set id counter higher for next id


            processed.update(neighbour_list)
        
#        for isolated_label in layer_dict.keys():
#            
#            key = list(fs.label)
#            #key = list(isolated_label)
#            key.append(isolated_label)
#            
#            key_string = '-'.join(key)
#            print("Isolated Label: ", '-'.join(key))
#            
#            self.cluster_centers[attribute][key_string] = center_vector

        for base, new_patches in layer_dict.items():
             center_vector = self.cluster_centers[attribute][base]
             
             for patch in range(new_patches):
                
                key = base.split('-')
                key.append(str(patch))
                
                key_string = '-'.join(key)
             
                self.cluster_centers[attribute][key_string] = center_vector                 
                
        print(layer_dict)


    def get_equal_neighbors(self, node, attribute):
        '''Helper function for IPAG.single_feature().'''
        # Do the same for all neighbors with the same previous cluster
        filter_n = lambda n: self.node[node][attribute] == self.node[n][attribute]

        return filter(filter_n, self.neighbors(node))



        #self.node[node][layer].append(str(clusters))


#    def isolate_helper(self, node, clusters, processed, layer):
#        '''Helper function for IPAG.single_feature().'''
#        # Node is processed and gets new cluster ID
#        processed.add(node)
#
#        # Do the same for all neighbors with the same previous cluster
#        for neighbour in self.neighbors(node):
#            if (self.node[node][layer] == self.node[neighbour][layer]) and neighbour not in processed:
#                self.isolate_helper(neighbour, clusters, processed, layer)
#
#        self.node[node][layer].append(str(clusters))


    def remove_top_layer(self, fs, attribute, layers):
        if not isinstance(fs, IPAG.feature_space):
            raise TypeError("To the latest layer the input must be IPAG.feature_space!")

        for node in fs.order:
            del self.node[node][attribute][-layers:]


    def apply_group_metrics(self, fs, metric_config):
        '''IN DEVELOPMENT'''
        metric_dict = dict.fromkeys(metric_config)

        for name, metric in metric_config.items():
            metric_dict[name] = metric.func(self, fs, **metric.kwargs)

        return metric_dict




    def produce_label_dict(self, attribute, max_layer=None, sort=False, dtype=np.int64):
        '''Render an image (2D numpy array) of cluster labels based
        on a cluster label node attribute.'''

        if max_layer is not None:
            attr_labels = {'-'.join(self.node[node][attribute][:max_layer]) for node in self.__iter__()}
        else:
            attr_labels = {'-'.join(self.node[node][attribute]) for node in self.__iter__()}


        if sort:
            sort_attr_lables = list(sorted(attr_labels, key=len))
            label_dict = dict(zip(sort_attr_lables, range(len(attr_labels))))
        else:
            label_dict = dict(zip(attr_labels, range(len(attr_labels))))

        return label_dict




    def produce_cluster_image(self, attribute, max_layer=None, sort=False, dtype=np.int64):
        '''Render an image (2D numpy array) of cluster labels based
        on a cluster label node attribute.'''

        if max_layer is not None:
            attr_labels = {'-'.join(self.node[node][attribute][:max_layer]) for node in self.__iter__()}
        else:
            attr_labels = {'-'.join(self.node[node][attribute]) for node in self.__iter__()}


        if sort:
            sort_attr_lables = list(sorted(attr_labels, key=len))
            label_dict = dict(zip(sort_attr_lables, range(len(attr_labels))))
        else:
            label_dict = dict(zip(attr_labels, range(len(attr_labels))))

        print(label_dict)

        cluster_img = np.zeros_like(self.seg_img, dtype=dtype)

        for node in self.__iter__():
            for label in set(self.node[node]['labels']):
                attr_string = '-'.join(self.node[node][attribute][:max_layer])
                cluster_img[self.mask(node)] = label_dict[attr_string ]

        return cluster_img


    def neighbour_cross_tabulation(self, attribute):
        '''Tabulate the joint distribution of cluster labels
        for all adjacent nodes.'''

        count = Counter()
        for node1, node2, in self.edges():
            combo = tuple(sorted([self.node[node1][attribute], self.node[node2][attribute]]))
            count[combo] += 1
        return count


    @classmethod
    def old_init(cls, seg_img, tex_img, color_image, tex_bins, color_bins, **attr):
        '''Constructor of the first version of this class to ensure backwards compatibility.'''

        new_rag = cls(seg_img, **attr)

        new_rag.add_attribute('tex', tex_img, Hist, vbins=tex_bins)
        new_rag.normalize_attribute('tex')

        new_rag.add_attribute('color', color_image, Hist, bins=color_bins)
        new_rag.normalize_attribute('color')

        return new_rag







#Simple merging function
def _bow_merge_simple(graph, src, dst):
    '''Function to perform attribute transfer/recalculation
    of two nodes to be merged as part of a sequently merging
    algorithm.'''

    #pixel counter
    graph.node[dst]['pixel_count'] += graph.node[src]['pixel_count']

    #get color values for super pixel
    label_mask = (graph.seg_img == src) | (graph.seg_img == dst)

    for attr, fconfig in graph.attr_func_configs.items():

        masked_image = fconfig.img[label_mask]

        graph.node[dst][attr] = graph.calc_attr_value(data=masked_image,
                                                      func=fconfig.func, **fconfig.kwargs)

        #Normalize according to specs
        if attr in graph.attr_norm_val:
            graph.normalize_attribute(attr, graph.attr_norm_val[attr])
        #else: raise KeyError(f"Attribute '{attr}' has no stored normalization value")
