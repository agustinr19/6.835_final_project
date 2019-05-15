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

global POINTS, SWIPE, CYCLE, BEAT_NUM, TIME_SIG
POINTS = Queue.Queue()
SWIPE = False
CYCLE = False
BEAT_NUM = 1
TIME_SIG = 4

class LeapEventListener(Leap.Listener):
    global POINTS, SWIPE
    finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    bone_names = ['Metacarpal', 'Proximal', 'Intermediate', 'Distal']
    state_names = ['STATE_INVALID', 'STATE_START', 'STATE_UPDATE', 'STATE_END']

    def on_init(self, controller):
        self.prev_position = None
        self.prev_velocity = None
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
        frame = controller.frame()
        timestamp = frame.timestamp
        for hand in frame.hands:
            if hand.is_right:
                pos = hand.palm_position
                vel = hand.palm_velocity
                is_beat = False
                if (BEAT_NUM%TIME_SIG==1 or BEAT_NUM%TIME_SIG==0):
                    if (vel[1]/self.prev_velocity[1]<=0): 
                        #abrupt stop/change in y direction -> recognize beat
                        is_beat = True
                else:
                    if (vel[0]/self.prev_velocity[2]<=0):
                        #abrupt stop/change in x direction -> recognize beat
                        is_beat = True
                POINTS.put(pos + [timestamp, is_beat])
                self.prev_position = pos
                self.prev_velocity = vel

        for gesture in frame.gestures():
            state = self.state_string(gesture.state)
            command = gesture.type
            if command == Leap.Gesture.TYPE_SWIPE:
                swipe = SwipeGesture(gesture)
                if state == 'STATE_END':
                    SWIPE = True
            elif command == Leap.Gesture.TYPE_CIRCLE:
                circle = CircleGesture(gesture)
                if state == 'STATE_END':
                    CYCLE = True

    def state_string(self, state):
        if state == Leap.Gesture.STATE_START:
            return "STATE_START"

        if state == Leap.Gesture.STATE_UPDATE:
            return "STATE_UPDATE"

        if state == Leap.Gesture.STATE_STOP:
            return "STATE_STOP"

        if state == Leap.Gesture.STATE_INVALID:
            return "STATE_INVALID"

        if state == Leap.Gesture.STATE_END:
            return "STATE_END"

class Multimodal_Metronome:
    global TIME_SIG
    DIRECTIONS = ["LEFT","RIGHT","UP","DOWN"]
    def __init__(self,root):
        self.root = root

        self.time_types = ["4/4","3/4","2/4"]
        self.references = {"":"../img/blank.png",0:"../img/blank.png",2:"../img/2-4.png", \
                            3:"../img/3-4.png",4:"../img/4-4.png"}
        self.met_bpm = 0
        self.met_delay = 0
        self.met_count = 0

        self.metronome = False
        self.conducting = False
        self.shutdown = False

        self.gui()
        self.metronome_thread = threading.Thread(target=self.metronome_handler)
        self.metronome_thread.start()

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

        self.met_reference = Canvas(frame,width=700,height=700)
        self.met_reference.grid(row=5,column=0,columnspan=4,rowspan=10,sticky=fill,padx=300)
        self.update_time_sig()

    def quit(self):
        self.shutdown = True

    def set_met_tempo(self,tempo):
        self.met_bpm = tempo

    def start_met(self):
        if self.metronome:
            return #metronome is already on
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

                if self.met_count >= TIME_SIG:
                    self.met_count = 0

                time.sleep(self.met_delay-0.3)

    def check_time_sig_select(self):
        try:
            return int(self.l2_display.get()[0])
        except:
            #voice feedback
            return None

    def check_tempo_select(self):
        try:
            return float(self.l1_display.get())
        except:
            # voice feedback
            return None

    def update_time_sig(self):
        self.pil_image = Image.open(self.references[TIME_SIG])
        width,height = self.pil_image.size
        self.pil_image.resize((5*width,5*height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=root)
        self.met_reference.create_image(width/2,height/2,image=self.img,anchor="center")

        self.trail_pts = []
        self.update_times = []
        self.cur_ind = 0
        for i in range(60):
            xo, yo = 350, 350
            new_pt = self.met_reference.create_oval(xo, yo, xo+10, yo+10, fill='yellow')
            self.trail_pts.append(new_pt)
            self.update_times.append(time.time())

    def update_trail(self,leap_data):
        #leap_data = [x, y, z, timestamp, is_beat]
        xo,yo = 350,700
        x,y = int(leap_data[0]*1.5), int(leap_data[1]*2)
        xf, yf = max(0,min(xo+x,700)), max(0,min((yo-y),700))
        cur_pt = self.trail_pts[self.cur_ind]
        self.met_reference.coords(cur_pt,(xf,yf,xf+10,yf+10))
        self.update_times[self.cur_ind]=cur_time
        self.cur_ind = (self.cur_ind+1) % len(self.trail_pts)

    def tracking(self,leap_data):
        #leap_data = [x, y, z, timestamp, is_beat]
        return 0

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

if __name__ == '__main__':
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
    prev_time_sig = 4
    prev_tempo = None
    prev_trail_update = time.time()
    empty_count = 0
    while(1): #tkinter updates
        # check for quit button 
        if app.shutdown:
            break

        # check for user inputs to gui
        time_sig_select = app.check_time_sig_select()
        if time_sig_select and time_sig_select != prev_time_sig:
            TIME_SIG = time_sig_select
            prev_time_sig = TIME_SIG
            app.update_time_sig()
        tempo_select = app.check_tempo_select()
        if tempo_select and tempo_select != prev_tempo:
            app.set_met_tempo(tempo_select)

        # if no motion inputs, stop conducting functions
        if POINTS.empty():
            if empty_count > 1500:
                app.conducting = False
                app.r_title['bg'] = 'red'
                app.r1_display['text']='      '
                app.r2_display['text']='      '
            empty_count +=1

        # if new motion info, update visuals
        while not POINTS.empty():
            empty_count = 0
            data = POINTS.get()
            app.tracking(data)
            cur_time = time.time()
            if abs(cur_time - prev_trail_update) > 0.015:
                app.update_trail(data)
                prev_trail_update = cur_time
        try:
            root.update()
        except:
            break

    controller.remove_listener(listener)
    root.destroy()
    