from pynput import keyboard
recording=0
def on_press(key):
    global recording
    if key.char=='a':
        recording=1
        print(f"You pressed 'a'!,recording={recording}")

def on_release(key):
    global recording
    if key.char=='a':
        recording=0
        print(f"You released 'a'!,recording={recording}")

if __name__=="__main__":
    listener=keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    listener.join()
    