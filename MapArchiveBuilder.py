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

		f = open("%s/maps/%s.res" % (self.archivePath, self.mapname), "r")
		lines = f.readlines()

		resources = []
		for line in lines:
			line = line.strip()
			if( line and line[0] != "/"):
				resources.append(line)

		## Download required resources based on the res file
		for res in resources:
			self.getter.getRelativeFile(res)

		## Look for overview file
		try:
			self.getter.getRelativeFile("overviews/%s.bmp" % self.mapname)
			with open("%s/maps/%s.res" % (self.archivePath, self.mapname), "a") as myfile:
				myfile.write("\n\n")
				myfile.write("overviews/%s.bmp" % self.mapname)

			self.getter.getRelativeFile("overviews/%s.txt" % self.mapname)
			with open("%s/maps/%s.res" % (self.archivePath, self.mapname), "a") as myfile:
				myfile.write("\n")
				myfile.write("overviews/%s.txt" % self.mapname)
		except FileNotFoundError:
			shutil.rmtree(os.path.join(self.archivePath, "overviews"))
			print("Overview not found")




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

		if os.path.exists(src):
			os.makedirs(os.path.dirname(dest), exist_ok=True)
		
			shutil.copyfile(src, dest)
		else:
			raise FileNotFoundError
		
		print("Get file: %s" % src)



