
#! /usr/bin/env python3
import os
import rclpy
from rclpy.node import Node
import cv2
from cv_bridge import CvBridge
import h5py
import pymongo
import numpy as np
from rosidl_runtime_py import message_to_ordereddict
import importlib
import warnings



class datalogger:
    def __init__ (self, topics =[],mongodb_ip = 'mongodb://localhost:27017/', path_to_hdf5_file = "/", hdf5_file_name = 'data',Mo_Database_name = "Robot_Experiment", Mo_collection_name= "data_",buffer = 100,ws = 10):
        #Initiating RCL node
        #super().__init__('data_logger')
        self.node = rclpy.create_node('subscriber_node')
        self.buffer = buffer
        #Set time window size ws in nano seconds (10**-9 seconds)
        self.window_size = ws 
        # Get the ROS clock
        self.get_clock = self.node.get_clock()
        self.init_time = str(self.get_clock.now().nanoseconds)
        # Exit if topic list is empty
        if len(topics) == 0: raise ValueError("The topic list is Empty ")
        else:self.all_topic = topics
        
        # Defining Heavy data
        # Heavy data: The Actual data is store in a Hdf5 file and the hdf5 path is stored in the database, 
        self.Heavy_data_list = ["Image"]
        
        #Interpret topics
        self.topic_info_dict = self.interpret_topic(topics)
        
        #check for any heavy data in the topics to create Hdf5 file
        self.have_heavy_data = any(item["Heavy_data"] for item in self.topic_info_dict.values())
        
        
        if self.have_heavy_data:
            #create a sub dict only with Heavy data topics
            self.heavydata_topic_info = dict()
            for id in self.topic_info_dict.keys():
                entry = self.topic_info_dict[id]
                if entry["Heavy_data"]:
                    self.heavydata_topic_info.update({entry['Topic_id']: entry })
            
            #Creating a Hdf5 file to store heavy data
            self.path_to_hdf5_file = os.path.join(path_to_hdf5_file, hdf5_file_name+".h5")
            self.hdf5_file = h5py.File(self.path_to_hdf5_file, 'a')
            self.exp_group = self.hdf5_file.create_group(f"EXP_{self.init_time}")
            #print(f"Creating new group at {self.init_time}")
            #creating the Group for each Topic in Hdf5 file and updating the 'heavydata_topic_info' dictionary with group instance
            for entry in self.heavydata_topic_info: self.heavydata_topic_info[entry]["hdf5_group"] = self.exp_group.create_group(str(self.heavydata_topic_info[entry]["Topic"]).replace("/", "_"))
            
            
            
        #DB init
        self.client = pymongo.MongoClient(mongodb_ip)
        self.db = self.client[Mo_Database_name]
        self.collection = self.db[Mo_collection_name+self.init_time]
        
        self.create_subscriber()

    def interpret_topic(self,topics):
        """TODO: read all the topics fill the dictionary with
        1. Topic_id
        2. Topic
        3. Datatype
        4. Heavy_data
        5. Subscriber_object
        6. Datatype_str
        Topic_id is the key for each data
        """
        topic_info_dict = dict()
        # Fetch all publishing topics
        all_topics = self.node.get_topic_names_and_types()
        id_ = 1 #counter
        for topic, data_type in all_topics:
            #Checking for input topic
            if topic in topics:
                for data_type_as_str in data_type:
                    try:
                        # Import its message type
                        
                        # split module and class name
                        data_type_module, data_type_class = data_type_as_str.split("/msg/")
                        # generate messaage for importlib
                        message_type = f"{data_type_module}.msg"
                        module = importlib.import_module(message_type)
                        #fetch class from imported package "module"
                        message_class = getattr(module, data_type_class)
                        # update dictionary
                        topic_info_dict.update(
                                {id_:{"Topic_id": id_,
                                "Topic" : topic,
                                "Datatype": message_class,
                                "Heavy_data": False,
                                "Datatype_str":data_type_class,}}
                                )
                        # Check if data type is in heavy data list
                        if data_type_class in self.Heavy_data_list : topic_info_dict[id_]["Heavy_data"] = True
                        id_+=1
                    
                    
                    except Exception as e:
                        print(f"Error in Importing library for data type {data_type_as_str} from topic {topic}: {e}")
            else:
                pass #warnings.warn(f"Could not find the publisher for topic: {topic}")

        return topic_info_dict
        
    def create_subscriber(self):
        """TODO: Create Subscribers for all Topics in loop and update topic_info_dict with subcriber object"""
        for id in self.topic_info_dict.keys():
            entry = self.topic_info_dict[id]
            # if Heavy_data : heavy_data_call_back()
            if entry['Heavy_data']:entry['Subscriber_object'] = self.node.create_subscription(entry['Datatype'],entry['Topic'],lambda msg, id=entry['Topic_id']: self.heavy_data_call_back(id, msg),self.buffer)
            #if Light data: light_data_call_back()
            elif not entry['Heavy_data']:entry['Subscriber_object'] = self.node.create_subscription(entry['Datatype'],entry['Topic'],lambda msg, id=entry['Topic_id']: self.light_data_call_back(id, msg),self.buffer)
            #Raise Error if Nature of data is empty
            else: raise RuntimeError(f"Subscriber for Topic : {entry['Topic']} cannot be created")
    def heavy_data_call_back(self, subscriber_id,msg):
        """
        TODO: 
        1. Process the preprocess data (multiple if statements for each expexted data type)
        2. Store the data in Hdf5 file
        3. Check for existing event id and create new if not exist else update in Database
        4. Store the HDF5 path in MongoDB
        5. Print Status
        """
        #Fetch Topicname
        topic_name = self.topic_info_dict[int(subscriber_id)]["Topic"]
        datatype_ = self.topic_info_dict[int(subscriber_id)]["Datatype_str"]
        #read current time and it is used as Unique Event identifier
        time_i = int(self.get_clock.now().nanoseconds/(self.window_size*1e9))
        #________________________________________Define Compression steps for each heavy data____________________________________________________________________________________________________________
        if datatype_ == "Image":
            try:
                cv_bridge = CvBridge()
                cv_image = cv_bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            except Exception as e:
                self.node.get_logger().error(f"Skipped image due to conversion problem")
                return
            _, data_ = cv2.imencode('.png', cv_image)
        elif datatype_ == "Datatype_X":pass
        elif datatype_ == "Datatype_Y":pass
        else: raise RuntimeError(f"Unknown Data type encountered at Heavy data call back. Compression method for {datatype_} is not defined")
        #____________________________________________________________________________________________________________________________________________________
        # Storing in Hdf5 file
        # Fetching the entry number i.e., Timestep
        num_entry = len((self.heavydata_topic_info[int(subscriber_id)]["hdf5_group"]).keys())
        # Creating Dataset(image) name
        ds_name = f"{time_i}"
        # Creating dataset in Respective Hdf5 group at storing data
        # Deleting if an data at given time step (time_i) exist
        try: del self.heavydata_topic_info[int(subscriber_id)]["hdf5_group"][ds_name]
        except:pass
        dataset = self.heavydata_topic_info[int(subscriber_id)]["hdf5_group"].create_dataset(ds_name, shape = data_.shape,chunks = True,data = data_)
        
        #____________________________________________________________________________________________________________________________________________________
        # Storing Hdf5 path in Data base
        #Checking for existing event id created by other data source and update if available
        result = self.collection.update_one({'event_id': time_i},{"$set":{f'{topic_name}_data_path': dataset.name }})
        # Create new Event if event id not exist
        if result.matched_count == 0:
            pass
            self.collection.insert_one({'event_id': time_i,f'{topic_name}_data_path': dataset.name })
            self.collection.update_one({"event_id": time_i},{"$set":{'hdf5_pth': self.path_to_hdf5_file }})
            
        #print status
        self.node.get_logger().info(f"{time_i}: Received {self.topic_info_dict[subscriber_id]['Datatype_str']} Data from Subscriber {subscriber_id} ")
        
    def light_data_call_back(self, subscriber_id,msg):
        """
        TODO: 
        1. Check for existing event id and create new if not exist else update in Database
        2. Store the Data as a dictionary in DB
        3. Print Status
        """
        #reading current time and it is used as the unique event identifier
        time_i = int(self.get_clock.now().nanoseconds/(self.window_size*1e9))
        #Fetch Topic Name
        topic_name = self.topic_info_dict[int(subscriber_id)]["Topic"]
        # Fetching the entry number i.e., Timestep
        num_ent = len(self.collection.distinct(topic_name))
        
        
        #____________________________________________________________________________________________________________________________________________________
        #Checking for existing event id created by other data source and update if available
        result = self.collection.update_one({'event_id': time_i},{"$set":{f'{topic_name}': message_to_ordereddict (msg) }})
        # Create new Event if event id not exist
        if result.matched_count == 0:
            pass
            self.collection.insert_one({'event_id': time_i,f'{topic_name}': message_to_ordereddict (msg) })
            self.collection.update_one({"event_id": time_i},{"$set":{'hdf5_pth': self.path_to_hdf5_file }})
        #Print status
        self.node.get_logger().info(f"{time_i}: Received {self.topic_info_dict[subscriber_id]['Datatype_str']} Data from Subscriber {subscriber_id}")  





def main(args = None):
    rclpy.init()
    topics = ["/cam0/image_raw","/cam1/image_raw", "/leica/position", "/imu0"] 
    mongodb_ip = 'mongodb://172.21.208.1:27017/'
    path_to_hdf5_file = '/mnt/d/Germany/CERI/Prof. Meißner Robot/Retrived/Test/'
    name_of_experiment = "pick_and_place"
    ws = 1
    logger = datalogger(topics,mongodb_ip,path_to_hdf5_file,Mo_Database_name = name_of_experiment,hdf5_file_name = name_of_experiment,ws =ws )
    
    try:
        rclpy.spin(logger.node)
    except KeyboardInterrupt:
        #print(logger.init_time)
        logger.node.destroy_node()    
        logger.hdf5_file.close()
        logger.client.close()


if __name__ == '__main__':
        main()
