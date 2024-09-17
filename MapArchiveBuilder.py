import os
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
		os.makedirs(self.archivePath, exist_ok=True)

		## Download map file
		self.getter.getRelativeFile("maps/%s.bsp" % self.mapname)

		## Generate res file
		resgenPath=os.path.join(self.resgenRootPath, "RESGen.exe")
		resgenRFA=os.path.join(self.resgenRootPath, "rfa/res_dod.rfa")
		resgenSubprocessArgs = [resgenPath, "-v", "-b", resgenRFA, "%s/maps/%s.bsp" % (self.archivePath, self.mapname)]
		if platform.system() == "Linux":
			resgenSubprocessArgs.insert(0, "wine")
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
		ovrImgFile = "overviews/%s.bmp" % self.mapname
		ovrDataFile = "overviews/%s.txt" % self.mapname
		try:
			self.getter.getRelativeFile(ovrImgFile)
			self.addResourceToFile(ovrImgFile)
			self.getter.getRelativeFile(ovrDataFile)
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
				try:
					self.getter.getRelativeFile(objfile)
					self.addResourceToFile(objfile)
				except FileNotFoundError:
					pass


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

