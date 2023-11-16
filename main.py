import pygame
from PyQt6.QtWidgets import QApplication, QPushButton, QCheckBox,  QMainWindow, QFileDialog, QMenu
from PyQt6 import uic
from PyQt6.QtGui import QCursor, QFont, QIcon
from pathlib import Path
import shutil
from pygame import mixer
import time
import threading
from tinytag import TinyTag
from PyQt6.QtCore import Qt
import random
from pytube import YouTube, Playlist
from pytube.exceptions import RegexMatchError
import urllib
from moviepy.editor import AudioFileClip
import sys
import os
import images

original_stdout = sys.stdout
original_stderr = sys.stderr

if sys.stdout is None or sys.stderr is None:
    output = open(os.devnull, "w")
    sys.stdout = output
    sys.stderr = output

executable_path = os.path.dirname(os.path.abspath(__file__))
ui_path1 = os.path.join(executable_path,"images")
ui_path = os.path.join(ui_path1, "arialoom.ui")
print(ui_path)


directory_path = Path.home() / "Arialoom"
directory_path.mkdir(parents=True, exist_ok=True)
directory_path_all = directory_path / "Music"
directory_path_all.mkdir(parents=True, exist_ok=True)


def turn_into_clock(length):
    if length < 3600:
        second = int(length % 60)
        minute = int(length / 60)
        if len(str(minute)) == 1:
            minute = f"0{minute}"
        if len(str(second)) == 1:
            second = f"0{second}"
        return f"{minute}:{second}"
    else:
        hour = int(length / 3600)
        second = int(length % 60)
        minute = int((length % 3600) / 60)
        if len(str(minute)) == 1:
            minute = f"0{minute}"
        if len(str(second)) == 1:
            second = f"0{second}"
        return f"{hour}:{minute}:{second}"


# noinspection PyUnresolvedReferences because uic.loadUi()
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.youtube_mp3_playlist_only = None  # Download playlist contents
        self.youtube_mp3_playlist_also = None  # Download playlist contents and make a playlist with them
        self.link = None
        self.old_name = None
        self.old_playlist_name = None
        self.paused = None
        self.mouse_start = None
        self.mouse_movement = None
        self.mouse_end = None
        self.youtube_mp3 = None
        self.realtime = None
        self.slider_thread = None
        self.slider_volume = None
        self.current_piece = None  # Path to the current mp3
        self.current_path = directory_path_all  # Path to the current directory
        self.current_path_for_mode = directory_path_all  # Path to the current directory(specialized for modes)

        self.exit_flag = False  # Exit flag for timer thread
        self.colour_flag = True
        self.playlist_switch_flag = True
        self.slider_timer = False  # Flag to manage the timer according to the slider
        self.volume_flag = False
        self.is_muted = False
        self.pressing = False
        self.mode_flag = 0  # Modes(nothing, repeat-one, repeat-all, random)

        self.unmuted_volume = 1
        self.remaining = 0
        self.total_length = 0
        self.current_value = 0

        self.true_false_dict = {}
        self.randomized_list = []

        uic.loadUi(f"{ui_path}", self)
        self.setWindowIcon(QIcon(":/images/Arialoom.ico"))
        self.setFixedSize(1120, 637)

        self.update_music_list()
        self.label.setWordWrap(True)

        self.musicSlide.hide()
        self.customSignal.hide()
        self.warningLabel.hide()
        self.renameBox.hide()
        self.renameBox_2.hide()
        self.linkFrame.hide()
        self.warningLabel_2.hide()
        self.customSignal_2.hide()
        self.downloadFeedback.hide()
        self.warningLabel_rename.hide()
        self.warningLabel_rename_2.hide()
        self.askPlaylist.hide()
        self.skip.hide()
        self.youTubePlaylist.hide()

        self.horizontalSlider.sliderPressed.connect(self.slider_hold)  # Horizontal Slider is the main music slider
        self.horizontalSlider.sliderReleased.connect(self.slider_release)
        self.muteToggle.clicked.connect(self.mute_unmute)
        self.volumeSlider.sliderPressed.connect(self.volume_slider_start)
        self.volumeSlider.sliderReleased.connect(self.volume_slider_set)
        self.modeChange.clicked.connect(self.mode_set)
        self.PlayPause.clicked.connect(self.pause_start)
        self.pushButton.clicked.connect(self.open_explorer)
        self.customSignal.textChanged.connect(self.mode_apply)
        self.viewAll.clicked.connect(self.view_all)
        self.youTubeDownload.clicked.connect(self.youtube_download_prepare)
        self.cancelButton_2.clicked.connect(self.youtube_download_cancel)
        self.cancelButton_3.clicked.connect(self.youtube_download_cancel_playlist)
        self.downloadButton.clicked.connect(self.youtube_download_preaction)
        self.onlyButton.clicked.connect(self.youtube_download_preaction_playlist_only)
        self.alsoButton.clicked.connect(self.youtube_download_preaction_playlist_also)
        self.customSignal_2.textChanged.connect(self.youtube_download_done)
        self.cancelButton_rename.clicked.connect(self.rename_cancel)
        self.applyButton_rename.clicked.connect(self.rename_apply)
        self.cancelButton_rename_2.clicked.connect(self.rename_playlist_cancel)
        self.applyButton_rename_2.clicked.connect(self.rename_playlist_apply)
        self.skip.clicked.connect(self.skip_do)
        self.closeButton.clicked.connect(self.close)
        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton.clicked.connect(self.maximize)
        self.addPlaylist.clicked.connect(self.make_playlist_prepare)
        self.cancelButton.clicked.connect(self.close_playlist_adding_box)
        self.createButton.clicked.connect(self.create_playlist)

        mixer.init()
        mixer.music.set_volume(1)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.update_playlist()

        self.PlayPause.setStyleSheet("border-image: url(:/images/pause.png);"
                                     "background-position:center;")
        self.muteToggle.setStyleSheet("border-image: url(:/images/unmuted.png)")
        self.modeChange.setStyleSheet("border-image: url(:/images/donothing.png)")
        self.minimizeButton.setStyleSheet(
            """
            QPushButton {
                border: none;
                background-image: url(:/images/minimize.png);
            }

            QPushButton:hover:!pressed {
                border: none;
                background-image: url(:/images/minimizeunder.png);
            }
            """
        )
        self.closeButton.setStyleSheet(
            """
            QPushButton {
                border: none;
                background-image: url(:/images/close.png);
            }

            QPushButton:hover:!pressed {
                border: none;
                background-image: url(:/images/closeunder.png);
            }
            """
        )
        self.maximizeButton.setStyleSheet(
            """
            QPushButton {
                border: none;
                background-image: url(:/images/maximize.png);
            }

            QPushButton:hover:!pressed {
                border: none;
                background-image: url(:/images/maximizeunder.png);
            }
            """
        )
        self.skip.setStyleSheet("border-image: url(:/images/skip.png)")

    def resizeEvent(self, a0):
        if self.isMaximized():
            height = self.size().height()
            width = self.size().width()
            self.CustomBar.resize(width,21)
            self.controlButtons.move(width-151,0)
            self.musicSlide.resize(width,81)
            self.musicSlide.move(0,height-81)
            self.modeChange.move(width-59,22)
            self.label.move(width-181,28)
            self.horizontalSlider.resize(width-340,22)
            self.muteToggle.move(width-261,51)
            self.volumeSlider.move(width-241,52)
            self.scrollArea.resize(width-321,899)
            self.Options.resize(321,height+10)
            self.askPlaylist.resize(321,height-331)
            self.scrollArea_2.resize(301,height-481)
            self.cancelButton.move(10,height-400)
            self.createButton.move(240,height-400)
            self.playlists.resize(321,height-331)
        else:
            self.CustomBar.resize(1131, 21)
            self.controlButtons.move(970, 0)
            self.musicSlide.resize(1151, 81)
            self.musicSlide.move(-10, 560)
            self.modeChange.move(1080, 20)
            self.label.move(950, 26)
            self.horizontalSlider.resize(801, 22)
            self.muteToggle.move(930, 50)
            self.volumeSlider.move(960, 50)
            self.scrollArea.resize(801, 501)
            self.Options.resize(321, 651)
            self.askPlaylist.resize(321, 301)
            self.scrollArea_2.resize(301, 191)
            self.cancelButton.move(10, 260)
            self.createButton.move(240, 260)
            self.playlists.resize(321, 311)

    def maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def skip_do(self):  # Skip button
        self.mode_apply()

    def rename_playlist_cancel(self):
        self.renameBox_2.hide()

    def rename_playlist_apply(self):
        new_name = self.newName_2.text()
        if new_name == "" or new_name.isspace():
            self.warningLabel_rename_2.show()
        else:
            self.renameBox_2.hide()
            new_path = directory_path / new_name
            try:
                shutil.move(self.old_playlist_name,new_path)
            except PermissionError:
                self.music_close()
                shutil.move(self.old_playlist_name, new_path)
        self.update_playlist()
        self.playlistName.setText(f"    new_name")

    def rename_apply(self):
        new_name = self.newName.text()
        if new_name == "" or new_name.isspace():
            self.warningLabel_rename.show()
        else:
            self.renameBox.hide()
            directories = directory_path.glob("*/")
            file_list = {}
            for directory in directories:
                piece = directory / self.old_name
                file_list[piece] = directory
            for file in file_list:
                try:
                    file.rename(file_list.get(file) / f"{new_name}.mp3")
                except FileNotFoundError:
                    pass
            self.update_music_list()

    def rename_cancel(self):
        self.renameBox.hide()

    def youtube_download_prepare(self):
        self.buttonFrame.hide()
        self.warningLabel_2.hide()
        self.youTubeLink.setText("")
        self.youTubeLink.setFocus()
        self.linkFrame.show()

    def youtube_download_cancel(self):
        self.buttonFrame.show()
        self.linkFrame.hide()

    def youtube_download_cancel_playlist(self):
        self.buttonFrame.show()
        self.linkFrame.hide()
        self.youTubePlaylist.hide()
        self.downloadFeedback.hide()
        self.cancelButton_2.show()
        self.downloadButton.show()

    def youtube_download_done(self):
        self.buttonFrame.show()
        self.linkFrame.hide()
        self.update_music_list()
        self.update_playlist()
        self.downloadFeedback.hide()
        self.cancelButton_2.show()
        self.downloadButton.show()

    def youtube_download_preaction(self):
        self.youtube_mp3 = threading.Thread(target=self.youtube_download_action, args=(), daemon=True)
        self.youtube_mp3.start()

    def youtube_download_preaction_playlist_only(self):
        self.youtube_mp3_playlist_only = threading.Thread(target=self.youtube_download_action_playlist_only, args=(),
                                                          daemon=True)
        self.youtube_mp3_playlist_only.start()

    def youtube_download_preaction_playlist_also(self):
        self.youtube_mp3_playlist_also = threading.Thread(target=self.youtube_download_action_playlist_also, args=(),
                                                          daemon=True)
        self.youtube_mp3_playlist_also.start()

    def youtube_download_action(self):
        try:
            self.downloadFeedback.setFont(QFont('Segue UI', 11))
            self.downloadFeedback.setText("Downloading...\nPlease wait.")
            self.warningLabel_2.hide()
            self.downloadFeedback.show()
            self.cancelButton_2.hide()
            self.downloadButton.hide()
            link = self.youTubeLink.text()
            yt = YouTube(link)
            name = yt.title
            stream = yt.streams.filter(only_audio=True).get_by_itag(251)
            stream.download(output_path=directory_path_all, filename="prototype.webm")
            file_path = directory_path_all / "prototype.webm"
            new_file_path = directory_path_all / f"{name}.mp3"
            audio = AudioFileClip(f"{file_path}")
            audio.write_audiofile(f"{new_file_path}", codec='mp3', bitrate="320k")
            file_path.unlink()
            if self.customSignal_2.text() == "A":
                self.customSignal_2.setText("B")
            else:
                self.customSignal_2.setText("A")
        except RegexMatchError:
            try:
                Playlist(link).title  # This will raise KeyError if the link isn't a playlist
                self.link = link
                self.downloadFeedback.setText("The given link is a playlist.\nChoose an action.")
                self.youTubePlaylist.show()

            except KeyError:
                self.warningLabel_2.setText("Invalid Link!")
                self.warningLabel_2.show()
                self.downloadFeedback.hide()
                self.cancelButton_2.show()
                self.downloadButton.show()

        except urllib.error.URLError:
            self.warningLabel_2.setText(f"An error occurred.(Check internet connection)")
            self.warningLabel_2.show()
            self.downloadFeedback.hide()
            self.cancelButton_2.show()
            self.downloadButton.show()

    def youtube_download_action_playlist_only(self):
        self.youTubePlaylist.hide()
        self.downloadFeedback.setText("Downloading...\nThis might take a few minutes.")
        pl = Playlist(self.link)
        for video in pl.videos:
            name = video.title
            stream = video.streams.filter(only_audio=True).get_by_itag(251)
            stream.download(output_path=directory_path_all, filename="prototype.webm")
            file_path = directory_path_all / "prototype.webm"
            new_file_path = directory_path_all / f"{name}.mp3"
            audio = AudioFileClip(f"{file_path}")
            audio.write_audiofile(f"{new_file_path}", codec='mp3', bitrate="320k")
        if self.customSignal_2.text() == "A":
            self.customSignal_2.setText("B")
        else:
            self.customSignal_2.setText("A")

    def youtube_download_action_playlist_also(self):
        self.youTubePlaylist.hide()
        self.downloadFeedback.setText("Downloading...\nThis might take a few minutes.")
        pl = Playlist(self.link)
        name_playlist = pl.title
        new_playlist_path = directory_path / name_playlist
        new_playlist_path.mkdir()
        for video in pl.videos:
            name = video.title
            stream = video.streams.filter(only_audio=True).get_by_itag(251)
            stream.download(output_path=directory_path_all, filename="prototype.webm")
            file_path = directory_path_all / "prototype.webm"
            new_file_path = directory_path_all / f"{name}.mp3"
            audio = AudioFileClip(f"{file_path}")
            audio.write_audiofile(f"{new_file_path}", codec='mp3', bitrate="320k")
            new_music_path = new_playlist_path / f"{name}.mp3"
            shutil.copyfile(f"{new_file_path}",new_music_path)
        if self.customSignal_2.text() == "A":
            self.customSignal_2.setText("B")
        else:
            self.customSignal_2.setText("A")

    def view_all(self):
        self.playlist_handler(directory_path_all)()

    def make_playlist_prepare(self):
        self.addPlaylist.hide()
        self.playlists.hide()
        self.lineEdit.setText("")
        self.lineEdit.setFocus()
        self.askPlaylist.show()
        count = 0
        musics = directory_path_all.glob("*.mp3")
        self.true_false_dict = {}
        for a in reversed(range(self.verticalLayout_3.count())):
            self.verticalLayout_3.itemAt(a).widget().deleteLater()
        for file in musics:
            name_path = file.name
            name = file.name[:-4]
            if len(name) > 30:
                name = name[:30] + "..."
            name = name + "                                                                   "
            new = QCheckBox()
            new.setText(f" {name}")
            new.setFixedHeight(30)
            new.setStyleSheet(
                "QCheckBox {"
                "    background-color: rgb(29, 29, 29);"
                "    color: white;"
                "    font-size: 16px;"
                "    border-style: outset;"
                "    border-color: white;"
                "    border-width: 0px;"
                "    border-right-width: 0px;"
                "    border-left-width: 0px;"
                "    border-bottom-width: 1px;"
                "    text-align: left;"
                "}"
                "QCheckBox:hover:!pressed {"
                "    background-color: rgb(49, 49, 49);"
                "}"
                "QCheckBox::indicator {"
                "    width: 20px;"
                "    height: 20px;"
                "    margin-left: 10px;"
                "}"
                "QCheckBox::indicator::unchecked {"
                "    image: url();"
                "}"
                "QCheckBox::indicator::checked {"
                "    image: url(:/images/checkmark.png);"
                "}"
            )
            self.true_false_dict[name_path] = new.isChecked()
            new.stateChanged.connect(self.dictionary_handler(name_path))
            self.verticalLayout_3.addWidget(new, alignment=Qt.AlignmentFlag.AlignTop)
            count += 1

    def dictionary_handler(self, x):
        def handler3():
            if self.true_false_dict[x]:
                self.true_false_dict[x] = False
            else:
                self.true_false_dict[x] = True

        return handler3

    def close_playlist_adding_box(self):
        self.addPlaylist.show()
        self.playlists.show()
        self.askPlaylist.hide()

    def create_playlist(self):
        name = self.lineEdit.text()
        if name.isspace() or name == "":
            self.warningLabel.show()
        else:
            self.warningLabel.hide()
            self.close_playlist_adding_box()
            self.make_playlist_action(name)
            self.update_playlist()

    def make_playlist_action(self, name):
        new_playlist_path = directory_path / f"{name}"
        new_playlist_path.mkdir(parents=True, exist_ok=True)
        song_list = list(self.true_false_dict.keys())
        for y in song_list:
            if self.true_false_dict[y]:
                file = directory_path_all / f"{y}"
                target = new_playlist_path / f"{y}"
                try:
                    shutil.copyfile(file, target)
                except PermissionError:
                    pass
            else:
                pass
        self.update_music_list()

    def mousePressEvent(self, event):
        self.mouse_start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing and not self.isMaximized() and (self.CustomBar.underMouse() or self.playlistName.underMouse()):
            self.mouse_end = self.mapToGlobal(event.pos())
            self.mouse_movement = self.mouse_end - self.mouse_start
            self.setGeometry(self.mapToGlobal(self.mouse_movement).x(), self.mapToGlobal(self.mouse_movement).y(),
                             self.width(), self.height())
            self.mouse_start = self.mouse_end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    def open_explorer(self):
        dialog = QFileDialog()
        dialog.setNameFilter("*.mp3")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)

        if dialog.exec():
            selected = dialog.selectedFiles()
            for select in selected:
                file_name = Path(select).name
                target = directory_path / "Music"
                target = target / file_name
                try:
                    shutil.copyfile(select, target)
                except PermissionError:
                    pass
        self.update_music_list()

    def click_handler(self, name):
        def handler():
            self.music_open(x=self.current_path / name)
            self.current_path_for_mode = self.current_path
            if not self.current_path == directory_path_all:
                self.sourceName.setText(f"Playlist: {self.current_path_for_mode.name}")
            else:
                self.sourceName.setText("")

        return handler

    def options_handler(self, name):
        def handler4():
            context_menu = QMenu(self)

            if self.current_path != directory_path_all:
                context_menu.addAction("Remove from playlist", self.handle_remove_from_playlist(name))
            else:
                context_menu.addAction("Delete file", self.handle_remove_from_music(name))
                action = context_menu.addAction("Rename file", self.handle_rename_file(name))
                try:
                    if self.current_piece.name == name:
                        action.setEnabled(False)
                except AttributeError:
                    pass
            playlist_menu = context_menu.addMenu("Add to playlist")
            playlist_list = directory_path.glob("*/")
            for directory in playlist_list:
                directory_name = directory.name
                if directory_name == "Music" or directory_name == self.current_path.name:
                    continue
                playlist_menu.addAction(directory_name, self.handle_add_to_playlist(directory_path_a=directory,
                                                                                    file_name=name))
            context_menu.exec(QCursor.pos())

        return handler4

    def handle_rename_file(self, name):
        def handler9():
            self.renameBox.move(self.mapFromGlobal(QCursor.pos()))
            self.newName.setText(name[:-4])
            self.newName.setFocus()
            self.renameBox.show()
            self.old_name = name
        return handler9

    def handle_add_to_playlist(self, file_name, directory_path_a):
        def handler3():
            file = self.current_path / file_name
            target = directory_path_a / file_name
            try:
                shutil.copyfile(file, target)
            except PermissionError:
                mixer.music.pause()
                shutil.copyfile(file, target)
                mixer.music.unpause()

        return handler3

    def handle_remove_from_playlist(self, name):
        def handler5():
            file = self.current_path / name
            try:
                file.unlink()
            except PermissionError:
                self.music_close()
                file.unlink()
            self.update_music_list()

        return handler5

    def handle_remove_from_music(self, name):
        def handler8():
            directories = directory_path.glob("*/")
            file_list = []
            for directory in directories:
                piece = directory / name
                file_list.append(piece)
            for file in file_list:
                try:
                    file.unlink()
                except FileNotFoundError:
                    pass
                except PermissionError:
                    self.music_close()
                    file.unlink()
            self.update_music_list()

        return handler8

    def playlist_options_handler(self, name):
        def handler6():
            playlist_menu = QMenu(self)
            playlist_menu.addAction("Delete Playlist", self.playlist_delete(name))
            playlist_menu.addAction("Rename Playlist", self.handle_rename_playlist(name))
            playlist_menu.exec(QCursor.pos())

        return handler6

    def handle_rename_playlist(self, name):
        def handler10():
            self.renameBox_2.move(self.mapFromGlobal(QCursor.pos()))
            self.newName_2.setText(name.name)
            self.newName_2.setFocus()
            self.renameBox_2.show()
            self.old_playlist_name = name

        return handler10

    def playlist_delete(self, name):
        def handler7():
            if self.current_path == name:
                self.current_path = directory_path_all
                self.update_music_list()
                self.playlistName.setText(f"    Music")
            try:
                name.rmdir()
            except OSError:
                try:
                    for file in name.glob("*.mp3"):
                        file.unlink()
                except PermissionError:
                    self.music_close()
                    for file in name.glob("*.mp3"):
                        file.unlink()

                name.rmdir()
            self.update_playlist()

        return handler7

    def playlist_handler(self, path):
        def handler2():
            self.current_path = path
            self.update_music_list()
            self.playlistName.setText(f"    {path.name}")

        return handler2

    def update_playlist(self):
        for a in reversed(range(self.verticalLayout_2.count())):
            self.verticalLayout_2.itemAt(a).widget().deleteLater()
        playlists_a = directory_path.glob("*/")
        playlist_list = []
        count = -1
        for file in playlists_a:
            count += 1
            playlist_list.append(file)
        playlist_list.remove(directory_path_all)
        for number in range(0, count):
            playlist_path = playlist_list[number]
            name = playlist_path.name
            new_playlist = QPushButton()
            new_playlist.setText(f"    {name}")
            new_playlist.clicked.connect(self.playlist_handler(playlist_path))
            new_playlist.setStyleSheet("QPushButton"
                                       "{"
                                       "background-color:rgb(29, 29, 29);"
                                       "color:white;"
                                       "border-style:outset;"
                                       "border-color:white;"
                                       "border-width:0-------------px;"
                                       "border-right-width:0px;"
                                       "border-left-width:0px;"
                                       "border-bottom-width:1px;"
                                       "text-align:left;"
                                       "}"
                                       "QPushButton:hover:!pressed"
                                       "{"
                                       "background-color: rgb(40, 40, 40);"
                                       "}")
            new_playlist.setFixedHeight(40)
            self.verticalLayout_2.addWidget(new_playlist, alignment=Qt.AlignmentFlag.AlignTop)
            new_playlist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            new_playlist.customContextMenuRequested.connect(self.playlist_options_handler(playlist_path))

    def update_music_list(self):
        self.colour_flag = False
        count = 0
        objects = []
        for a in reversed(range(self.verticalLayout.count())):
            self.verticalLayout.itemAt(a).widget().deleteLater()
        pieces = self.current_path.glob("*.mp3")
        for i in range(10000):
            new_object = f"piece{i}"
            objects.append(new_object)
        for file in pieces:
            if self.colour_flag:
                self.colour_flag = False
            else:
                self.colour_flag = True
            name = file.name
            objects[count] = QPushButton()
            objects[count].clicked.connect(self.click_handler(name))
            objects[count].setText(f"   {name}"[:-4])
            objects[count].setFixedHeight(60)
            if self.colour_flag:
                objects[count].setStyleSheet("text-align :left;"
                                             "color:white;"
                                             "background-color:rgb(18, 18, 18);")
            else:
                objects[count].setStyleSheet("text-align :left;"
                                             "color:white;"
                                             "background-color:grey;")
            objects[count].setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            objects[count].customContextMenuRequested.connect(self.options_handler(name))

            self.verticalLayout.addWidget(objects[count], alignment=Qt.AlignmentFlag.AlignTop)
            count += 1

    def music_open(self, x, start_time=0):

        try:
            if not self.playlist_switch_flag:
                self.modeChange.show()
            self.playlist_switch_flag = False
            self.PlayPause.setStyleSheet("border-image: url(:/images/pause.png);"
                                         "background-position:center;")
            mixer.music.unload()
            self.current_piece = x
            name = x.name[:-4]
            self.songName.setText(name)
            self.total_length = int(TinyTag.get(x).duration)
            self.remaining = TinyTag.get(x).duration
            self.horizontalSlider.setMaximum(int(self.remaining))
            mixer.music.load(x)
            self.musicSlide.show()
            mixer.music.play(start=start_time)
            self.realtime_start(self.current_piece, TinyTag.get(x).duration - start_time)
        except FileNotFoundError:
            self.update_music_list()
            self.exit_flag = True
            self.label.setText("00:00/00:00")

    def realtime_start(self, x, y):
        if self.realtime and self.realtime.is_alive():
            self.exit_flag = True
            self.realtime.join()
        self.exit_flag = False
        self.realtime = threading.Thread(target=self.timer, args=(x, y), daemon=True)
        self.realtime.start()

    def timer(self, x, y):  # pygame.mixer has a function that tells the time, but it's not accurate.
        length = y
        duration_millisecond = TinyTag.get(x).duration
        duration = turn_into_clock(duration_millisecond)
        while not self.exit_flag:
            if length <= 0:
                break
            remaining = turn_into_clock(duration_millisecond - length)
            length = length - 0.2
            slider_position = int(self.total_length - length)
            self.horizontalSlider.setValue(slider_position)
            self.label.setText(f"{remaining}/{duration}")
            time.sleep(0.2)
        self.remaining = length
        if length <= 0 and self.mode_flag != 0:
            if self.customSignal.text() == "a":
                self.customSignal.setText("b")
            else:
                self.customSignal.setText("a")

    def mode_apply(self):
        if self.mode_flag == 1:
            self.music_open(self.current_piece)
        elif self.mode_flag == 2:
            pieces = self.current_path_for_mode.glob("*.mp3")
            mp3list = []
            for file in pieces:
                mp3list.append(file)
            where = mp3list.index(self.current_piece)
            try:
                self.music_open(mp3list[where + 1])
            except IndexError:
                self.music_open(mp3list[0])
        elif self.mode_flag == 3:
            where = self.randomized_list.index(self.current_piece)
            try:
                try:
                    mixer.music.load(self.randomized_list[where + 1])
                except IndexError:
                    mixer.music.load(self.randomized_list[0])
                try:
                    self.music_open(self.randomized_list[where + 1])
                except IndexError:
                    self.music_open(self.randomized_list[0])
            except pygame.error:
                try:
                    self.music_open(self.randomized_list[where + 2])
                except IndexError:
                    self.music_open(self.randomized_list[0])

    def music_close(self):
        self.exit_flag = True
        try:
            self.realtime.join()
        except AttributeError:
            pass
        mixer.music.unload()
        self.musicSlide.hide()
        self.mode_flag = 3
        self.mode_set()

    def pause_start(self):
        if mixer.music.get_busy():
            self.exit_flag = True
            self.realtime.join()
            mixer.music.pause()
            self.paused = True
            self.PlayPause.setStyleSheet("border-image: url(:/images/play.png);"
                                         "background-position: center;")
        else:
            mixer.music.unpause()
            self.PlayPause.setStyleSheet("border-image: url(:/images/pause.png);"
                                         "background-position: center;")
            self.realtime_start(self.current_piece, self.remaining)
            self.paused = False

    def slider_hold(self):
        self.slider_timer = True
        if mixer.music.get_busy():
            mixer.music.unload()
            self.exit_flag = True
        self.slider_thread_start()

    def slider_release(self):
        self.slider_timer = False
        self.slider_thread.join()
        self.playlist_switch_flag = True
        if self.paused:
            self.music_open(self.current_piece, self.current_value)
            self.pause_start()
        else:
            self.music_open(self.current_piece, self.current_value)

    def slider_thread_start(self):
        if self.slider_thread and self.slider_thread.is_alive():
            self.slider_timer = False
            self.slider_thread.join()
        self.slider_timer = True
        self.slider_thread = threading.Thread(target=self.slider_timer_show, args=())
        self.slider_thread.start()

    def slider_timer_show(self):
        while self.slider_timer:
            time.sleep(0.01)
            self.current_value = int(self.horizontalSlider.value())
            duration = turn_into_clock(TinyTag.get(self.current_piece).duration)
            remaining = turn_into_clock(self.current_value)
            self.label.setText(f"{remaining}/{duration}")

    def mute_unmute(self):
        if self.is_muted:
            self.is_muted = False
            mixer.music.set_volume(self.unmuted_volume)
            self.muteToggle.setStyleSheet("border-image: url(:/images/unmuted.png)")
        else:
            self.is_muted = True
            self.unmuted_volume = mixer.music.get_volume()
            mixer.music.set_volume(0)
            self.muteToggle.setStyleSheet("border-image: url(:/images/muted.png)")

    def volume_slider_start(self):
        if self.slider_volume and self.slider_volume.is_alive():
            self.volume_flag = False
            self.slider_volume.join()
        self.volume_flag = True
        self.slider_volume = threading.Thread(target=self.volume_slider_track, args=())
        self.slider_volume.start()

    def volume_slider_track(self):
        while self.volume_flag:
            time.sleep(0.05)
            self.unmuted_volume = float(self.volumeSlider.value() / 100)
            if not self.is_muted:
                mixer.music.set_volume(self.unmuted_volume)

    def volume_slider_set(self):
        self.volume_flag = False

    def mode_set(self):
        if self.mode_flag == 0:
            self.modeChange.setStyleSheet("border-image: url(:/images/repeatsame.png)")
            self.skip.show()
            self.PlayPause.move(20,10)
        elif self.mode_flag == 1:
            self.modeChange.setStyleSheet("border-image: url(:/images/repeatall.png)")
        elif self.mode_flag == 2:
            self.modeChange.setStyleSheet("border-image: url(:/images/shuffle.png)")
            pieces = self.current_path_for_mode.glob("*.mp3")
            mp3list = []
            for file in pieces:
                mp3list.append(file)
                random.shuffle(mp3list)
                self.randomized_list = mp3list
        elif self.mode_flag == 3:
            self.modeChange.setStyleSheet("border-image: url(:/images/donothing.png)")
            self.skip.hide()
            self.PlayPause.move(60, 10)

        if not self.mode_flag == 3:
            self.mode_flag += 1
        else:
            self.mode_flag = 0


app = QApplication(sys.argv)

window = MainWindow()
window.show()
try:
    sys.exit(app.exec())
except SystemExit:
    mixer.quit()

