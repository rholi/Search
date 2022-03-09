
import os,sys,time, datetime,locale,re
import subprocess,sys
import platform

from time import sleep
from PyQt5 import QtCore
from threading import *
from .filesearcher import FileSearcher

from fman import show_alert


SEARCH_MODE_SEQU = 0
SEARCH_MODE_SPOTLIGHT = 1

class Searcher(QtCore.QObject):

	# Create the signals
	additemSignal = QtCore.pyqtSignal(object)
	messageSignal = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal()
	
	def __init__(self,directory,pattern,searchText='',stopEvent=Event(),searchMode=SEARCH_MODE_SEQU,searchSubDirLevel=0,includeDirectories=True,includeRegex=True, encoding='utf-8'):
		super(Searcher, self).__init__()		
		self.directory = directory
		self.pattern = pattern
		self.searchText = searchText
		self.stopEvent = stopEvent
		self.searchMode = searchMode
		self.searchSubDirLevel = searchSubDirLevel
		self.includeDirectories = includeDirectories
		self.includeRegex = includeRegex
		self.encoding = encoding

	def startSearch(self):
		# On mac start search with Spotlight
		if self.searchMode == SEARCH_MODE_SPOTLIGHT:
			self.searchInSpotlight(self.directory,self.pattern,self.searchText)
		elif self.searchMode == SEARCH_MODE_SEQU:
			self.searchInDir(self.directory,self.pattern,self.searchText)
			
		self.finished.emit()
		
	def shortMessage(self,message):
		short_message = message
		if len(message) > 80:
			short_message = '%s...%s' %(message[:20],message[-60:])

		return(short_message)
	
	def searchInDir(self,directory,searchpattern,searchText=''):
		"search in directory  pattern"
		searchInText = False
		message = directory
		filename = ''
		
		searchArray = []
		if self.includeRegex == False:
			searchArray = searchpattern.split(' ')					

		regexp = convert_filefilter_to_regexp(searchpattern)				
		pattern = re.compile(regexp)
		
		names = os.path.normpath(directory).split(os.sep)
		base_level = len(names)
		
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
					
					# get the depth
					names = os.path.normpath(filename).split(os.sep)
					level = len(names)-base_level-1
					
					if os.path.isdir(filename):
						
						# check for subDirLevel
						if level < self.searchSubDirLevel:
							stack.insert(0,filename)
							
						if level <= self.searchSubDirLevel:	
							# include directories for search pattern
							if self.includeDirectories and pattern.search(filep) and not searchInText:
								# Emit the signal for found directory/filename
								self.additemSignal.emit('[D]%s' %filename)
							
					else:											
						if len(searchArray) > 0:												
							filep = filep.lower()
							containsAll = True
							for searchItem in searchArray:
								if filep.find(searchItem.lower()) == -1:									
									containsAll = False
									break
									
							if containsAll:
								if searchInText:
									if searchText in open(filename, 'r').read():
										self.additemSignal.emit('[T]%s' %filename)
								else:
									self.additemSignal.emit('[F]%s' %filename)
						elif pattern.search(filep):
							if(searchInText):
								fsearch = FileSearcher(filename,self,self.stopEvent,self.encoding)
								if(fsearch.search(searchText,FileSearcher.SEARCH_MODE_TEXT)):	
									# Emit the signal for found filename
									self.additemSignal.emit('[F]%s' %filename)
							else:
								# Emit the signal for found filename
								self.additemSignal.emit('[F]%s' %filename)	
							

					if self.stopEvent.isSet():
						return
				
			except Exception as e:
				self.messageSignal.emit('error: %s' %(e))

		return
		
	# Spotlight Search for MAC only
	def searchInSpotlight(self,directory,pattern,searchText=''):
		self.messageSignal.emit('search in spotlight for %s %s' %(pattern,searchText) )
		command = "mdfind -onlyin '%s'" %(directory)
		if searchText:
			command += " \"kMDItemFSName=='%s' && kMDItemTextContent=='%s'\"" %(pattern,searchText)
		else:
			command += " \"kMDItemFSName=='%s'\"" %(pattern)
			
		for filename in run_command(command):
			self.additemSignal.emit(str(filename))
			if self.stopEvent.isSet():
				return
			
		
	def searchInDirRecursive(self,directory,searchpattern,searchText=''):
		show_alert("Sucht Rekursiv ab Verzeichnis nach pattern")
		"Sucht Rekursiv ab Verzeichnis nach pattern"
		searchInText = False
		message = directory
		filename = ''
		regexp = convert_filefilter_to_regexp(searchpattern)
		pattern = re.compile(regexp)

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

def run_command(command):
	p = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
	for line in iter(p.stdout.readline,b''):
		if line: # Don't print blank lines
			yield line.decode('utf8').replace('\n','')
			
	# waiting for done
	while p.poll() is None:                                                                                                                                        
		sleep(.1) 
		
def convert_filefilter_to_regexp(filefilter):
	regexp = filefilter
	# * to .*
	# ? to .
	# . to [.]
	regexp = regexp.replace('.','[.]')
	regexp = regexp.replace('*','.*')
	regexp = regexp.replace('?','.')

	regexp = '^' + regexp + '$'

	return(regexp)