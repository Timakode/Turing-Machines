import sys
import time
import itertools
import copy

from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtGui import QRegularExpressionValidator as QRegExpValidator
from PyQt6.QtCore import QThread, pyqtSignal, QRegularExpression as QRegExp
from PyQt6.uic import loadUi
import pyqtgraph as pg
from pyqtgraph import exporters

from turing import Turing

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

ALPHABET = 'abc'
with open('mt.tur', encoding="utf8") as mtFile, \
     open('mmt.tur', encoding="utf8") as mmtFile:
    MT = Turing(mtFile.read())
    MMT = Turing(mmtFile.read(), 4)


class CheckWordThread(QThread): # поток для проверки слова
    stepPassed = pyqtSignal(str)
    resultGot = pyqtSignal(str)

    def __init__(self, mt, word):
        super().__init__()
        self.continueFlag = True
        self.word = word
        self.generator = mt.processWord(word, True)

    def run(self):
        for logStr, iterNum in self.generator:
            if not self.continueFlag:
                self.resultGot.emit(f'Операция прервана на {iterNum} такте.')
                return
            self.stepPassed.emit(logStr + '\n')
            time.sleep(0.001)
        self.resultGot.emit(
            f"Слово «{self.word}» {'' if '1' in logStr else 'НЕ '}"
            f"принадлежит языку ({iterNum} тактов)."
        )


class PlottingThread(QThread): # поток для построения графика
    iterationPassed = pyqtSignal(int)

    def __init__(self, activeMT):
        super().__init__()
        self.continueFlag = True
        self.mt = copy.deepcopy(activeMT)

    def run(self):
        maxIterCounter = 0
        lettersCount = 0
        while self.continueFlag:
            maxIterCounter = 0
            for word in itertools.product(ALPHABET, repeat=lettersCount):
                word = ''.join(word)
                _, iterCounter = tuple(self.mt.processWord(word))[0]
                if iterCounter > maxIterCounter:
                    maxIterCounter = iterCounter
            lettersCount += 1
            self.iterationPassed.emit(maxIterCounter)
            time.sleep(0.25)


class MainWindow(QMainWindow): # главное окно приложения
    def __init__(self):
        super().__init__()
        loadUi('design.ui', self)
        self.activeMT = MT
        self.checkWordThread = None
        self.plotWidg.setLabel('left', 'Макс. число итераций')
        self.plotWidg.setLabel('bottom', 'Длина слова')
        self.iterationsData = []
        self.plottingThread = None

        self.tabsWidg.currentChanged.connect(self.saveBtnUpdateState)
        alphabetValidator = QRegExpValidator(QRegExp(f'[{ALPHABET}]*'))
        self.wordInp.setValidator(alphabetValidator)
        self.wordInp.returnPressed.connect(self.checkWord)
        self.checkBtn.clicked.connect(self.checkWord)
        self.startPlottingBtn.clicked.connect(self.plotting)
        self.tapesCombo.currentIndexChanged.connect(self.switchTapes)
        self.saveBtn.clicked.connect(self.save)

    def checkWord(self): # проверка введенного слова
        if self.checkWordThread and self.checkWordThread.isRunning():
            self.checkWordThread.continueFlag = False
            self.checkBtn.setText("Проверить")
        else:
            self.turingOutp.clear()
            self.checkWordThread = CheckWordThread(self.activeMT, self.wordInp.text())
            self.checkWordThread.stepPassed.connect(
                lambda logStr: self.turingOutp.textCursor().insertText(logStr)
            )
            self.checkWordThread.resultGot.connect(self.wordChecked)
            self.checkWordThread.start()
            self.checkBtn.setText("Завершить")

    def wordChecked(self, result): # отображение результата работы МТ
        self.checkBtn.setText("Проверить")
        self.turingOutp.textCursor().insertText(result)
        self.statusbar.showMessage(result)
        self.saveBtnUpdateState()

    def plotting(self): # запуск/остановка PlottingThread
        if self.plottingThread and self.plottingThread.isRunning():
            self.plottingThread.continueFlag = False
            self.startPlottingBtn.setText("Начать построение")
        else:
            self.statusbar.clearMessage()
            self.plotWidg.clear()
            self.plottingThread = PlottingThread(self.activeMT)
            self.plottingThread.iterationPassed.connect(self.updatePlot)
            self.plottingThread.finished.connect(self.iterationsData.clear)
            self.plottingThread.start()
            self.startPlottingBtn.setText("Завершить построение")
        self.saveBtnUpdateState()

    def updatePlot(self, newIterationsCount): # обновление графика
        self.iterationsData.append(newIterationsCount)
        self.plotWidg.plot(self.iterationsData, pen='k')

    def saveBtnUpdateState(self): # состояние кнопки сохранения
        if self.tabsWidg.currentIndex() == 0:
            self.saveBtn.setText('Сохранить протокол')
            self.saveBtn.setEnabled(bool(
                self.checkWordThread 
                and not self.checkWordThread.isRunning()
            ))
        else:
            self.saveBtn.setText('Сохранить график')
            self.saveBtn.setEnabled(self.plottingThread is not None)

    def switchTapes(self): # переключение активной МТ
        self.activeMT = MT if self.activeMT is MMT else MMT

    def save(self): # сохранение протокла работы МТ или графика (зависит от выбранной вкладки)
        if self.tabsWidg.currentIndex() == 0:
            filename = QFileDialog.getSaveFileName(
                parent=self, filter='Текстовые файлы (*.txt)',
                caption='Выберите файл сохранения протокола работы МТ'
            )[0]
            if filename:
                if not filename.endswith('.txt'):
                    filename += '.txt'
                with open(filename, 'w', encoding="utf8") as file:
                    file.write(self.turingOutp.toPlainText())
        else:
            filename = QFileDialog.getSaveFileName(
                parent=self, filter='Изображения (*.png)',
                caption='Выберите файл сохранения графика'
            )[0]
            if filename:
                if not filename.endswith('.png'):
                    filename += '.png'
                exporter = exporters.ImageExporter(self.plotWidg.scene())
                exporter.parameters()['width'] = 1920
                exporter.export(filename)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
