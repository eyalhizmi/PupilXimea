import copy
import threading
import queue as queue
import time
import os as os
import numpy as np
from ximea import xiapi
from collections import namedtuple
import yaml
import mmap
import copy
import sys
import gc
import signal
import gc
import ctypes
import stat
import cv2
import struct
import base64

frame_data = namedtuple("frame_data", "raw_data nframe tsSec tsUSec")

def write_sync_queue(sync_queue, cam_name, save_folder):
    '''
    Get() everything from the sync string queue and write it to disk.
    Params:
        sync_queue (Multiprocessing Queue): Queue of sync strings to write to disk
        cam_name (str) name of camera - used for filename
        save_folder (str) directory to save sync string
    Returns:
        None
    '''
    sync_file_name = os.path.join(save_folder, f"timestamp_camsync_{cam_name}.tsv")
    with open(sync_file_name, 'w') as sync_file:
        sync_file.write(f"tcam_name\t_wall\t_cam\n")
    #open it for appending
    sync_file = open(sync_file_name, 'a+')
    while not sync_queue.empty():
        sync_string = sync_queue.get()
        sync_file.write(sync_string)
    return()

def get_sync_string(cam_name, cam_handle):
    '''
    Clock camera and wall clocks together to ensure they match
    Params:
        cam_name (str): String name of camera (ie cam_od/cam_os/cam_cy
        cam_handle (XimeaCamera instance): camera handle to query time
    Returns:
        sync_string (str): string to write to file with cam name, time, and wall time
    '''
    t_wall_1 = time.time()
    t_cam = cam_handle.get_param('timestamp')
    t_cam = t_cam/(1e9) #this is returned in nanoseconds, change to seconds
    t_wall_2 = time.time()
    t_wall = np.mean((t_wall_1, t_wall_2)) #take middle of two wall times
    sync_string = f'{cam_name}\t{t_wall}\t{t_cam}\n'
    return(sync_string)

def apply_cam_settings(cam, config_file):
    """
    Apply settings to the camera from a config file.

    Params:
        camera (XimeaCamera instance): camera handle
        config_file (str): string filename of the config file for the camera
    """
    with open(config_file, 'r') as f:
        cam_props = yaml.safe_load(f)

    for prop, value in cam_props.items():
        #print(prop, value)
        if f"set_{prop}" in dir(cam):
            try:
                cam.__getattribute__(f"set_{prop}")(value)
            except Exception as e:
                print(e)
        elif prop in dir(cam) and "is_" in prop:
            en_dis = "enable_" if value else "disable_"
            try:
                cam.__getattribute__(f"{en_dis}{prop.replace('is_', '')}")()
            except Exception as e:
                print(e)

        else:
            print(f"Camera doesn't have a set_{prop}")

def save_queue_worker(cam_name, save_queue_out, save_folder, ims_per_file, stop_collecting_event, logger):
    try:
        if not os.path.exists(os.path.join(save_folder, cam_name)):
            os.makedirs(os.path.join(save_folder, cam_name))
            #os.chmod(save_folder, stat.S_IRWXO)
        ts_file_name = os.path.join(save_folder, f"timestamps_{cam_name}.tsv")
        #make a new blank timestamp file
        with open(ts_file_name, 'w') as ts_file:
            ts_file.write(f"nframe\ttime\n")
        #open it for appending
        ts_file = open(ts_file_name, 'a+')
        i = 0
        logger.info('Started Saving...')
        if(ims_per_file == 1):
            while (not stop_collecting_event.is_set())  or save_queue_out.empty():
                bin_file_name = os.path.join(save_folder, cam_name, f'frame_{i}.bin')
                f = os.open(bin_file_name, os.O_WRONLY | os.O_CREAT , 0o777 | os.O_TRUNC | os.O_SYNC | os.O_DIRECT)
                image = save_queue_out.get()
                os.write(f, image.raw_data)
                ts_file.write(f"{i}\t{image.nframe}\t{image.tsSec}.{str(image.tsUSec).zfill(6)}\n")
                i+=1
        else:
            while (not stop_collecting_event.is_set())  or save_queue_out.empty():
                fstart=i*ims_per_file
                bin_file_name = os.path.join(save_folder, cam_name, f'frames_{fstart}_{fstart+ims_per_file-1}.bin')
                f = os.open(bin_file_name, os.O_WRONLY | os.O_CREAT , 0o777 | os.O_TRUNC | os.O_SYNC | os.O_DIRECT)
                for j in range(ims_per_file):
                    image = save_queue_out.get()
                    os.write(f, image.raw_data)
                    ts_file.write(f"{fstart+j}\t{image.nframe}\t{image.tsSec}.{str(image.tsUSec).zfill(6)}\n")
                os.close(f)
                i+=1

    except Exception as e:
        print(f'Exception!: e')
        print('Exiting Save Thread')


def init_camera(cam_id, settings_file, logger):
    '''
    Initialize a ximea camera for use (recoring and preview) by external scripts
    Params:
        cam_id (str): Serial number of camera to opening
        setttings_file (str): Path to settings file for camera
        logger (instace of class logger): used to pass messages to gui
    Returns:
        camera (instace of class Ximea Camera): A camera that produces Images
        iamge_handle (Ximea Camera image): handle to point to images from camera
        open_success (bool): Were we able to open the camera?
    '''
    try:
        logger.info(f'Opening Ximea Camera {cam_id}')
        camera = xiapi.Camera()
        camera.open_device_by_SN(cam_id)
        logger.info('Sucessfully Opened Camera')
        apply_cam_settings(camera, settings_file)
        logger.info('Sucessfully Applied Settings to Camera')
        camera.start_acquisition()
        image = xiapi.Image()
        logger.info('Sucessfully Started Aquisition')
        return(camera, image, True)
    except:
        logger.info('Problem initializing camera.')
        logger.info('Check .yaml file')
        camera.stop_acquisition()
        camera.close_device()
        return(None, None, False)


def decode_ximea_frame(camera, image_handle, imshape, logger, norm=True):
    '''
    Get a single frame from ximea cameras
    '''
    camera.get_image(image_handle)
    im = image_handle.get_image_data_raw()
    im = np.frombuffer(im,dtype='uint8') #.byteswap()
    im = im.reshape(imshape)
    im = cv2.cvtColor(im, cv2.COLOR_BayerRG2BGR)
    im = cv2.flip(im, -1)
    if(norm):
        im = cv2.normalize(im, None, 0, 255, cv2.NORM_MINMAX)
    return(im)

def aquire_camera_worker(camera, image_handle, cam_name, sync_queue, save_queue, stop_collecting_event, logger):

    """
    Acquire frames from a single camera. Can have mulitple instances of this to record from multiple cameras.

    Parameters:
        camera (Ximea Camera) Instance of a ximea camera
        image_handle (Ximea Image) Instance of Ximea camera image
        sync_queue (Mutlithreading.Queue): A queue to sync timestamps of camera and computer
        save_queue (Mutlithreading.Queue): A queue which accepts xiapi.Images
        stop_collecting (threading.Event): keep collecting until this is set

    """

    try:
        logger.info(f'Begin Recording..')

        while not stop_collecting_event.is_set():
            camera.get_image(image_handle)
            data = image_handle.get_image_data_raw()
            save_queue.put(frame_data(data,
                                   image_handle.nframe,
                                   image_handle.tsSec,
                                   image_handle.tsUSec))

        logger.info(f'Stopping Ximea Collection')
        sync_str = get_sync_string(cam_name + "_post", camera)
        sync_queue.put(sync_str)

    except Exception as e:
        logger.info(f'Detected Exception {e} Stopping Acquisition')
        sync_str = get_sync_string(cam_name + "_post", camera)
        sync_queue.put(sync_str)

    finally:
        logger.info(f"Camera aquisition finished")

def start_ximea_aquisition(camera, image_handle,
                            save_dir, ims_per_file,
                            stop_collecting_event,
                            logger):

    save_queue = queue.Queue()
    sync_queue = queue.Queue()

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    cam_name = 'ximea'
    save_proc = threading.Thread(target=save_queue_worker,
                            args=(cam_name, save_queue,
                                 save_dir, ims_per_file,
                                 stop_collecting_event,
                                 logger))

    acq_proc = threading.Thread(target=aquire_camera_worker,
                          args=(camera,
                                image_handle,
                                cam_name,
                                sync_queue,
                                save_queue,
                                stop_collecting_event,
                                logger))
    save_proc.daemon = True
    save_proc.start()
    acq_proc.daemon = False
    acq_proc.start()

    return(save_queue)

def notify_ximea_save_finished(save_queue, currently_saving, logger):
    '''
    Notify when save threads are done.
    '''
    logger.info(f" Waiting for Save Queues to Empty...")
    while not save_queue.empy():
        time.sleep(1)

    logger.info(f"Finished Saving")
    currently_saving = False

def end_ximea_aquisition(save_queue,
                         currently_saving,
                         logger):

    notify_proc = threading.Thread(target=notify_ximea_save_finished,
                          args=(save_queue, currently_saving,
                                logger))
    notify_proc.daemon = True
    notify_proc.start()

    save_queue.join()

    logger.info(f"Finished Aquiring...")

    # logger.info(f"Saving Timestamp Sync Information...")
    # for i, (cam_name, cam_sn) in enumerate(cameras.items()):
    #     write_sync_queue(sync_queues[i], cam_name, save_folders[i])
