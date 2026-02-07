import os
import sys
import shutil
import subprocess
import platform
import urllib.request
from urllib.parse import urljoin

class MapArchiveBuilder:
	def __init__(self, mapname, basePath, outDir, resgenRootPath):
		self.mapname = mapname
		self.archivePath = os.path.join(outDir, mapname)
		self.resgenRootPath = resgenRootPath
		self.resFile = "%s/maps/%s.res" % (self.archivePath, self.mapname)
		self.missingFile = "%s/_missing.txt" % (self.archivePath)
		print("Base Path: %s" % basePath)

		if os.path.exists(basePath):
			self.getter = LocalGetter(basePath, self.archivePath)
			print("Local Path Detected")
		else:
			self.getter = WebGetter(basePath, self.archivePath)
			print("Web URL Detected")

	def build(self):
		"""Build the map archive"""
		skipall = False
		
		## Create map archive root folder
		if os.path.exists(self.archivePath):
			shutil.rmtree(self.archivePath)

		## Download map file
		self.getter.getRelativeFile("maps/%s.bsp" % self.mapname)
		os.makedirs(self.archivePath, exist_ok=True)

		## Generate res file
		resgenPath = os.path.join(self.resgenRootPath, "resgen" if platform.system() == "Linux" else "RESGen.exe")
		resgenRFA = os.path.join(self.resgenRootPath, "rfa/res_dod.rfa")
		resgenSubprocessArgs = [resgenPath, "-v", "-b", resgenRFA, "%s/maps/%s.bsp" % (self.archivePath, self.mapname)]
		subprocess.run(resgenSubprocessArgs)

		f = open(self.resFile, "a+")
		f.seek(0)
		lines = f.readlines()

		self.resources = []
		self.missing = []
		for line in lines:
			line = line.strip()
			if( line and line[0] != "/"):
				self.resources.append(line)

		## Download required resources based on the res file
		print("Downloading resources...")
		for res in self.resources:
			try:
				self.getter.getRelativeFile(res)
			except FileNotFoundError:
				print("File not found:  %s" % res)
				
				self.addMissingResourceToFile(res)
				
				if not skipall:
					skip = input("Skip file? (y/n): ")
					if( skip == "a" ):
						skipall = True
					elif( skip != "y" ):
						self._fatal_filenotfound_message(res)
					
					print("Check %s for missing file list." % self.missingFile)
		
		## Map Info
		mapDataFile = "maps/%s.txt" % self.mapname
		try:
			self.getter.getRelativeFile(mapDataFile)
			self.addResourceToFile(mapDataFile)
		except FileNotFoundError:
			print("Map info not found")

		## Detailed Textures File
		mapDetailFile = "maps/%s_detail.txt" % self.mapname
		try:
			self.getter.getRelativeFile(mapDetailFile)
			self.addResourceToFile(mapDetailFile)
		except FileNotFoundError:
			print("Detailed textures info not found")

		## Look for overview file
		ovrBmpFile = "overviews/%s.bmp" % self.mapname
		ovrTgaFile = "overviews/%s.tga" % self.mapname
		ovrDataFile = "overviews/%s.txt" % self.mapname
		try:
			self.getter.getRelativeFile(ovrTgaFile)
			self.getter.getRelativeFile(ovrDataFile)
			self.addResourceToFile(ovrTgaFile)
			self.addResourceToFile(ovrDataFile)
		except FileNotFoundError:
			try:
				self.getter.getRelativeFile(ovrBmpFile)
				self.getter.getRelativeFile(ovrDataFile)
				self.addResourceToFile(ovrBmpFile)
				self.addResourceToFile(ovrDataFile)
			except FileNotFoundError:
				try:
					shutil.rmtree(os.path.join(self.archivePath, "overviews"))
				except FileNotFoundError:
					pass
				print("Overview not found")

		# Cleanup
		delete_empty_folders(self.archivePath)

	def addResourceToFile(self, relRes):
		if relRes not in self.resources:
			with open(self.resFile, "a") as myfile:
				myfile.write("\n")
				myfile.write(relRes)

	def addMissingResourceToFile(self, path):
		if path not in self.missing:
			with open(self.missingFile, "a") as myfile:
				myfile.write("\n")
				myfile.write(path)

	def _fatal_filenotfound_message(self, file):
		print("File not found:  %s" % file)
		
		# Clean up
		if os.path.exists(self.archivePath):
			shutil.rmtree(self.archivePath)

		exit()






class ResourceGetter:
	def __init__(self):
		pass

class WebGetter(ResourceGetter):
	def __init__(self, baseUrl, destBasePath):
		self.baseUrl = baseUrl
		self.archivePath = destBasePath

	def getRelativeFile(self, file, notify=False):
		src = urljoin(self.baseUrl, file)
		dest = os.path.join(self.archivePath, file)
		os.makedirs(os.path.dirname(dest), exist_ok=True)

		if notify:
			print("Download file: %s" % file)

		try:
			urllib.request.urlretrieve(src, dest)
		except urllib.error.HTTPError:
			raise FileNotFoundError


class LocalGetter(ResourceGetter):
	def __init__(self, srcBasePath, destBasePath):
		self.basePath = self._find_game_root_dir(srcBasePath)
		self.archivePath = destBasePath

	def getRelativeFile(self, file, notify=False):
		src = os.path.join(self.basePath, file)
		dest = os.path.join(self.archivePath, file)

		if notify:
			print("Get file: %s" % src)

		if os.path.exists(src):
			os.makedirs(os.path.dirname(dest), exist_ok=True)
		
			shutil.copyfile(src, dest)
		else:
			raise FileNotFoundError
	
	def _find_folder_by_name(self, root_path, folder_name):
		for dirpath, dirnames, filenames in os.walk(root_path):
			if folder_name in dirnames:
				return os.path.join(dirpath, folder_name)
		return None

	def _find_game_root_dir(self, path):
		foundPath = self._find_folder_by_name(path, "maps")
		if foundPath:
			return os.path.dirname(foundPath)
		raise FileNotFoundError("Game root directory not found in provided source path")


def delete_empty_folders(root):
	"""
		source: https://stackoverflow.com/a/65624165
	"""
	deleted = set()
	
	for current_dir, subdirs, files in os.walk(root, topdown=False):

		still_has_subdirs = False
		for subdir in subdirs:
			if os.path.join(current_dir, subdir) not in deleted:
				still_has_subdirs = True
				break
	
		if not any(files) and not still_has_subdirs:
			os.rmdir(current_dir)
			deleted.add(current_dir)

	return deleted


if __name__ == "__main__":
	print("Map:  %s" % sys.argv[1])
	print("Server Files:  %s" % sys.argv[2])
	print("Output Directory:  %s" % sys.argv[3])
	print("Resgen Folder:  %s" % sys.argv[4])

	map = MapArchiveBuilder(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
	map.build()





