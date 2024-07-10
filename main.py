import sys
import cv2
import numpy as np
import random
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QAction, QVBoxLayout, QMainWindow
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QDesktopWidget

class FloatingVideoPlayer(QWidget):
    def __init__(self, character_defs, init_char_def, main_window):
        super().__init__()
        self.anim_path = init_char_def['path']
        self.character_defs = character_defs
        self.main_window = main_window
        self.initUI()
        self.initCharacterAnim()
        self.ensureOnScreen()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout()
        self.label = QLabel(self)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        self.setGeometry(100, 100, 300, 300)  # Initial size, will be adjusted

    def initCharacterAnim(self, update=False):
        self.cap = cv2.VideoCapture(self.anim_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video file {self.anim_path}")
            self.close()
            exit()

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if not update:
            screen_geometry = self.main_window.getScreenGeometry()
            self.setGeometry(int(screen_geometry.width() / 2), int(screen_geometry.height() / 2), self.frame_width, self.frame_height)
        else:
            self.resize(self.frame_width, self.frame_height)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateFrame)
        self.timer.start(33)  # Approximately 30 fps

    def ensureOnScreen(self):
        screen_geometry = self.main_window.getScreenGeometry()
        if not screen_geometry.contains(self.geometry()):
            # If the widget is out of screen bounds, move it to a valid position
            new_x = max(screen_geometry.x(), min(screen_geometry.x() + screen_geometry.width() - self.width(), self.x()))
            new_y = max(screen_geometry.y(), min(screen_geometry.y() + screen_geometry.height() - self.height(), self.y()))
            self.move(new_x, new_y)

    def updateFrame(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert frame to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Define color tolerance
            tolerance = 20  # Adjust this value to be more or less strict
            
            # Define the background color
            bg_color = np.array([140, 140, 140])
            
            # Create a mask for the background color
            lower_bound = np.clip(bg_color - tolerance, 0, 255)
            upper_bound = np.clip(bg_color + tolerance, 0, 255)
            mask = cv2.inRange(frame, lower_bound, upper_bound)
            
            # Invert the mask
            mask = 255 - mask
            
            # Apply Gaussian blur to soften the edges
            mask = cv2.GaussianBlur(mask, (5, 5), 0)
            
            # Normalize the mask
            mask = mask.astype(float) / 255.0
            
            # Create an alpha channel
            alpha = mask * 255
            
            # Blend the edges
            for c in range(3):
                frame[:,:,c] = frame[:,:,c] * mask + 255 * (1 - mask)

            # Add the alpha channel to the frame
            frame = np.dstack((frame, alpha.astype(np.uint8)))
            
            image = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image)
            self.label.setPixmap(pixmap)
            self.adjustSize()  # Adjust window size to content
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def showContextMenu(self, pos):
        menu = QMenu(self)
        submenu = menu.addMenu('Toot')

        for cur_def in self.character_defs:
                    action = QAction(cur_def['name'], self)
                    action.triggered.connect(lambda _, path=cur_def['path']: self.changeAnim(path))
                    submenu.addAction(action)

        # Spawn a new character
        spawnAction = QAction('Spawn New', self)
        spawnAction.triggered.connect(self.main_window.spawnNewCharacter)
        menu.addAction(spawnAction)

        # Start a rave with all the characters
        raveAction = QAction('Rave', self)
        raveAction.triggered.connect(self.main_window.startRave)
        menu.addAction(raveAction)

        # Remove the current character
        removeAction = QAction('Remove', self)
        removeAction.triggered.connect(self.close)
        menu.addAction(removeAction)

        # Exit the application
        exitAction = QAction('Exit', self)
        exitAction.triggered.connect(QApplication.instance().quit)
        menu.addAction(exitAction)

        menu.exec_(pos)

    def closeEvent(self, event):
        self.main_window.removeCharacter(self)
        event.accept()

    def changeAnim(self, anim_path):
        self.cap.release()
        self.anim_path = anim_path
        self.timer.stop()
        self.initCharacterAnim(update=True)


class MainWindow(QMainWindow):
    def __init__(self, character_defs):
        super().__init__()
        self.character_defs = character_defs
        self.characters = []
        self.spawnNewCharacter()

    def spawnNewCharacter(self, random_position=False):
        character = FloatingVideoPlayer(self.character_defs, self.character_defs[0], self)
        if random_position:
            self.positionCharacterRandomly(character)

        character.show()
        self.characters.append(character)

    def positionCharacterRandomly(self, character):
        screen_geometry = self.getScreenGeometry()
        max_x = screen_geometry.width() - character.width()
        max_y = screen_geometry.height() - character.height()
        random_x = random.randint(0, max_x)
        random_y = random.randint(0, max_y)
        character.move(screen_geometry.x() + random_x, screen_geometry.y() + random_y)

    def removeCharacter(self, character):
        self.characters.remove(character)
        if not self.characters:
            QApplication.instance().quit()

    def startRave(self):
        for char_def in self.character_defs:
            character = FloatingVideoPlayer(self.character_defs, char_def, self)
            self.positionCharacterRandomly(character)
            character.show()
            self.characters.append(character)

    def getScreenGeometry(self):
        desktop = QDesktopWidget()
        screen_number = desktop.screenNumber(self)
        return desktop.screenGeometry(screen_number)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    character_defs = [
        {'name': 'Normal',   'path': 'videos/normal_toot.mp4' },
        {'name': 'Shorty',   'path': 'videos/short_toot.mp4'  },
        {'name': 'Tall-Boi', 'path': 'videos/tall_toot.mp4'   },
        {'name': 'Tail',     'path': 'videos/tail_toot.mp4'   },
        {'name': 'Party',    'path': 'videos/party_toot.mp4'  },
        {'name': 'Angry',    'path': 'videos/angry_toot.mp4'  },
        {'name': 'Wings',    'path': 'videos/wing_toot.mp4'   },
        {'name': 'Music',    'path': 'videos/music_toot.mp4'  },
        {'name': 'Light',    'path': 'videos/light_toot.mp4'  }
    ]

    main_window = MainWindow(character_defs)
    sys.exit(app.exec_())