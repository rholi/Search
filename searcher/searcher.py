
import os,sys,time, datetime,locale,re

from PyQt5 import QtCore
from threading import *
from .filesearcher import FileSearcher

class Searcher(QtCore.QObject):

	# Create the signals
	additemSignal = QtCore.pyqtSignal(object)
	messageSignal = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal()
	
	def __init__(self,directory,pattern,searchText='',stopEvent=Event()):
		super(Searcher, self).__init__()

		self.directory = directory
		self.pattern = pattern
		self.searchText = searchText
		self.stopEvent = stopEvent

	def startSearch(self):
		self.searchInDir(self.directory,self.pattern,self.searchText)
		self.finished.emit()
		
	def shortMessage(self,message):
		short_message = message
		if len(message) > 80:
			short_message = '%s...%s' %(message[:20],message[-60:])

		return(short_message)
	
	def searchInDir(self,directory,pattern,searchText=''):
		"searach in directory  pattern"
		searchInText = False
		message = directory
		filename = ''

		stack = [directory]

		if(len(searchText) > 0):
			searchInText = True
		
		while stack:
			cur_dir = stack[0]
			
			self.messageSignal.emit(self.shortMessage(cur_dir))

			stack = stack[1:]
			try:
				filesInDir = os.listdir(cur_dir)
				for filep in filesInDir:

					filename = cur_dir + os.sep + filep
					if os.path.isdir(filename):
						stack.insert(0,filename)
						self.messageSignal.emit(self.shortMessage(filename))
					else:
						if pattern.search(filep):
							if(searchInText):
								fsearch = FileSearcher(filename,self,self.stopEvent)
								if(fsearch.search(searchText,FileSearcher.SEARCH_MODE_TEXT)):	
									# Emit the signal for found filename
									self.additemSignal.emit(filename)
							else:
								# Emit the signal for found filename
								self.additemSignal.emit(filename)	
							

					if self.stopEvent.isSet():
						return
				
			except Exception as e:
				self.messageSignal.emit('error: %s' %(e))

		return
	
	def searchInDirRecursive(self,directory,pattern,searchText=''):
		"Sucht Rekursiv ab Verzeichnis nach pattern"
		searchInText = False
		message = directory
		filename = ''

		if(len(searchText) > 0):
			searchInText = True

		if len(directory) > 60:
			message = '%s...%s' %(directory[:20],directory[-30:])

		self.messageSignal.emit(message)

		if self.stopEvent.isSet():
			return
		
		try:
			filesInDir = os.listdir(directory)
			for filep in filesInDir:

				filename = directory + os.sep + filep
				if os.path.isdir(filename):
					self.searchInDirRecursive(filename,pattern,searchText) 
				else:
					if pattern.search(filep):
						if(searchInText):
							fs = FileSearcher(filename,self)
							if(fs.search(searchText,FileSearcher.SEARCH_MODE_TEXT)):	
								# Emit the signal for found filename
								self.additemSignal.emit(filename)
								
						else:
							# Emit the signal for found filename
							self.additemSignal.emit(filename)
							

				if self.stopEvent.isSet():
					break
				
		except Exception as e:
			self.messageSignal.emit('error: %s' %(e))

		return

	 