import sys
from PyQt6.QtWidgets import QApplication
from gui.window import VoiceAgentWindow
from agent import Agent
from dotenv import load_dotenv

load_dotenv()


def main():
    app = QApplication(sys.argv)
    agent = Agent()
    window = VoiceAgentWindow(agent)
    window.show()
    agent.start(voice_name="kaltsit")
    ret = app.exec()
    agent.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()
