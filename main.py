#---------------------------------------------------------------------------------------------#
# Initial Setup
from tkinter import *
import tkinter as tk
import matplotlib

master = Tk() 

master.title("E2 GUI Maker V2")

def log(text):
    file.write(text)

file = open("Hud.txt","w+")
log("@name Hud \n" )
log("@inputs E:wirelink\n")
log("@persist X Y ScreenRes:vector2\n")
log("if(first()){\n")
log("    #-------------------------#\n")
log("    E:egpClear()\n")
log("    ScreenRes = egpScrSize(owner())\n")
log("    X = ScreenRes:x()\n")
log("    Y = ScreenRes:y()\n")
log("    Res=ScreenRes/2\n")
log("    print('Your Resolution Is: '+ScreenRes:toString())\n")
log("    #-------------------------#\n")
log("}\n")
file.close()
#---------------------------------------------------------------------------------------------#
# Global Variables
Clicks = 0
relx = 0
rely = 0
lx = 0
ly = 0
wi = 495
hi = 450
var = StringVar()
var2 = StringVar()
var3 = StringVar()
collis = Listbox(master,relief = RAISED, height=5)
typelbl = Listbox(master,relief = RAISED,height = 5)
snapslider = Scale(master)
A=0
B=0
C=0
snapamnt = 10

color = StringVar()
type = StringVar()
#---------------------------------------------------------------------------------------------#
# Functions
def gridobj(obj,coln,rown,cex,rex):
    obj.grid(column = coln, row = rown, columnspan = cex, rowspan = rex)

def snap(num,amn):
    return round((num/snapamnt),0)*amn

def exit():
    master.quit()

def callback(event):
    global Clicks, lx, ly, relx, rely
    Clicks+=1
    relx = (wi/2-event.x)*-1
    rely = hi/2-event.y
    lx = event.x
    ly = event.y
    print("Mouse Clicked at X={0}, Y={1}".format(relx,rely))
    print("Point Snapped to X={0}. Y={1}".format(snap(relx,snapamnt),snap(rely,snapamnt)))

def showcolchoice():
    global collis, A, var, color
    if(A==0):
        A = 1
        collis = Listbox(master,relief = RAISED,height = 5)
        collis.insert(1, "Black")
        collis.insert(2, "Red")
        collis.insert(3, "Blue")
        collis.insert(4, "Green")
        collis.insert(5, "Yellow")
        collis.insert(6, "Brown")
        collis.insert(7,"Orange")
        collis.insert(8,"Purple")
        for i in range(8):
            collis.itemconfig(i,fg = collis.get(i))
        gridobj(collis,8,0,1,2)
    else:
        var.set("Color: "+collis.get(ACTIVE))
        color = collis.get(ACTIVE)
        collbl.config(fg = color)
        collis.destroy()
        A=0

def showtypechoice():
    global typelbl, B, var
    if(B==0):
        B = 1
        typelbl = Listbox(master,relief = RAISED,height = 5)
        typelbl.insert(1, "Rectangle")
        typelbl.insert(2, "Oval")
        typelbl.insert(3, "Circle")
        typelbl.insert(4, "Line")

        gridobj(typelbl,8,2,1,1)
    else:
        var2.set("Type: " + typelbl.get(ACTIVE))
        type = typelbl.get(ACTIVE)
        typelbl.destroy()
        B=0

def showsnapslider():
    global snapslider, C, snapamnt
    if(C==0):
        C = 1
        var3str = var3.get()
        snapslider = Scale(master,from_ = 0, relief = RAISED, to = 50)
        if var3str != "Snap: 10":
            sp = var3str.split(" ")
            snapslider.set(int(sp[1]))
        gridobj(snapslider,8,3,1,1)
    else:
        ge = snapslider.get()
        var3.set("Snap: " + str(snapslider.get()))
        snapamnt = snapslider.get()
        snapslider.destroy()
        C=0

#---------------------------------------------------------------------------------------------#
# Widgets
can = Canvas(master, width=wi, height=hi)

quitb = Button(master,command = exit,text = "Quit",activebackground = "red",bd = 1)

collbl = Button(master, textvariable=var,relief=RAISED, command = showcolchoice)
collbl.config(font=("Courier", 24))
var.set("Color:")

typelbl = Button(master, textvariable=var2,relief=RAISED, command = showtypechoice)
typelbl.config(font=("Courier", 24))
var2.set("Type:")

snaplbl = Button(master, textvariable=var3,relief=RAISED, command = showsnapslider)
snaplbl.config(font=("Courier", 24))
var3.set("Snap: 10")

can.bind("<Button-1>", callback)
#---------------------------------------------------------------------------------------------#
# Geometry stuff
can.create_rectangle(-wi, -hi, wi, hi)
can.create_line(-wi,hi/2,wi,hi/2, dash=(8, 24))
can.create_line(wi/2,-hi,wi/2,hi, dash=(8, 24))

#---------------------------------------------------------------------------------------------#
# Gridding everything
gridobj(can,1,1,6,6)
gridobj(quitb,7,7,1,1)
gridobj(collbl,7,1,1,1)
gridobj(typelbl,7,2,1,1)
gridobj(snaplbl,7,3,1,1)

#---------------------------------------------------------------------------------------------#
# Finishing it all
master.mainloop()
#---------------------------------------------------------------------------------------------#

