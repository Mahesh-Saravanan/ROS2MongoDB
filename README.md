# ROS2MongoDB

## Overview

The ROS2MongoDB package is designed for recording sensors and actuators data generated during scientific experiments with robots. It stores this data in a structured manner within a database, facilitating further analysis for research purposes.

## Dependencies

This package is compatible with MongoDB and HDF5 file formats for storing low and high-dimensional data, respectively. To use this package, you'll need the following Python libraries:
- [Pymongo](https://pypi.org/project/pymongo/): For MongoDB communication.
- [h5py](https://pypi.org/project/h5py/): For working with HDF5 files.

## Usage

The ROS2MongoDB package is used to log data from ROS topics published by sensors and actuators on a robot during its operation or experiments. It stores this data in a NoSQL database (MongoDB) and high-dimensional data (e.g., images) in hierarchical structured files (HDF5). Users can customize several functionalities based on their specific use case, including data compression and specifying the data of interest.

### Configuration

Users must configure required parameters in the `datalogger` class in`datalogger.py`:
1. **MongoDB IP**: The IP address of the MongoDB server for the Python client. Variable: `mongodb_ip`.
2. **Path to Store HDF5 File**: The local path where HDF5 files should be stored. Variable: `path_to_hdf5_file`.
3. **Topics**: A list of topics to which the package should listen and record data (comma-separated). Variable: `Topics`.
4. **Name of the Experiment**: A name describing the experiment or type of experiment. Variable: `name_of_experiment`.
5. **Frequency (Optional)**: The frequency or time window at which data should be recorded (default: 10 nanoseconds). Variable: `ws`.

## Database Information

This package is designed to work with MongoDB version 7.0.1. You can find installation instructions for MongoDB [here](https://www.mongodb.com/try/download/community). Each significant experiment is stored as a database, and each trial is stored as a collection. Local paths for high-dimensional data (HDF5 database name) and global paths (path to HDF5 files) are stored as separate features. Data from different sources is synchronized with a common reference time (time of generation). The latest data generated within the specified time window (default: 10 nanoseconds) is recorded, while the rest is ignored.

## HDF5 Structure

HDF5 stores high-dimensional data in either compressed or non-compressed formats. Users can configure the different compression and pre processing technique tailored to their use case at `heavy_data_call_back()` method in `datalogger.py` .A new file is created for each type of experiment. Data from different trials of the same experiment is stored in different Level 1 groups, and different sensors/topics are distinguished by distinct Level 2 sub-groups.

## Maintainer Information

- Author: Mahesh Saravanan
- Maintainer: Mahesh Saravanan
- Email: maheshhss750@gmail.com
- Source: [GitHub Repository](https://github.com/Mahesh-Saravanan/ROS2_MongoDB_hdf5.git)

