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

global POINTS, SWIPE, CYCLE, BEAT_NUM, TIME_SIG,BPM
POINTS = Queue.Queue()
SWIPE = False
CYCLE = False
NEXT_BEAT_NUM = 1
TIME_SIG = 4
BPM = 0

class LeapEventListener(Leap.Listener):
    global POINTS, SWIPE
    finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    bone_names = ['Metacarpal', 'Proximal', 'Intermediate', 'Distal']
    state_names = ['STATE_INVALID', 'STATE_START', 'STATE_UPDATE', 'STATE_END']

    def on_init(self, controller):
        self.prev_position = None
        self.prev_velocity = None
        self.prev_time = 0
        self.prev_beat_times = []
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

                dim = 0 #x - horizontal motion
                if (NEXT_BEAT_NUM%TIME_SIG==1 or NEXT_BEAT_NUM%TIME_SIG==0):
                    dim = 1 #y - first and last beats are vertical motions

                #velocity sign change in direction corresponding to current beat
                if (vel[dim]/self.prev_velocity[dim]<=0): 
                    print(pos,vel)
                    #distance threshold for beat recognition
                    if (abs(pos[dim]-self.prev_position[dim])>50):
                        is_beat = True
                        NEXT_BEAT_NUM = (NEXT_BEAT_NUM + 1) % 4
                        self.prev_beat_times.append(timestamp)

                        #calculate bpm based on time signature and beat times
                        beat_refs = 4
                        if len(self.prev_beat_times) > beat_refs:
                            time_refs = self.prev_beat_times[-beat_refs:]
                            temp = 0 #total beats/sec
                            for i in range(beat_refs-1):
                                #(1 beat / x usec) * (10^6 us / 1 s) = 10^6/x beats/sec
                                temp += 10^6/(time_refs[i]-time_refs[i+1])   
                            BPM = (temp*60)//(beat_refs-1)

            
                POINTS.put(pos + [timestamp, is_beat])
                self.prev_position = pos
                self.prev_velocity = vel
                self.prev_time = timestamp

        for gesture in frame.gestures():
            state = self.state_string(gesture.state)
            command = gesture.type
            if command == Leap.Gesture.TYPE_SWIPE:
                swipe = SwipeGesture(gesture)
                if state == 'STATE_END':
                    SWIPE = True
            if command == Leap.Gesture.TYPE_CIRCLE:
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
        self.met_count = 1

        self.metronome = False
        self.conducting = False
        self.tutorial = False
        self.shutdown = False
        self.showtime = False

        self.log = ""

        self.gui()
        self.sound_thread = threading.Thread(target=self.sound_handler)
        self.sound_thread.start()

    def gui(self):
        frame = Frame()
        frame.pack()
        fill = ("N", "S", "E", "W")
        default_font = nametofont("TkDefaultFont")
        default_font.configure(size=20)
        subtitle_font = Font(family=default_font,size=18)

        self.app_title = Label(frame,text="Multimodal Metronome",bg='pale goldenrod')
        self.app_title.grid(row=0,column=0,columnspan=2,rowspan=2,sticky=fill)

        self.message = Label(frame, text="Welcome, friend!",)
        self.message.grid(row=0,column=2,columnspan=6,sticky=fill)

        self.quit_button = Button(frame,text="QUIT",command=self.quit,bg='goldenrod')
        self.quit_button.grid(row=0, column = 8,sticky=fill)
        self.quit_button['font']=subtitle_font

        self.l_title = Label(frame,text="Metronome")
        self.l_title['bg']='gray'
        self.l1_subtitle = Label(frame,text="BPM",padx=60)
        self.l2_subtitle = Label(frame,text="Time")
        self.l1_display = Entry(frame,font=default_font,width=11)
        self.l1_display.insert(0," ")
        self.l2_display = Spinbox(frame,values=self.time_types,font=default_font,width=10)

        self.l_title.grid(row=2,column=0,columnspan=2,sticky=fill)
        self.l1_subtitle.grid(row=3,column=0,sticky=fill)
        self.l2_subtitle.grid(row=4,column=0,sticky=fill)
        self.l1_display.grid(row=3,column=1)
        self.l2_display.grid(row=4,column=1)

        self.start = Button(frame,text="Start",command=self.start_met,bg='goldenrod')
        self.stop = Button(frame,text="Stop",command=self.stop_met,bg='goldenrod')
        self.start.grid(row=5,column=0,sticky=fill)
        self.stop.grid(row=5,column=1,sticky=fill)
        self.start['font']=subtitle_font
        self.stop['font']=subtitle_font

        self.r_title = Label(frame,text="Conducting")
        self.r_title['bg']='gray'
        self.r1_subtitle = Label(frame,text="BPM")
        self.r2_subtitle = Label(frame,text="Time")
        self.r1_display = Label(frame,text="      ")
        self.r2_display = Label(frame,text="      ")

        self.r_title.grid(row=6,column=0,columnspan=2,sticky=fill)
        self.r1_subtitle.grid(row=7,column=0,sticky=fill)
        self.r2_subtitle.grid(row=8,column=0,sticky=fill)
        self.r1_display.grid(row=7,column=1)
        self.r2_display.grid(row=8,column=1,)

        self.start = Button(frame,text="Showtime!",command=self.toggle_challenge,bg='gold')
        self.start.grid(row=9,column=0,columnspan=2,sticky=fill)

        self.met_reference = Canvas(frame,width=700,height=700)
        self.met_reference.grid(row=1,column=2,columnspan=7,rowspan=9,sticky=fill)
        self.update_time_sig()

    def quit(self):
        self.shutdown = True

    def toggle_challenge(self):
        self.showtime = not self.showtime

    def set_met_tempo(self,tempo):
        self.met_bpm = tempo

    def start_met(self):
        if not self.met_bpm or self.met_bpm <= 0:
            self.log = "Input a valid BPM"
            return
        elif self.metronome:
            self.log = "Metronome is on"
            return #metronome is already on
        else:
            self.metronome = True
            self.l_title['bg'] = 'green' 
            self.log = "Starting metronome"

    def stop_met(self):
        if not self.metronome:
            return #metronome is already off
        self.metronome = False
        self.met_count = 0
        self.l_title['bg'] = 'gray'
        self.log = "Stopping metronome"

    def sound_handler(self):
        while not self.shutdown:
            if self.metronome:
                delay = 60.0 / self.met_bpm
                s_beep_dur = max(0.3, delay * 0.25)
                # print(delay,s_beep_dur)
                ms_beep_dur = s_beep_dur * 1000
                if self.met_count == 1: #down beat
                    Beep(1000, int(ms_beep_dur))#TODO: modify duration of beeps
                else:                   
                    Beep(700, int(ms_beep_dur))

                # print(self.met_count,TIME_SIG)
                if self.met_count >= TIME_SIG:
                    self.met_count = 1
                else:
                    self.met_count += 1
                time.sleep(delay - s_beep_dur)
            if self.showtime:
                continue #play music

    def check_time_sig_select(self):
        try:
            return int(self.l2_display.get()[0])
        except:
            self.log = "Input a valid time signature"
            return None

    def check_tempo_select(self):
        try:
            return float(self.l1_display.get())
        except:
            self.log = "Input a valid BPM"
            return None

    def update_message(self):
        self.message['text'] = self.log

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
        x,y,z,timestamp,is_beat = leap_data
        xo,yo = 350,700
        x,y = int(x*1.5), int(y*2) #adjust for dimensions of screen
        xf, yf = max(0,min(xo+x,700)), max(0,min((yo-y),700))
        cur_pt = self.trail_pts[self.cur_ind]
        self.met_reference.coords(cur_pt,(xf,yf,xf+10,yf+10))
        self.update_times[self.cur_ind]=cur_time
        self.cur_ind = (self.cur_ind+1) % len(self.trail_pts)

    def reset_conducting(self):
        self.conducting = False
        self.r_title['bg']='gray'
        self.r1_display['text']='      '
        self.r2_display['text']='      '
        self.log = "No motion input detected"

    def tracking(self,leap_data):
        #leap_data = [x, y, z, timestamp, is_beat]
        x,y,z,timestamp,is_beat = leap_data
        if is_beat:
            self.met_count
        return 0

# class Tutorial:
#     global SWIPE
#     def __init__(self,root):
#         self.root = root
#         self.pg_num = 1

#         frame = Frame()
#         frame.pack()
#         self.page = Canvas(frame,width=1304,height=936)
#         self.page.grid(row=0,column=0)
#         self.pil_image = Image.open("../img/tutorial1.png")
#         width,height = self.pil_image.size
#         self.pil_image.resize((width,height),Image.ANTIALIAS)
#         self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
#         self.page.create_image(width/2,height/2,image=self.img,anchor="center")

#         self.next_page = Button()

#     def turn_page(self):
#         self.pg_num+=1
#         if self.pg_num == 4:
#             return True

#         file = "../img/tutorial"+str(self.pg_num)+".png"
#         self.pil_image = Image.open(file)
#         width,height = self.pil_image.size
#         self.pil_image.resize((width,height),Image.ANTIALIAS)
#         self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
#         self.page.create_image(width/2,height/2,image=self.img,anchor="center")

if __name__ == '__main__':
    root = Tk()
    root.wm_title("Multimodal Metronome")
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
    prev_message = ""
    while(1): #tkinter updates
        # check for quit button 
        if app.shutdown:
            break

        #check for announcements
        if app.log != prev_message:
            app.update_message()

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
            if app.conducting and empty_count > 1500:
                app.reset_conducting()
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
    