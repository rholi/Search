import os
import stat

class DirectoryNode:
	'''
	DirectoryNode:
	root = DirectoryNode()
	root.add_from_os_path('/usr/home/test/test.txt')
	'''
	def __init__(self,name='root',parent=None):
		self.filestat = None
		self.name = name
		self.parent = parent
		self.children = {}
		
		if parent is not None:
			parent.children[name] = self
	
	@property
	def os_filestat(self):
	
		if self.filestat:
			# return buffered filestat
			return self.filestat

		path = os.path.normpath(self.os_path)
		
		# get fileinfos
		try:
			self.filestat = os.stat(path)
		except:
			self.filestat = None
			
		return(self.filestat)
		
	def get_from_os_path(self,os_path):

		# get the absolute os pathname
		names = os.path.normpath(os_path).split(os.sep)
	
		# begin from root
		root = self.root
			
		dir_entry = root
		for entry in names:
			# search for entry in children
			try:
				dir_entry = dir_entry.children[entry]
			except:
				# not found
				dir_entry = None

		return(dir_entry)
		
	def add_from_os_path(self,os_path):
		normpath = os.path.normpath(os_path)

		# get the absolute os pathname
		names = normpath.split(os.sep)
		
		# begin from root
		root = self.root
		
		dir_entry = root
		for entry in names:
			try:
				dir_entry = dir_entry.children[entry]
			except:
				# not found
				dir_entry = DirectoryNode(entry,dir_entry)
				
		return(dir_entry)
		
	@property
	def os_path(self):

		path = self.path
		ospath = ''

		isFirst = True
		for entry in path:

			if not isFirst:
				ospath += os.sep

			isFirst = False

			ospath += entry.name
		return(os.path.normpath(ospath))
			
	@property
	def path(self):
		return(self._path)
			
	@property
	def _path(self):
		path = []
		node = self
		while not node.is_root:
			path.insert(0, node)
			node = node.parent
		return list(path)
			
	@property
	def root(self):
		node = self
		while node.parent:
			node = node.parent
		return node

	@property
	def first_with_children(self):
		node = self
		while len(node.children_as_list) == 1:
			node = node.children_as_list[0]
		
		return(node)
		
	@property
	def allchildren(self):
		return(list(self._allchildren))
	
	@property
	def children_as_list(self):
		children = self.children
		if(children):
			return(list(children.values()))
		else:
			return(children)
		
	@property
	def children_as_reverse_list(self):
		children = self.children_as_list
		if children:
			children.reverse()
			#reversed(sorted(children))
		return(children);
		
	@property
	def children_as_string(self):
		names = []
		for node in self.children_as_list:
			names.append(node.name)
		return(names)	
		
	@property
	def _allchildren(self):
		children = []
		
		stack = [self]
		while stack:
			cur_node = stack[0]
			stack = stack[1:]
			children.append(cur_node)
			for child in cur_node.children_as_reverse_list:
				stack.insert(0,child)

		return(children)

	def tree(self):
		tree_str = ''
		for node in self.allchildren:
			deep = len(node.path)
			if node.name:
				print(' ' * deep + node.name)

		return(tree_str)
		
	@property
	def siblings(self):
		return(list(self._siblings()))
		
	def _siblings(self):
		siblings = []
		
		if self.parent is not None:
			for key in self.parent.children:
				child = self.parent.children[key]
				siblings.append(child)
				
		return(siblings)
		
	@property
	def is_root(self):
		return(self.parent == None)
		
	@property
	def is_dir(self):
		return(len(self.children) > 0)

	def clear(self):
		self.children.clear()
	
	def __iter__(self):
		yield(self)
		for child in self.allchildren:
			yield(child)
			
	#def __repr__(self):
	#	return('%r' %  [str(self.name) for node in self.path])
			
	def __repr__(self):
		name = self.name
		path = self.os_path
		if self.is_root:
			name = 'root'
			path = ''
		return('(DirectoryNode name:%s path:%s)' %  (name,path))	

