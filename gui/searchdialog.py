import os,sys,time, datetime,locale,re
import platform
import fman.fs
import fman.url
import queue
import json

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore
from fman import *
from fman.url import as_url

from searcher.directory_node import DirectoryNode
from searcher.searcher import *

from threading import *

SEARCHSETUP = os.path.expanduser('~') + os.sep + '.searchsetup'
BUTTON_MODE_FOR_SEARCHING = 0
BUTTON_MODE_FOR_STOPPING  = 1

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
		
		self.searchSpotlightCheckBox = QCheckBox('Sp&otlight Search')
		
		
		fileFilterLabel = QLabel('file filter')
		self.fileFilterText = QLineEdit('*.*')
		
		searchDirLabel = QLabel('search in directory')
		self.searchDirText = QLineEdit(self.directory)
		
		self.searchCheckBox = QCheckBox('search &text')
		self.searchText = QLineEdit()

		self.cancelButton = QPushButton("&Cancel")
		self.cancelButton.clicked.connect(self.closeDialog)
		
		self.searchButton = QPushButton("&Search")
		self.searchButton.clicked.connect(self.searchButtonClicked)
		
		self.stopButton = QPushButton("Sto&p")
		self.stopButton.clicked.connect(self.stopButtonClicked)
		
		self.showInFmanButton = QPushButton("show results in &fman pane")
		self.showInFmanButton.clicked.connect(self.showInFman)
		
		
		self.messageLabel = QLabel('')
		
		self.counterLabel = QLabel('')

		# Only for Mac
		if platform.system() == 'Darwin':
			gridLayout.addWidget(self.searchSpotlightCheckBox,0,0)
			gridLayout.addWidget(QLabel('search for files with spotlight'),0,1)	

		gridLayout.addWidget(fileFilterLabel,1,0)	
		gridLayout.addWidget(self.fileFilterText,1,1)
		
		gridLayout.addWidget(searchDirLabel,2,0)	
		gridLayout.addWidget(self.searchDirText,2,1)
		
		gridLayout.addWidget(self.searchCheckBox,3,0)
		gridLayout.addWidget(self.searchText,3,1)
		
		gridLayout.addWidget(self.counterLabel,4,0)
		gridLayout.addWidget(self.messageLabel,4,1)
	
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
		
		self.buttonMode(BUTTON_MODE_FOR_SEARCHING)

		# set from setup
		try:
			spotlightcheck = self.setup['searchspotlight']
			self.searchSpotlightCheckBox.setChecked(spotlightcheck)
		except Exception as e:
			pass
			
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
			self.fileNameQueueTimer.stop()

			if hasattr(self,'searchThread'):
				self.searchStop()


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
			
	def buttonMode(self,button_mode):
		try:
			if button_mode == BUTTON_MODE_FOR_SEARCHING:
				
				self.stopButton.setEnabled(False)
				self.stopButton.setVisible(False)
				
				self.searchButton.setVisible(True)
				self.searchButton.setEnabled(True)
				self.searchButton.setDefault(True)
			
			elif button_mode == BUTTON_MODE_FOR_STOPPING:			
				
				self.searchButton.setEnabled(False)
				self.searchButton.setVisible(False)
				
				self.stopButton.setVisible(True)
				self.stopButton.setEnabled(True)
				self.stopButton.setDefault(True)
				
			QtWidgets.QApplication.instance().processEvents()
			
		except Exception as e:
			show_status_message('error: %s' %(e))
			
		
	def searchButtonClicked(self):
		show_status_message('searching...')
		self.buttonMode(BUTTON_MODE_FOR_STOPPING)
		self.searchInDir()
		
	
	def stopButtonClicked(self):
		show_status_message('stopping...')
		self.buttonMode(BUTTON_MODE_FOR_SEARCHING)
		self.searchStop()
		
	def searchInDir(self):

		try:
		
			if hasattr(self,'searchThread'):
				self.searchThread.quit()
				self.searchThread.wait()
		
		
			pattern = self.fileFilterText.text()
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

			searchmode = SEARCH_MODE_SEQU
			if platform.system() == 'Darwin' and self.searchSpotlightCheckBox.isChecked():
				searchmode = SEARCH_MODE_SPOTLIGHT

			self.searcher = Searcher(directory,pattern,searchText,self.searchStopEvent,searchmode)
			self.searchThread = QtCore.QThread()
			self.searcher.moveToThread(self.searchThread)

			self.searchThread.started.connect(self.searcher.startSearch)

			self.searcher.additemSignal.connect(self.searchResultAddItem)
			self.searcher.messageSignal.connect(self.showMessage)
			self.searcher.finished.connect(self.finished)

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

	def progress(self,value):
		self.progressBar.setProperty('value', value)
		self.progressBar.setFormat('update filelist %i/%i' %(self.counterInserted,self.counter))

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

		QtWidgets.QApplication.instance().processEvents()
			
		
		
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
		self.buttonMode(BUTTON_MODE_FOR_SEARCHING)
		self.showMessage('search finished - double click on entry to show file in fman pane')
		clear_status_message()
		
		
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
		setup['searchspotlight'] = self.searchSpotlightCheckBox.checkState()

		with open(setupfile, 'w') as outfile:
			json.dump(setup, outfile)