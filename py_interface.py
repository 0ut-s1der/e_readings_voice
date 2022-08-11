import PySimpleGUI as gui
import main

gui.theme("DarkAmber")
layout = [[],
    [gui.Button("Звонок",size=(20, 5),font="Calibri 20")],
          []]

window = gui.Window('Diplom', layout, margins=(100,100))
a=0
while True:                             # The Event Loop
    event, values = window.read()
    # print(event, values) #debug
    if event =="Звонок":
        main.start()
    elif event in(None,"Cancel"):
        break