import os,sys,time, datetime,locale,re
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore
from fman import *
import fman.fs
import fman.url
import queue
from fman.url import as_url

from searcher.directory_node import DirectoryNode
from searcher.searcher import Searcher

from threading import *

import json

SEARCHSETUP = os.path.expanduser('~') + os.sep + '.searchsetup'

class SearchDialog(QDialog):
	directoryDict = {}

	def __init__(self,scheme,directory,pane,root_node,parent=None):
		super().__init__()
		self.fman_pane = pane
		self.scheme = scheme

		self.root_node = root_node
		
		self.counter = 0
		self.counterInserted = 0
		
		self.searchStopEvent = Event()
		
		self.directoryDict = {}
		self.fileNameQueue = queue.Queue()

		self.fileNameQueueTimer = QTimer()
		self.fileNameQueueTimer.setInterval(500)
		self.fileNameQueueTimer.timeout.connect(self.addItemsFromQueue)
		self.fileNameQueueTimer.start()
		
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.title = 'Search'
		
		self.directory = directory
		self.fileFilter = ''

		self.setup = self.load_setup(SEARCHSETUP)
		
		self.initUI()
		self.createUI()

	def initUI(self):
		self.resize(1000, 400)
		self.setWindowTitle(self.title)

	def createUI(self):
		self.layout = QVBoxLayout(self)
		self.layout.setContentsMargins(0, 0, 0, 0)
	
		groupBox = QGroupBox("Search")
		self.layout.addWidget(groupBox)
		
		gridLayout = QGridLayout()
		groupBox.setLayout(gridLayout)
		
		fileFilterLabel = QLabel('file filter')
		self.fileFilterText = QLineEdit('*.*')
		
		searchDirLabel = QLabel('search in directory')
		self.searchDirText = QLineEdit(self.directory)
		
		self.searchCheckBox = QCheckBox('search &text')
		self.searchText = QLineEdit()

		self.cancelButton = QPushButton("&Cancel")
		self.cancelButton.clicked.connect(self.closeDialog)
		
		self.searchButton = QPushButton("&Search")
		self.searchButton.setDefault(True)
		self.searchButton.clicked.connect(self.searchButtonClicked)
		
		self.stopButton = QPushButton("Sto&p")
		self.stopButton.clicked.connect(self.stopButtonClicked)
		self.stopButton.setVisible(False)
		
		self.showInFmanButton = QPushButton("show results in &fman pane")
		self.showInFmanButton.clicked.connect(self.showInFman)
		
		
		self.messageLabel = QLabel('')
		
		self.counterLabel = QLabel('')

		gridLayout.addWidget(fileFilterLabel,0,0)	
		gridLayout.addWidget(self.fileFilterText,0,1)
		
		gridLayout.addWidget(searchDirLabel,1,0)	
		gridLayout.addWidget(self.searchDirText,1,1)
		
		gridLayout.addWidget(self.searchCheckBox,2,0)
		gridLayout.addWidget(self.searchText,2,1)
		
		gridLayout.addWidget(self.counterLabel,3,0)
		gridLayout.addWidget(self.messageLabel,3,1)
	
		self.searchResultList = QListWidget()
		self.layout.addWidget(self.searchResultList)
		self.searchResultList.itemDoubleClicked.connect(self.onDoubleClickSearchResultList)
		
		self.progressBar = QProgressBar(self)
		self.layout.addWidget(self.progressBar)
		self.progressBar.setProperty("value", 0)
		self.progressBar.setVisible(False)

		buttonBoxLayout = QHBoxLayout(self)
		buttonBoxLayout.addWidget(self.cancelButton)
		buttonBoxLayout.addWidget(self.searchButton)
		buttonBoxLayout.addWidget(self.stopButton)
		buttonBoxLayout.addWidget(self.showInFmanButton)
		
		self.layout.addLayout(buttonBoxLayout)

		# set from setup
		try:
			filefilter = self.setup['filefilter']
			self.fileFilterText.setText(filefilter)
		except Exception as e:
			pass

		try:
			searchtext = self.setup['searchtext']
			self.searchText.setText(searchtext)
		except Exception as e:
			pass

		try:
			searchtextcheck = self.setup['searchtextcheck']
			self.searchCheckBox.setChecked(searchtextcheck)
		except Exception as e:
			pass


	def onDoubleClickSearchResultList(self,item):
		fullname = item.text()
		path,filename = os.path.split(os.path.abspath(fullname))
		if not filename == '':

			def callback():
				self.fman_pane.place_cursor_at(as_url(fullname))

			self.fman_pane.set_path(as_url(path),callback)

	
	def closeDialog(self):		

		try:
			if hasattr(self,'searchThread'):
				self.searchStop()

			#show_status_message('search end')

			self.addItemsFromQueue()

			if self.isFullScreen():
				self.showNormal()

			self.save_setup(SEARCHSETUP)

			self.close()
		except Exception as e:
			show_status_message('error: %s' %(e))

		
	def showModal(self):	
		self.show()
		rc = self.exec_()
	
	def keyPressEvent(self, e):
		if e.key() == Qt.Key_Escape:
			self.closeDialog()

	def searchButtonClicked(self):
		self.searchButton.setVisible(False)
		self.stopButton.setVisible(True)
		self.stopButton.setDefault(True)
		self.searchInDir()
	
	def stopButtonClicked(self):
		self.stopButton.setVisible(False)
		self.searchButton.setVisible(True)
		self.searchButton.setDefault(True)
		self.searchStop()
	
		
	def searchInDir(self):

		try:
		
			if hasattr(self,'searchThread'):
				self.searchThread.quit()
				self.searchThread.wait()
		
		
			fileFilter = self.fileFilterText.text()
			regexp = self.convert_filefilter_to_regexp(fileFilter)
			pattern = re.compile(regexp)
			directory = self.searchDirText.text()
		
			searchText = ''

			if self.searchCheckBox.isChecked():
				searchText = self.searchText.text()
		
			self.fileNameQueue.queue.clear()
			self.searchResultList.clear()
			self.root_node.clear()
			self.searchStopEvent.clear()
			self.counter = 0
			self.counterInserted = 0

			self.progressBar.setProperty("value", 0)
			self.progressBar.setVisible(True)
			
			self.setFoundFiles(self.counter)

			self.searcher = Searcher(directory,pattern,searchText,self.searchStopEvent)
			self.searchThread = QtCore.QThread()
			self.searcher.moveToThread(self.searchThread)

			self.searchThread.started.connect(self.searcher.startSearch)

			self.searcher.additemSignal.connect(self.searchResultAddItem)
			self.searcher.messageSignal.connect(self.showMessage)
			self.searcher.finished.connect(self.finished)
			self.searchThread.finished.connect(self.finished)

			self.searchThread.start()
		except Exception as e:
			show_status_message('error: %s' %(e))
	

	def searchStop(self):
		
		self.searchStopEvent.set()
		
		if hasattr(self,'searchThread'):
			self.searchThread.quit()
			self.searchThread.wait()		

	def showInFman(self):
		
		if len(self.root_node.children) > 0:
			scheme = 'search://'

			fullname = self.searchDirText.text()
			
			self.fman_pane.set_path(as_url(fullname,scheme))
			
			self.closeDialog()	
		else:
			show_alert('no search results to display in fman!')

		self.close()
				
	def convert_filefilter_to_regexp(self,filefilter):
		regexp = filefilter
		# * to .*
		# ? to .
		# . to [.]
		regexp = regexp.replace('.','[.]')
		regexp = regexp.replace('*','.*')
		regexp = regexp.replace('?','.')

		regexp = '^' + regexp + '$'

		return(regexp)

	def progress(self,value):
		self.progressBar.setProperty('value', value)
		
		self.progressBar.setFormat('update gui %i/%i' %(self.counterInserted,self.counter))

	def addItem(self,filename):
		self.searchResultList.addItem(filename)

		self.counterInserted += 1

		if(self.counter > 0):
			self.progress(100 / self.counter * self.counterInserted)
		
	def addItems(self,filenames):
		self.searchResultList.addItems(filenames)

		self.counterInserted += len(filenames)

		if(self.counter > 0):
			self.progress(100 / self.counter * self.counterInserted)
			
		
		
	def setFoundFiles(self,count):
		self.counterLabel.setText('%i files found' %(count))
		
	def addItemsFromQueue(self):
		try:
			self.setFoundFiles(self.counter)
			QtWidgets.QApplication.instance().processEvents()

			stringList = []

			while not self.fileNameQueue.empty() and self.fileNameQueueTimer.isActive():
				filename = self.fileNameQueue.get()
				stringList.append(filename)
				
				if len(stringList) > 1000:
					self.addItems(stringList)
					stringList.clear()

				self.setFoundFiles(self.counter)
				QtWidgets.QApplication.instance().processEvents()

			self.addItems(stringList)
	
		except Exception as e:
			show_status_message('error: %s' %(e))

	def searchResultAddItem(self,filename):
		self.fileNameQueue.put(filename)
		self.root_node.add_from_os_path(filename)
		self.counter += 1
		
		
	def showMessage(self,message):
		try:
			self.messageLabel.setText(message)
		except Exception as e:
			show_status_message('error: %s' %(e))

	def finished(self):
		self.showMessage('search finished - double click on entry to show file in fman pane')

	def load_setup(self,setupfile):
		list = {}

		try:
			list = json.load(open(setupfile))
		except Exception as e:
			list = {}

		return(list)

	def save_setup(self,setupfile):
		setup = {}
		
		setup['filefilter'] = self.fileFilterText.text()
		setup['searchtext'] = self.searchText.text()
		setup['searchtextcheck'] = self.searchCheckBox.checkState()

		with open(setupfile, 'w') as outfile:
			json.dump(setup, outfile)