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
from pyglui.cygl.utils import draw_points_norm, RGBA
from pyglui import ui

#logging
import logging
logger = logging.getLogger(__name__)

import os

class Ximea_Capture(Plugin):
    """
    Ximea Capture captures frames from a Ximea camera
    during collection in parallel with world camera
    """
    icon_chr = chr(0xEC09)
    icon_font = "pupil_icons"

    def __init__(self, g_pool, record_ximea=True, serial_num='XECAS1930001', subject='TEST_SUBJECT', task='TEST_TASK'):
        super().__init__(g_pool)
        self.order = 0.8
        #self.pupil_display_list = []

        self.record_ximea = record_ximea
        self.serial_num = serial_num
        self.subject = subject
        self.task = task
        print(g_pool)

        self.currently_recording = False
        self.currently_saving = False
        self.blink_counter = 0

        self.START_RECORDING_MSG = 'Recording from Ximea Cameras...'
        self.STOP_RECORDING_MSG = 'Stopped Recording from Ximea Cameras. Cleaning Up and Saving...'
        self.DONE_SAVING_MSG = 'Finished Saving Ximea Frames...'

    def init_ui(self):
        self.add_menu()
        self.menu.label = "Ximea Cpature"

        def set_record(record_ximea):
            self.record_ximea = record_ximea
        def set_serial_num(new_serial_num):
            self.serial_num = new_serial_num
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

        help_str = "Ximea Capture Captures frames from Ximea Cameras in Parallel with Record."
        self.menu.append(ui.Info_Text(help_str))
        self.menu.append(ui.Switch("record_ximea",self, setter=set_record, label="Record From Ximea Cameras"))
        self.menu.append(ui.Text_Input("serial_num", self, setter=set_serial_num, label="Serial Number"))
        self.menu.append(ui.Text_Input("subject", self, setter=set_subject_id, label="Subject ID"))
        self.menu.append(ui.Text_Input("task", self, setter=set_task_name, label="Task Name"))

        set_save_dir()

    def gl_display(self):
        # blink?
        if(int(self.blink_counter / 10) % 2 == 1):
            if(self.currently_recording):
                draw_points_norm([(0.01,0.1)], size=35, color=RGBA(0.1, 1.0, 0.1, 0.8))
            if(self.currently_saving):
                draw_points_norm([(0.01,0.01)], size=35, color=RGBA(1.0, 0.1, 0.1, 0.8))
        self.blink_counter += 1

    def get_init_dict(self):
        return {}


    def start_recording(self):
        '''
        Begin Recording from Ximea Cameras.
        '''
        self.START_SAVING_MSG = f'Saving Ximea Frames at {self.save_dir}...'
        logger.info(self.START_SAVING_MSG)




    def on_char(self,char):
        '''
        When we hit record, also start recording from ximea cameras
        '''
        if(char=='r'):

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
