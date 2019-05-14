from Tkinter import *
from tkFont import Font, nametofont
from PIL import ImageTk, Image
from winsound import Beep
import threading,time,math
import Queue

import sys
sys.path.insert(0,"../lib")
import Leap
from Leap import SwipeGesture

global POINTS, SWIPE, IMG
POINTS = Queue.Queue()
SWIPE = False

class LeapEventListener(Leap.Listener):
    global POINTS, SWIPE
    finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    bone_names = ['Metacarpal', 'Proximal', 'Intermediate', 'Distal']
    state_names = ['STATE_INVALID', 'STATE_START', 'STATE_UPDATE', 'STATE_END']

    def on_init(self, controller):
        print "Initialized"

    def on_connect(self, controller):
        print "Connected"
        controller.enable_gesture(Leap.Gesture.TYPE_SWIPE);

    def on_disconnect(self, controller):
        # Note: not dispatched when running in a debugger.
        print "Disconnected"

    def on_exit(self, controller):
        print "Exited"

    def on_frame(self, controller):
        # Get the most recent frame and report some basic information
        frame = controller.frame()

        # print "Frame id: %d, timestamp: %d, hands: %d, fingers: %d, tools: %d, gestures: %d" % (
        #       frame.id, frame.timestamp, len(frame.hands), len(frame.fingers), len(frame.tools), len(frame.gestures()))

        # Get hands
        for hand in frame.hands:
            if hand.is_right:
                handType = "Right hand"
                # print "  %s, id %d, position: %s" % (
                #     handType, hand.id, hand.palm_position)
                POINTS.put(hand.palm_position)
                # print hand.palm_velocity

            # Get the hand's normal vector and direction
            # normal = hand.palm_normal
            # direction = hand.direction
            # Calculate the hand's pitch, roll, and yaw angles
            # print "  pitch: %f degrees, roll: %f degrees, yaw: %f degrees" % (
            #     direction.pitch * Leap.RAD_TO_DEG,
            #     normal.roll * Leap.RAD_TO_DEG,
            #     direction.yaw * Leap.RAD_TO_DEG)

        # Get gestures
        for gesture in frame.gestures():
            if gesture.type == Leap.Gesture.TYPE_SWIPE:
                swipe = SwipeGesture(gesture)
                state = self.state_names[gesture.state]
                if state == 'STATE_END':
                    # print "Swipe Gesture Complete"
                    SWIPE = True
                # print "  Swipe id: %d, state: %s, position: %s, direction: %s, speed: %f" % (
                #         gesture.id, self.state_names[gesture.state],
                #         swipe.position, swipe.direction, swipe.speed)

        if not (frame.hands.is_empty and frame.gestures().is_empty):
            return

    def state_string(self, state):
        if state == Leap.Gesture.STATE_START:
            return "STATE_START"

        if state == Leap.Gesture.STATE_UPDATE:
            return "STATE_UPDATE"

        if state == Leap.Gesture.STATE_STOP:
            return "STATE_STOP"

        if state == Leap.Gesture.STATE_INVALID:
            return "STATE_INVALID"

class Tutorial:
    global SWIPE
    def __init__(self,root):
        self.root = root
        self.pg_num = 1

        frame = Frame()
        frame.pack()
        self.page = Canvas(frame,width=1304,height=936)
        self.page.grid(row=0,column=0)
        self.pil_image = Image.open("../img/tutorial1.png")
        width,height = self.pil_image.size
        self.pil_image.resize((width,height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
        self.page.create_image(width/2,height/2,image=self.img,anchor="center")

        self.next_page = Button()

    def turn_page(self):
        self.pg_num+=1
        if self.pg_num == 4:
            return True

        file = "../img/tutorial"+str(self.pg_num)+".png"
        self.pil_image = Image.open(file)
        width,height = self.pil_image.size
        self.pil_image.resize((width,height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
        self.page.create_image(width/2,height/2,image=self.img,anchor="center")

class Multimodal_Metronome:
    DIRECTIONS = ["LEFT","RIGHT","UP","DOWN"]
    def __init__(self,root):
        self.root = root

        self.time_types = ["4/4","3/4","2/4"]
        self.references = {"":"../img/blank.png",0:"../img/blank.png",2:"../img/2-4.png",3:"../img/3-4.png",4:"../img/4-4.png"}
        self.met_bpm = 0
        self.met_timesig = ""
        self.met_delay = 0
        self.met_count = 0

        self.set_bpm = False
        self.set_time = False
        self.metronome = False
        self.conducting = False
        self.shutdown = False

        self.gui()
        self.metronome_thread = threading.Thread(target=self.metronome_handler)
        self.metronome_thread.start()
        self.dummy_timer = 0

    def gui(self):
        frame = Frame()
        frame.pack()
        fill = ("N", "S", "E", "W")
        default_font = nametofont("TkDefaultFont")
        default_font.configure(size=25)
        subtitle_font = Font(family=default_font,size=12)

        self.app_title = Label(frame,text="Multimodal Metronome")
        self.app_title.grid(row=0,column=0,columnspan=4,sticky=fill,padx=450)

        self.l_title = Label(frame,text="Metronome")
        self.l_title['bg']='red'
        self.l1_subtitle = Label(frame,text="BPM")
        self.l2_subtitle = Label(frame,text="Time")
        self.l1_display = Entry(frame)
        self.l1_display.insert(0,"100")
        self.l2_display = Spinbox(frame,values=self.time_types)

        self.l_title.grid(row=1,column=0,columnspan=2,sticky=fill,padx=50)
        self.l1_subtitle.grid(row=2,column=0,sticky=fill,padx=50)
        self.l2_subtitle.grid(row=3,column=0,sticky=fill,padx=50)
        self.l1_display.grid(row=2,column=1,padx=50)
        self.l2_display.grid(row=3,column=1,padx=50)

        self.l_start = Button(frame,text="Start",command=self.start_met,bg='papaya whip')
        self.l_stop = Button(frame,text="Stop",command=self.stop_met,bg='papaya whip')
        self.l_start.grid(row=4,column=0,sticky="E")
        self.l_stop.grid(row=4,column=1,sticky="W")
        self.l_start['font']=subtitle_font
        self.l_stop['font']=subtitle_font

        self.r_title = Label(frame,text="Conducting")
        self.r_title['bg']='red'
        self.r1_subtitle = Label(frame,text="BPM")
        self.r2_subtitle = Label(frame,text="Time")
        self.r1_display = Label(frame,text="      ")
        self.r2_display = Label(frame,text="      ")

        self.r_title.grid(row=1,column=2,columnspan=2,sticky=fill,padx=50)
        self.r1_subtitle.grid(row=2,column=2,sticky=fill,padx=50)
        self.r2_subtitle.grid(row=3,column=2,sticky=fill,padx=50)
        self.r1_display.grid(row=2,column=3,padx=50)
        self.r2_display.grid(row=3,column=3,padx=50)

        self.quit_button = Button(frame,text="QUIT",command=self.quit,bg='papaya whip')
        self.quit_button.grid(row=4, column = 3,sticky="W")
        self.quit_button['font']=subtitle_font

        self.met_reference = Canvas(frame,width=700,height=700,)
        self.met_reference.grid(row=5,column=0,columnspan=4,rowspan=10,sticky=fill,padx=300)
        self.pil_image = Image.open("../img/4-4.png")
        width,height = self.pil_image.size
        self.pil_image.resize((width,height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
        self.met_reference.create_image(width/2,height/2,image=self.img,anchor="center")

        self.trail_pts = []
        self.update_times = []
        self.cur_ind = 0
        for i in range(60):
            xo, yo = 350, 350
            new_pt = self.met_reference.create_oval(xo, yo, xo+10, yo+10, fill='yellow')
            self.trail_pts.append(new_pt)
            self.update_times.append(time.time())

    def update_trail(self,leap_data,cur_time):
        xo,yo = 350,700
        x,y = int(leap_data[0]*1.5), int(leap_data[1]*2)
        xf, yf = max(0,min(xo+x,700)), max(0,min((yo-y),700))
        cur_pt = self.trail_pts[self.cur_ind]
        self.met_reference.coords(cur_pt,(xf,yf,xf+10,yf+10))
        self.update_times[self.cur_ind]=cur_time
        self.cur_ind += 1
        self.cur_ind = self.cur_ind % len(self.trail_pts)
        self.dummy_timer += 1

    def tracking(self,leap_data):
        if not self.conducting:
            self.conducting = True
            self.r_title['bg'] = 'green'
        if self.dummy_timer > 300:
            self.r1_display['text']=104
        elif self.dummy_timer > 210:
            self.r1_display['text']=106
        elif self.dummy_timer > 120:
            self.r2_display['text']='4/4'
            self.r1_display['text']=98

    def quit(self):
        self.shutdown = True

    def start_met(self):
        if self.metronome:
            return #metronome is already on
        try:
            self.met_bpm = float(self.l1_display.get())
            self.met_timesig = int(self.l2_display.get()[0])
        except ValueError:
            #voice feedback?
            return
        self.metronome = True
        self.l_title['bg'] = 'green' 

    def stop_met(self):
        if not self.metronome:
            return #metronome is already off
        self.metronome = False
        self.met_count = 0
        self.l_title['bg'] = 'red'

    def metronome_handler(self):
        while not self.shutdown:
            if self.metronome:
                self.met_delay = 60.0 / self.met_bpm
                self.met_count += 1

                if self.met_count == 1: #down beat
                    Beep(880,300)#TODO: modify duration of beeps
                else:                   
                    Beep(440,300)

                if self.met_count >=self.met_timesig:
                    self.met_count = 0

                time.sleep(self.met_delay-0.3)

if __name__ == '__main__':
    global SWIPE,POINTS
    root = Tk()
    root.configure(background='white')

    listener = LeapEventListener()
    controller = Leap.Controller()
    controller.add_listener(listener)

    # tutorial = Tutorial(root)
    # while(tutorial.pg_num < 4):
    #     root.update()
    # tutorial.page.close()

    app = Multimodal_Metronome(root)
    prev_timesig = ""
    prev_trail_update = time.time()
    empty_count = 0
    while(1):
        if app.shutdown:
            break
        app.met_timesig = int(app.l2_display.get()[0])
        if app.met_timesig != prev_timesig:
            app.pil_image = Image.open(app.references[app.met_timesig])
            width,height = app.pil_image.size
            app.pil_image.resize((5*width,5*height),Image.ANTIALIAS)
            app.img = ImageTk.PhotoImage(app.pil_image,master=root)
            app.met_reference.create_image(width/2,height/2,image=app.img,anchor="center")
            prev_timesig = app.met_timesig
            app.trail_pts=[]
            app.update_times=[]
            app.cur_ind=0
            for i in range(60):
                xo, yo = 350, 350
                new_pt = app.met_reference.create_oval(xo, yo, xo+10, yo+10, fill='yellow')
                app.trail_pts.append(new_pt)
                app.update_times.append(time.time())
        if POINTS.empty():
            if empty_count > 1500:
                app.conducting = False
                app.r_title['bg'] = 'red'
                app.r1_display['text']='      '
                app.r2_display['text']='      '
            empty_count +=1
        while not POINTS.empty():
            empty_count = 0
            data = POINTS.get()
            app.tracking(data)
            cur_time = time.time()
            if abs(cur_time - prev_trail_update) > 0.015:
                app.update_trail(data,cur_time)
                prev_trail_update = cur_time
        try:
            root.update()
        except:
            break
    controller.remove_listener(listener)
    root.destroy()
    