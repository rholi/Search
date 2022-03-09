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

SEARCH_SUBDIR_MODE_ALL = 0
SEARCH_SUBDIR_MODE_CURRENT = 1
SEARCH_SUBDIR_MODE_LEVEL = 2


class SearchDialog(QDialog):
	directoryDict = {}

	def __init__(self,scheme,directory,pane,root_node,parent=None):
		super().__init__()
		self.fman_pane = pane
		self.scheme = scheme

		self.root_node = root_node
		
		self.counter = 0
		self.counterFileInserted = 0
		self.counterDirInserted = 0
		
		
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
		
		self.searchSpotlightLabel = QLabel('search for files with spotlight')
		self.searchSpotlightCheckBox = QCheckBox('Sp&otlight Search')
		self.searchSpotlightCheckBox.stateChanged.connect(self.spotlightChecked)
		
		fileFilterLabel = QLabel('file filter')
		self.fileFilterText = QComboBox()
		self.fileFilterText.setEditable(True)
		
		searchDirLabel = QLabel('search in directory')
		self.searchDirText = QLineEdit(self.directory)
		
		
		subdirsHBoxLayout = QHBoxLayout(self)
				
		self.searchSubDirLabel = QLabel('search in subdirs:')
		
		self.searchSubDirAll = QRadioButton('all')
		self.searchSubDirAll.setChecked(True)
		
		self.searchSubDirCurrent = QRadioButton('only current')
		self.searchSubDirAll.setChecked(False)
		
		self.searchSubDirLevel = QRadioButton('depth:')
		self.searchSubDirAll.setChecked(False)
		
		self.searchSubDirLevelText = QLineEdit('1')		
		self.searchSubDirLevelText.setInputMask('99')
		
		self.includeDirectoriesCheckBox = QCheckBox('include directories in fileslist')

		self.includeRegexModeCheckBox = QCheckBox('use regex')
		
		subdirsHBoxLayout.addWidget(self.includeDirectoriesCheckBox)
		subdirsHBoxLayout.addWidget(self.includeRegexModeCheckBox)
		subdirsHBoxLayout.addStretch(1)
		
		subdirsHBoxLayout.addWidget(self.searchSubDirLabel)
		
		
		# search depth
		self.searchSubDirButtonGroup = QButtonGroup()
		self.searchSubDirButtonGroup.addButton(self.searchSubDirAll,SEARCH_SUBDIR_MODE_ALL)
		self.searchSubDirButtonGroup.addButton(self.searchSubDirCurrent,SEARCH_SUBDIR_MODE_CURRENT)
		self.searchSubDirButtonGroup.addButton(self.searchSubDirLevel,SEARCH_SUBDIR_MODE_LEVEL)
		
		subdirsHBoxLayout.addWidget(self.searchSubDirAll)
		subdirsHBoxLayout.addWidget(self.searchSubDirCurrent)
		subdirsHBoxLayout.addWidget(self.searchSubDirLevel)
		subdirsHBoxLayout.addWidget(self.searchSubDirLevelText)
		subdirsHBoxLayout.addStretch(1)
		
		# search text
		self.searchCheckBox = QCheckBox('search &text')
		self.searchCheckBox.stateChanged.connect(self.searchTextChecked)
		self.searchText = QComboBox()
		self.searchText.setEditable(True)
		
		# encoding
		self.encodingLabel = QLabel('encoding')
		self.encodingText = QComboBox()
		self.encodingText.addItem('utf-8')
		self.encodingText.addItem('utf-16')
		self.encodingText.addItem('cp437')
		self.encodingText.addItem('cp1252')
		
		self.encodingText.setEditable(True)

		# buttons
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

		gridLayout.addWidget(self.searchSpotlightCheckBox,0,0)
		gridLayout.addWidget(self.searchSpotlightLabel,0,1)	

		gridLayout.addWidget(fileFilterLabel,1,0)	
		gridLayout.addWidget(self.fileFilterText,1,1)
		
		gridLayout.addWidget(searchDirLabel,2,0)	
		gridLayout.addWidget(self.searchDirText,2,1)
		
		gridLayout.addLayout(subdirsHBoxLayout,3,1)
		
		gridLayout.addWidget(self.searchCheckBox,4,0)
		gridLayout.addWidget(self.searchText,4,1)
		
		encodingBoxLayout = QHBoxLayout(self)
		encodingBoxLayout.addWidget(self.encodingLabel)
		encodingBoxLayout.addWidget(self.encodingText)
		encodingBoxLayout.addStretch(1)
		
		gridLayout.addLayout(encodingBoxLayout,5,1)
		
		gridLayout.addWidget(self.counterLabel,6,0)
		gridLayout.addWidget(self.messageLabel,6,1)
	
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
		
		self.preset()
		

	def preset(self):
		# set from setup
		try:
			spotlightcheck = self.setup['searchspotlight']
			self.searchSpotlightCheckBox.setChecked(spotlightcheck)
		except Exception as e:
			pass
			
		try:
			filefilterhistory = self.setup['filefilterhistory']
			self.fileFilterText.addItems(filefilterhistory)
		except Exception as e:
			pass

		try:
			filefilter = self.setup['filefilter']
			self.fileFilterText.setEditText(filefilter)
		except Exception as e:
			pass

		try:
			searchtexthistory = self.setup['searchtexthistory']
			self.searchText.addItems(searchtexthistory)
		except Exception as e:
			pass

		try:
			searchtext = self.setup['searchtext']
			self.searchText.setEditText(searchtext)
		except Exception as e:
			pass

		try:
			searchtextcheck = self.setup['searchtextcheck']
			self.searchCheckBox.setChecked(searchtextcheck)
		except Exception as e:
			pass
			
		try:
			searchsubdirallcheck = self.setup['searchsubdirall']
			self.searchSubDirAll.setChecked(searchsubdirallcheck)
		except Exception as e:
			pass
			
		try:
			searchsubdircurrentcheck = self.setup['searchsubdircurrent']
			self.searchSubDirCurrent.setChecked(searchsubdircurrentcheck)
		except Exception as e:
			pass
			
		try:
			searchsubdirlevelcheck = self.setup['searchsubdirlevel']
			self.searchSubDirLevel.setChecked(searchsubdirlevelcheck)
		except Exception as e:
			pass	
			
		try:
			searchsubdirleveltext = self.setup['searchsubdirleveltext']
			self.searchSubDirLevelText.setText(searchsubdirleveltext)
		except Exception as e:
			pass	

		try:
			includedirectoriescheck = self.setup['includedirectoriescheck']
			self.includeDirectoriesCheckBox.setChecked(includedirectoriescheck)
		except Exception as e:
			pass	

		try:
			includegexcheck = self.setup['includegexcheck']
			self.includeRegexModeCheckBox.setChecked(includegexcheck)
		except Exception as e:
			pass		
			
		try:
			encoding = self.setup['encoding']
			self.encodingText.setEditText(encoding)
		except Exception as e:
			pass	
			
			
		# spotlight only for Mac
		if platform.system() == 'Darwin':
			self.setSpotlightMode(self.searchSpotlightCheckBox.isChecked(),True)
			self.setTextMode(self.searchCheckBox.isChecked(),True)
		else:
			# spotlight mode is off 
			self.searchSpotlightCheckBox.setChecked(False)
			self.setSpotlightMode(self.searchSpotlightCheckBox.isChecked(),False)
			self.setTextMode(self.searchCheckBox.isChecked(),True)
			
		
			
	def spotlightChecked(self,checked):
		# turn off text search if spotlight mode is on
		if checked:
			self.setTextMode(False,False)
	
		self.setSpotlightMode(checked,True)
		
		
	def searchTextChecked(self,checked):
		self.setTextMode(checked,True)
		
		
	def setTextMode(self,enabled,visible=False):
		self.searchCheckBox.setVisible(visible)
		
		self.searchText.setVisible(enabled and visible)

		# is spotlight is active no encoding
		if not self.searchSpotlightCheckBox.isChecked():
			self.encodingLabel.setVisible(enabled and visible)
			self.encodingText.setVisible(enabled and visible)
		
	
	def setSpotlightMode(self,enabled,visible=False):
		
		self.searchSpotlightLabel.setVisible(visible)
		self.searchSpotlightCheckBox.setVisible(visible)

		self.includeDirectoriesCheckBox.setVisible(not enabled)
		self.searchSubDirLabel.setVisible(not enabled)
		self.searchSubDirAll.setVisible(not enabled)
		self.searchSubDirCurrent.setVisible(not enabled)
		self.searchSubDirLevel.setVisible(not enabled)
		self.searchSubDirLevelText.setVisible(not enabled)
		
		self.searchCheckBox.setVisible(visible)
		self.searchText.setVisible(visible)
			
		self.encodingLabel.setVisible(not enabled)
		self.encodingText.setVisible(not enabled)
		
		self.setTextMode(self.searchCheckBox.isChecked(),True)
		

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
		self.save_setup(SEARCHSETUP)
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
		
		
			pattern = self.fileFilterText.currentText()
			if len(pattern) == 0:
				pattern = '*'
				
			directory = self.searchDirText.text()
		
			searchText = ''
			if self.searchCheckBox.isChecked():
				searchText = self.searchText.currentText()
		
			searchSubDirMode = self.searchSubDirButtonGroup.checkedId()
			searchSubDirLevelText = self.searchSubDirLevelText.text()
			includeDirectories = self.includeDirectoriesCheckBox.isChecked()
			includeRegex = self.includeRegexModeCheckBox.isChecked()
			
			searchSubDirLevel = 0
			
			if searchSubDirMode == SEARCH_SUBDIR_MODE_ALL:
				searchSubDirLevel = 9999999999999
			elif searchSubDirMode == SEARCH_SUBDIR_MODE_CURRENT:
				searchSubDirLevel = 0
			else:
				try:
					searchSubDirLevel = int(searchSubDirLevelText)
				except Exception as e1:
					searchSubDirLevel = 0
			
			self.fileNameQueue.queue.clear()
			self.searchResultList.clear()
			self.root_node.clear()
			self.searchStopEvent.clear()
			self.counter = 0
			self.counterFileInserted = 0
			self.counterDirInserted = 0

			self.progress(0)
			self.progressBar.setVisible(True)
			
			self.setFoundFiles(self.counter,self.counterFileInserted,self.counterDirInserted)

			searchmode = SEARCH_MODE_SEQU
			if platform.system() == 'Darwin' and self.searchSpotlightCheckBox.isChecked():
				searchmode = SEARCH_MODE_SPOTLIGHT

			encoding = self.encodingText.currentText()
			if len(encoding.strip()) == 0:
				encoding = 'utf-8'
				
			self.searcher = Searcher(directory,pattern,searchText,self.searchStopEvent,searchmode,searchSubDirLevel,includeDirectories,includeRegex,encoding)
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
		self.progressBar.setFormat('update filelist %i/%i' %(self.counterFileInserted+self.counterDirInserted,self.counter))

	def addItem(self,filename):
		if filename.startswith('[D]'):
			filename = filename[3:]
			self.counterDirInserted += 1
			
		elif filename.startswith('[F]'):
			filename = filename[3:]
			self.counterFileInserted += 1
		else:
			self.counterFileInserted += 1
			
		self.searchResultList.addItem(filename)

		if(self.counter > 0):
			self.progress(100 / self.counter * (self.counterFileInserted + self.counterDirInserted))
		
	def addItems(self,filenames):
	
		newfilenames = []
		for file in filenames:
			filename = file
			if file.startswith('[D]'):
				filename = file[3:]
				self.counterDirInserted += 1
			elif file.startswith('[F]'):
				filename = file[3:]
				self.counterFileInserted += 1
			else:
				self.counterFileInserted += 1
				
			newfilenames.append(filename)
	
		self.searchResultList.addItems(newfilenames)

		if(self.counter > 0):
			self.progress(100 / self.counter * (self.counterFileInserted + self.counterDirInserted))

		QtWidgets.QApplication.instance().processEvents()
			
		
		
	def setFoundFiles(self,counter,countFiles,countDirectories):
		if countFiles == 1:
			filestext = 'file'
		else:
			filestext = 'files'
			
		if countDirectories == 1:
			dirtext = 'directory'
		else:
			dirtext = 'directories'
			
		self.counterLabel.setText('%i %s\n%i %s found' %(countFiles,filestext,countDirectories,dirtext))
		
	def addItemsFromQueue(self):
		try:
			self.setFoundFiles(self.counter,self.counterFileInserted,self.counterDirInserted)
			QtWidgets.QApplication.instance().processEvents()

			stringList = []

			while not self.fileNameQueue.empty() and self.fileNameQueueTimer.isActive():
				filename = self.fileNameQueue.get()
				stringList.append(filename)
				
				if len(stringList) > 1000:
					self.addItems(stringList)
					stringList.clear()

				self.setFoundFiles(self.counter,self.counterFileInserted,self.counterDirInserted)
				QtWidgets.QApplication.instance().processEvents()

			self.addItems(stringList)
			
	
		except Exception as e:
			show_status_message('error: %s' %(e))

	def searchResultAddItem(self,filename):
		self.fileNameQueue.put(filename)
		
		if filename.startswith('[D]'):
			filename = filename[3:]
		elif filename.startswith('[F]'):
			filename = filename[3:]
			
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
		
		filefilter = self.fileFilterText.currentText()
		
		# save only the last 10 entries
		filefilterhistory = []
		try:
			filefilterhistory = self.setup['filefilterhistory']
		except Exception as e:
			pass
		
		if not filefilter in filefilterhistory:
			filefilterhistory.insert(0,filefilter)
			
		if len(filefilterhistory) > 10:
			filefilterhistory = filefilterhistory[:10]
		
		
		searchtext = self.searchText.currentText()
		
		# save only the last 10 entries
		searchtexthistory = []
		try:
			searchtexthistory = self.setup['searchtexthistory']
		except Exception as e:
			pass
		
		if not searchtext in searchtexthistory:
			searchtexthistory.insert(0,searchtext)
			
		if len(searchtexthistory) > 10:
			searchtexthistory = searchtexthistory[:10]
		
		
		setup['filefilter'] 			 = filefilter
		setup['filefilterhistory'] 		 = filefilterhistory
		setup['searchtext'] 			 = searchtext
		setup['searchtexthistory'] 		 = searchtexthistory
		setup['searchtextcheck'] 		 = self.searchCheckBox.checkState()
		setup['searchspotlight'] 		 = self.searchSpotlightCheckBox.checkState()
		setup['searchsubdirall'] 		 = self.searchSubDirAll.isChecked()
		setup['searchsubdircurrent'] 	 = self.searchSubDirCurrent.isChecked()
		setup['searchsubdirlevel'] 		 = self.searchSubDirLevel.isChecked()
		setup['searchsubdirleveltext'] 	 = self.searchSubDirLevelText.text()
		setup['includedirectoriescheck'] = self.includeDirectoriesCheckBox.checkState()
		setup['includegexcheck'] 		 = self.includeRegexModeCheckBox.checkState()
		setup['encoding']             	 = self.encodingText.currentText()
		
		with open(setupfile, 'w') as outfile:
			json.dump(setup, outfile)