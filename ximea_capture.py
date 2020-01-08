"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2019 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""

from plugin import Plugin
from pyglui.cygl.utils import draw_points_norm, RGBA, draw_gl_texture
from pyglui import ui
import gl_utils
import numpy as np

from video_overlay.plugins.generic_overlay import Video_Overlay


import ximea_utils

#logging
import logging
logger = logging.getLogger(__name__)

import os

class Ximea_Capture(Plugin):
    """
    Ximea Capture captures frames from a Ximea camera
    during collection in parallel with world camera
    """
    #icon_chr = chr(0xEC09)
    #icon_font = "pupil_icons"
    icon_font = "roboto"
    icon_chr = "X"

    def __init__(self, g_pool,
    record_ximea=False, preview_ximea=True,
    serial_num='XECAS1930001', subject='TEST_SUBJECT', task='TEST_TASK',
     yaml_loc='/home/vasha/cy.yaml', imshape=(2064,1544)):
        super().__init__(g_pool)
        self.order = 0.8
        #self.pupil_display_list = []

        self.record_ximea = record_ximea
        self.preview_ximea = preview_ximea
        self.serial_num = serial_num
        self.yaml_loc = yaml_loc
        self.subject = subject
        self.task = task
        self.imshape = imshape

        self.camera = None
        self.image_handle = None
        self.camera_open = False
        self.currently_recording = False
        self.currently_saving = False
        self.blink_counter = 0

        self.START_RECORDING_MSG = 'Recording from Ximea Cameras...'
        self.STOP_RECORDING_MSG = 'Stopped Recording from Ximea Cameras. Cleaning Up and Saving...'
        self.DONE_SAVING_MSG = 'Finished Saving Ximea Frames...'

        self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)


    def init_ui(self):
        self.add_menu()
        self.menu.label = "Ximea Cpature"

        def set_record(record_ximea):
            self.record_ximea = record_ximea
        def set_preview(preview_ximea):
            self.preview_ximea = preview_ximea
        def set_serial_num(new_serial_num):
            self.serial_num = new_serial_num
            if not self.camera == None:
                self.camera.close_device()
            self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
        def set_save_dir():
            self.save_dir = os.path.join(f'/home/vasha/ximea_recordings/{self.subject}/{self.task}/')
            #self.menu.append(ui.Info_Text(f'Save Dir: {self.save_dir}'))
            logger.info(f'Save Dir set to: {self.save_dir}')
        def set_subject_id(new_subject):
            self.subject = new_subject
            set_save_dir()
        def set_task_name(new_task_name):
            self.task = new_task_name
            set_save_dir()

        def set_yaml_loc(new_yaml_loc):
            self.yaml_loc = new_yaml_loc
            if not self.camera == None:
                self.camera.close_device()
            self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)

        help_str = "Ximea Capture Captures frames from Ximea Cameras in Parallel with Record."
        self.menu.append(ui.Info_Text(help_str))
        self.menu.append(ui.Text_Input("serial_num", self, setter=set_serial_num, label="Serial Number"))
        self.menu.append(ui.Switch("preview_ximea",self, setter=set_preview, label="Preview Ximea Cameras"))
        self.menu.append(ui.Text_Input("yaml_loc", self, setter=set_yaml_loc, label="Cam Settings Location"))
        self.menu.append(ui.Text_Input("subject", self, setter=set_subject_id, label="Subject ID"))
        self.menu.append(ui.Text_Input("task", self, setter=set_task_name, label="Task Name"))
        self.menu.append(ui.Switch("record_ximea",self, setter=set_record, label="Record From Ximea Cameras"))

        set_save_dir()

    def gl_display(self):
        # blink?
        if(int(self.blink_counter / 10) % 2 == 1):
            if(self.currently_recording):
                draw_points_norm([(0.01,0.1)], size=35, color=RGBA(0.1, 1.0, 0.1, 0.8))
            if(self.currently_saving):
                draw_points_norm([(0.01,0.01)], size=35, color=RGBA(1.0, 0.1, 0.1, 0.8))
        self.blink_counter += 1

        if(self.preview_ximea):
            if(self.currently_saving):
                #if we are currently saving, don't grab images
                im = np.ones((*self.imshape,3)).astype(np.uint8)
                alp=0.5
            elif(not self.camera_open):
                logger.info(f'Camera Open: {self.camera_open}')
                im = np.zeros((*self.imshape,3)).astype(np.uint8)
                alp = 0.5
            else:
                im = ximea_utils.decode_ximea_frame(self.camera, self.image_handle, self.imshape, logger)
                alp=1
            gl_utils.make_coord_system_norm_based()
            draw_gl_texture(im, interpolation=True, alpha=alp)

    def get_init_dict(self):
        return {}



    def start_recording(self):
        '''
        Begin Recording from Ximea Cameras.
        '''

        self.START_SAVING_MSG = f'Saving Ximea Frames at {self.save_dir}...'
        logger.info(self.START_SAVING_MSG)

        ximea_utils.ximea_acquire([self.save_dir],
                                    settings_file = self.yaml_loc,
                                    logger = logger,
                                    ims_per_file = 100,
                                    num_cameras = 1)
        self.currently_recording = False
        self.currently_saving = False


    def on_char(self,char):
        '''
        When we hit record, also start recording from ximea cameras
        '''
        if(char=='r'):
            if(self.record_ximea):
                if(self.currently_recording):
                    logger.info(self.STOP_RECORDING_MSG)
                    self.currently_recording = False
                    #self.menu.append(ui.Info_Text(self.STOP_RECORDING_MSG))

                elif(self.currently_saving and not self.currently_recording):
                    logger.info('Can\'t Start Recording Again until saving finished!')

                else:
                    logger.info(self.START_RECORDING_MSG)
                    #self.menu.append(ui.Info_Text(self.START_RECORDING_MSG))
                    self.currently_recording = True
                    self.currently_saving = True
                    self.start_recording()

        return(False)

    def deinit_ui(self):
        self.remove_menu()


    def cleanup(self):
        """
        gets called when the plugin get terminated.
        This happens either voluntarily or forced.
        if you have an gui or glfw window destroy it here.
        """
        if not self.camera == None:
            self.camera.close_device()
