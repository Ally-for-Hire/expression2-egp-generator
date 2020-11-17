#---------------------------------------------------------------------------------------------#
# Initial Setup
from tkinter import *
import tkinter as tk
from matplotlib import colors
import numpy as np

master = Tk() 

master.title("E2 GUI Maker V2")

def log(text):
    file.write(text)

file = open("Hud.txt","w+")
log("@name Made Using Ally's Hud Maker \n" )
log("@inputs E:wirelink\n")
log("@persist X Y ScreenRes:vector2\n")
log("if(first()){\n")
log("    #-------------------------#\n")
log("    E:egpClear()\n")
log("    ScreenRes = egpScrSize(owner())\n")
log("    X = ScreenRes:x()\n")
log("    Y = ScreenRes:y()\n")
log("    Res=ScreenRes/2\n")
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
wi = 495*2
hi = 450*2
var = StringVar()
var2 = StringVar()
var3 = StringVar()
collis = Listbox(master,relief = RAISED, height=5)
typelbl = Listbox(master,relief = RAISED,height = 5)
snapslider = Scale(master)
A=0
B=0
C=0
Point = 0,0
Points = []
AllPoints = []
snapamnt = 10
GList = []
color = "Black"
type = "Line"
var5 = StringVar()
valuelist = []
for i in range(105):
    if i % 5 == 0:
        valuelist.append(i)
#---------------------------------------------------------------------------------------------#
# Functions
def gridobj(obj,coln,rown,cex,rex):
    obj.grid(column = coln, row = rown, columnspan = cex, rowspan = rex)

def snap(num,amn):
    return round((num/snapamnt),0)*amn

def exit():
    master.quit()

def callback(event):
    global Clicks, lx, ly, relx, rely, Point, Points, color, type, var2, AllPoints
    Clicks+=1
    relx = (wi/2-event.x)*-1
    rely = hi/2-event.y
    def torelx(x):
        return ((wi/2-x)*-1)*2
    def torely(y):
        return (hi/2-y)*2
    
    lx = event.x
    ly = event.y
    Point = snap(lx,snapamnt)-5,snap(ly,snapamnt)
    Points.append(Point)
    type = var2.get().split(" ",1)[1]
    if type == "Line":
        if len(Points)==1:
            print("Point 1 Placed")
        elif len(Points)==2:
            print("Point 2 Placed")
            AllPoints.append(can.create_line(Points[0],Points[1],fill=color))
            file = open("Hud.txt","a")
            Ox = torelx(Points[0][0])
            Oy = torely(Points[0][1])
            Ax = torelx(Points[1][0])
            Ay = torely(Points[1][1])
            C = colors.to_rgba(color)[0]*255,colors.to_rgba(color)[1]*255,colors.to_rgba(color)[2]*255
            file.write("E:egpLine({0},Res+vec2({1},{2}),Res+vec2({3},{4}))\n".format(len(AllPoints),Ox,Oy,Ax,Ay))
            file.write("    E:egpColor({0},vec{1})\n".format(len(AllPoints),C))
            file.close()
            Points = []
    if type == "Rectangle":
        if len(Points)==1:
            print("Point 1 Placed")
        elif len(Points)==2:
            print("Point 2 Placed")
            AllPoints.append(can.create_rectangle(Points[0],Points[1],outline=color))
            file = open("Hud.txt","a")
            Rw = Points[0][0]-Points[1][0]
            Rh = Points[0][1]-Points[1][1]
            Originx = Points[0][0]-Rw/2 
            Originy = Points[0][1]-Rh/2
            Ox = torelx(Originx)
            Oy = torely(Originy)
            Ax = Rw
            Ay = Rh
            C = colors.to_rgba(color)[0]*255,colors.to_rgba(color)[1]*255,colors.to_rgba(color)[2]*255
            file.write("E:egpBoxOutline({0},Res+vec2({1},{2}),vec2({3},{4}))\n".format(len(AllPoints),Ox,Oy,abs(Ax),abs(Ay)))
            file.write("    E:egpColor({0},vec{1})\n".format(len(AllPoints),C))
            file.close()
            Points = []
    if type == "Box":
        if len(Points)==1:
            print("Point 1 Placed")
        elif len(Points)==2:
            print("Point 2 Placed")
            AllPoints.append(can.create_rectangle(Points[0],Points[1],fill=color))
            file = open("Hud.txt","a")
            Rw = Points[0][0]-Points[1][0]
            Rh = Points[0][1]-Points[1][1]
            Originx = Points[0][0]-Rw/2 
            Originy = Points[0][1]-Rh/2
            Ox = torelx(Originx)
            Oy = torely(Originy)
            Ax = Rw
            Ay = Rh
            C = colors.to_rgba(color)[0]*255,colors.to_rgba(color)[1]*255,colors.to_rgba(color)[2]*255
            file.write("E:egpBox({0},Res+vec2({1},{2}),vec2({3},{4}))\n".format(len(AllPoints),Ox,Oy,abs(Ax),abs(Ay)))
            file.write("    E:egpColor({0},vec{1})\n".format(len(AllPoints),C))
            file.close()
            Points = []
    if type == "Circle":
        if len(Points)==1:
            print("Point 1 Placed")
        elif len(Points)==2:
            print("Point 2 Placed")
            L = Points[0][0]-Points[0][0]/2
            I = Points[0][1]+Points[0][1]/2
            Pp = L,I
            AllPoints.append(can.create_oval(Points[0],Points[1],fill=color))
            file = open("Hud.txt","a")
            Ox = torelx(Points[0][0])
            Oy = torely(Points[0][1])
            Ax = torelx(Points[1][0])
            Ay = torely(Points[1][1])
            C = colors.to_rgba(color)[0]*255,colors.to_rgba(color)[1]*255,colors.to_rgba(color)[2]*255
            file.write("E:egpCircle({0},Res+vec2({1},{2}),Res+vec2({3},{4}))\n".format(len(AllPoints),Ox,Oy,Ax,Ay))
            file.write("    E:egpColor({0},vec{1})\n".format(len(AllPoints),C))
            file.close()
            Points = []



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
        collis.insert(9,"Gold")
        collis.insert(10,"Lightgrey")
        collis.insert(11,"Pink")
        for i in range(11):
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
        typelbl.insert(2,"Box")
        typelbl.insert(3, "Circle")
        typelbl.insert(4, "Line")

        gridobj(typelbl,8,2,1,1)
    else:
        var2.set("Type: " + typelbl.get(ACTIVE))
        type = typelbl.get(ACTIVE)
        typelbl.destroy()
        B=0

def valuecheck(value):
    global valuelist
    newvalue = min(valuelist, key=lambda x:abs(x-float(value)))
    snapslider.set(newvalue)

def showsnapslider():
    global snapslider, C, snapamnt, GList, wi, hi, AllPoints
    if(C==0):
        C = 1
        var3str = var3.get()
        snapslider = Scale(master,from_ = 10, relief = RAISED, to = 50, command = valuecheck)
        if var3str != "Snap: 10":
            sp = var3str.split(" ")
            snapslider.set(int(sp[1]))
        gridobj(snapslider,8,3,1,1)
    else:
        ge = snapslider.get()
        for l in range(len(GList)):
            can.delete(GList[0])
            GList.pop(0)
        hig = int(hi/ge)
        wig = int(wi/ge)
        for i in range(wig):
            GList.append(can.create_rectangle(i*ge-5,0,i*ge-5,wi,fill = "lightgrey",outline="lightgrey"))
        for i in range(hig):
            GList.append(can.create_rectangle(0,i*ge,wi,i*ge,fill = "lightgrey",outline="lightgrey"))
        can.create_rectangle(-wi, -hi, wi, hi)
        can.create_line(-wi,hi/2,wi,hi/2, dash=(8, 24), fill = "grey")
        can.create_line(wi/2,-hi,wi/2,hi, dash=(8, 24), fill = "grey")
        for i in range(len(AllPoints)):
            can.tag_raise(AllPoints[i-1])
        var3.set("Snap: " + str(ge))
        snapamnt = ge
        snapslider.destroy()
        C=0

def undolast():
    global AllPoints, can
    p = len(AllPoints)-1
    print("Undone "+str(AllPoints[p]))
    a_file = open("Hud.txt", "r")
    list_of_lines = a_file.readlines()
    print(len(AllPoints))
    list_of_lines[10+len(AllPoints)*2] = ""
    list_of_lines[11+len(AllPoints)*2] = ""
    a_file = open("Hud.txt", "w")
    a_file.writelines(list_of_lines)
    a_file.close()
    can.delete(AllPoints[p])
    AllPoints.pop(p)


#---------------------------------------------------------------------------------------------#
# Widgets
can = Canvas(master, width=wi, height=hi)

quitb = Button(master,command = exit,text = "Quit",activebackground = "red",bd = 1)

collbl = Button(master, textvariable=var,relief=RAISED, command = showcolchoice)
collbl.config(font=("Courier", 24))
var.set("Color: Black")

typelbl = Button(master, textvariable=var2,relief=RAISED, command = showtypechoice)
typelbl.config(font=("Courier", 24))
var2.set("Type: Line")

snaplbl = Button(master, textvariable=var3,relief=RAISED, command = showsnapslider)
snaplbl.config(font=("Courier", 24))
var3.set("Snap: 10")

back = Button(master, textvariable=var5,relief=RAISED, command = undolast)
back.config(font=("Courier", 24))
var5.set("Undo")

can.bind("<Button-1>", callback)

#---------------------------------------------------------------------------------------------#
# Geometry stuff
ge = 10
hig = int(hi/ge)
wig = int(wi/ge)
for i in range(wig):
    GList.append(can.create_rectangle(i*ge-5,0,i*ge-5,wi,fill = "lightgrey",outline="lightgrey"))
for i in range(hig):
    GList.append(can.create_rectangle(0,i*ge,wi,i*ge,fill = "lightgrey",outline="lightgrey"))
can.create_rectangle(-wi, -hi, wi, hi)
can.create_line(-wi,hi/2,wi,hi/2, dash=(8, 24), fill = "grey")
can.create_line(wi/2,-hi,wi/2,hi, dash=(8, 24), fill = "grey")
#---------------------------------------------------------------------------------------------#
# Gridding everything
gridobj(can,1,1,6,6)
gridobj(quitb,7,7,1,1)
gridobj(collbl,7,1,1,1)
gridobj(typelbl,7,2,1,1)
gridobj(snaplbl,7,3,1,1)
gridobj(back,7,4,1,1)
#---------------------------------------------------------------------------------------------#
# Finishing it all
master.mainloop()
#---------------------------------------------------------------------------------------------#
