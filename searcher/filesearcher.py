
import mmap,os,codecs
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from threading import *

class FileSearcher(QtCore.QObject):
	SEARCH_MODE_TEXT=1
	SEARCH_MODE_MAP=2
	SEARCH_MODE_LIMIT=64000
	
	_fileName = ''
	_f=0
	
	def __init__(self,fileName,parent=None,stopEvent=Event()):
		super(FileSearcher, self).__init__(parent)
		self.stopEvent = stopEvent
		if os.path.isfile(fileName):
			self._fileName = fileName
		
	def search(self,searchText,mode):
		rc = False
		try:
			if len(self._fileName) > 0:
				self._f = codecs.open(self._fileName,"r",encoding='utf-8', errors='ignore')
				if(mode==self.SEARCH_MODE_TEXT):
					rc = self._searchText(self._f,searchText)
				elif(mode==self.SEARCH_MODE_MAP):
					rc = self._searchMap(self._f,searchText)
				self._f.close()
		except Exception as e:
			rc = False

		return(rc)
	
	def _searchText(self,f,searchText):
		rc = False

		for line in f:
			if self.stopEvent.isSet():
				break
				
			if searchText in line:
				rc = True
				break
				
		return(rc)
		
	def _searchTextSmall(self,f,searchText):
		rc = False
		if searchText in f.read():
			rc = True
				
		return(rc)
		
	def _searchMap(self,f,searchText):
		rc = False
		s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
		if s.find(bytearray(searchText,encoding='utf-8')) != -1:
			rc = True
		
		return(rc)