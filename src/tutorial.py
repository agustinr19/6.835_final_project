from Tkinter import *
from tkFont import Font, nametofont
from PIL import ImageTk, Image

global SWIPE
SWIPE=False
class Tutorial:
    def __init__(self,root):
        self.root = root
        self.pg_num = 1

        frame = Frame()
        frame.pack()
        self.page = Canvas(frame,width=1304,height=936)
        self.page.grid(row=0,column=0)
        self.pil_image = Image.open("tutorial1.png")
        width,height = self.pil_image.size
        self.pil_image.resize((width,height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
        self.page.create_image(width/2,height/2,image=self.img,anchor="center")

    def turn_page(self):
        self.pg_num+=1
        if self.pg_num == 4:
            return True

        file = "tutorial"+str(self.pg_num)+".png"
        self.pil_image = Image.open(file)
        width,height = self.pil_image.size
        self.pil_image.resize((width,height),Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.pil_image,master=self.root)  
        self.page.create_image(width/2,height/2,image=self.img,anchor="center")

if __name__ == '__main__':
    root = Tk()
    root.configure(background='white')

    tutorial = Tutorial(root)
    while(tutorial.pg_num < 4):
        if SWIPE:
            SWIPE = False
            done = app.tutorial.turn_page()
            if done:
                break
        root.update()
    tutorial.page.close()
