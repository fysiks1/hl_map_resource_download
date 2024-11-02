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

		if os.path.exists(basePath):
			self.getter = LocalGetter(basePath, self.archivePath)
		else:
			self.getter = WebGetter(basePath, self.archivePath)

	def build(self):
		"""Build the map archive"""
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

		f = open(self.resFile, "r")
		lines = f.readlines()

		self.resources = []
		for line in lines:
			line = line.strip()
			if( line and line[0] != "/"):
				self.resources.append(line)

		## Download required resources based on the res file
		for res in self.resources:
			self.getter.getRelativeFile(res)

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
			pass

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
				shutil.rmtree(os.path.join(self.archivePath, "overviews"))
				print("Overview not found")

		## Custom Objective Icons
		# These are set on the `dod_control_point` entity via the 
		# `point_hud_icon_<neutral|axis|allies>`property set to 
		# values 18 through 27. ResGen doesn't detect these.

		for team in ["allies", "axis", "neutral", "brit"]:
			for index in [1, 2, 3]:
				objfile = "sprites/obj_icons/%s/icon_obj_custom%d_%s.spr" % (self.mapname, index, team)
				if objfile not in self.resources:
					try:
						self.getter.getRelativeFile(objfile)
						self.addResourceToFile(objfile)
					except FileNotFoundError:
						pass

		# Cleanup
		delete_empty_folders(self.archivePath)

	def addResourceToFile(self, relRes):
		if relRes not in self.resources:
			with open(self.resFile, "a") as myfile:
				myfile.write("\n")
				myfile.write(relRes)





class ResourceGetter:
	def __init__(self):
		pass

class WebGetter(ResourceGetter):
	def __init__(self, baseUrl, destBasePath):
		self.baseUrl = baseUrl
		self.archivePath = destBasePath

	def getRelativeFile(self, file):
		src = urljoin(self.baseUrl, file)
		dest = os.path.join(self.archivePath, file)
		os.makedirs(os.path.dirname(dest), exist_ok=True)

		print("Download file: %s" % file)
		try:
			urllib.request.urlretrieve(src, dest)
		except urllib.error.HTTPError:
			raise FileNotFoundError


class LocalGetter(ResourceGetter):
	def __init__(self, srcBasePath, destBasePath):
		self.basePath = srcBasePath
		self.archivePath = destBasePath

	def getRelativeFile(self, file):
		src = os.path.join(self.basePath, file)
		dest = os.path.join(self.archivePath, file)

		print("Get file: %s" % src)

		if os.path.exists(src):
			os.makedirs(os.path.dirname(dest), exist_ok=True)
		
			shutil.copyfile(src, dest)
		else:
			raise FileNotFoundError

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
	map = MapArchiveBuilder(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
	map.build()





