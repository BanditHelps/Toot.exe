import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QAction, QVBoxLayout, QMainWindow
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class FloatingVideoPlayer(QWidget):
    def __init__(self, video_names, main_window):
        super().__init__()
        self.video_path = video_names[0]['path']
        self.video_names = video_names
        self.main_window = main_window
        self.initUI()
        self.initVideo()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout()
        self.label = QLabel(self)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        self.setGeometry(100, 100, 300, 300)  # Initial size, will be adjusted

    def initVideo(self, update=False):
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video file {self.video_path}")
            self.close()
            exit()

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if not update:
            self.setGeometry(100, 100, self.frame_width, self.frame_height)
        else:
            self.resize(self.frame_width, self.frame_height)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateFrame)
        self.timer.start(33)  # Approximately 30 fps

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

        for video_name in self.video_names:
                    action = QAction(video_name['name'], self)
                    action.triggered.connect(lambda _, path=video_name['path']: self.changeVideo(path))
                    submenu.addAction(action)

        spawnAction = QAction('Spawn New', self)
        spawnAction.triggered.connect(self.main_window.spawnNewCharacter)
        menu.addAction(spawnAction)

        exitAction = QAction('Exit', self)
        exitAction.triggered.connect(QApplication.instance().quit)
        menu.addAction(exitAction)

        menu.exec_(pos)

    def closeEvent(self, event):
        self.main_window.removeCharacter(self)
        event.accept()

    def changeVideo(self, video_path):
        self.cap.release()
        self.video_path = video_path
        self.timer.stop()
        self.initVideo(update=True)


class MainWindow(QMainWindow):
    def __init__(self, video_names):
        super().__init__()
        self.video_names = video_names
        self.characters = []
        self.spawnNewCharacter()

    def spawnNewCharacter(self):
        character = FloatingVideoPlayer(self.video_names, self)
        character.show()
        self.characters.append(character)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    video_names = [
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

    player = FloatingVideoPlayer(video_names)
    player.show()
    sys.exit(app.exec_())