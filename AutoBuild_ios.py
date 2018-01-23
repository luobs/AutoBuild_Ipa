#!/usr/bin/env python
# -*- coding:utf-8 -*-

#./autobuild.py -p youproject.xcodeproj -s schemename
#./autobuild.py -w youproject.xcworkspace -s schemename

import argparse
import subprocess
import requests
import os,time
from datetime import datetime
from selenium import webdriver
starttime = datetime.now()
#from git_lab.Gitlab_project import setup

#configuration for iOS build setting
CONFIGURATION = "Debug"
EXPORT_OPTIONS_PLIST = "exportOptions.plist"
#会在桌面创建输出ipa文件的目录
EXPORT_MAIN_DIRECTORY = "~/Desktop/IPA/"

# configuration for pgyer
PGYER_UPLOAD_URL = "http://www.pgyer.com/apiv1/app/upload"
DOWNLOAD_BASE_URL = "http://www.pgyer.com"
USER_KEY = "2d56feaf82e43b173963b13a1f1dbd49"
API_KEY = "59dea7fd36ad9c8f6baea732d64b73be"
#设置从蒲公英下载应用时的密码
PYGER_PASSWORD = ""
# 蒲公英更新描述
PGYDESC = ""
#删除 *.xcarchive
def cleanArchiveFile(archiveFile):
	cleanCmd = "rm -r %s" %(archiveFile)
	process = subprocess.Popen(cleanCmd, shell = True)
	process.wait()
	print "cleaned archiveFile: %s" %(archiveFile)

#上传结果打印
def parserUploadResult(jsonResult):
	resultCode = jsonResult['code']
	browser = webdriver.Chrome()
	if resultCode == 0:
		downUrl = DOWNLOAD_BASE_URL +"/"+jsonResult['data']['appShortcutUrl']
		print "Upload Success"
		print "DownUr: " + downUrl
		browser.get(downUrl)
		time.sleep(10)
		browser.quit()
	else:
		print "Upload Fail!"
		print "Reason:"+jsonResult['message']
#上传parser
def uploadIpaToPgyer(ipaPath):
    print "ipaPath:"+ipaPath
    ipaPath = os.path.expanduser(ipaPath)
    ipaPath = unicode(ipaPath, "utf-8")
    files = {'file': open(ipaPath, 'rb')}
    headers = {'enctype':'multipart/form-data'}
    payload = {'uKey':USER_KEY,'_api_key':API_KEY,'Integer':'1', 'password':PYGER_PASSWORD, 'updateDescription':PGYDESC}
    #print "update desc：" + PGYDESC
    print "uploading...."
    ret = requests.post(PGYER_UPLOAD_URL, data = payload ,files=files,headers=headers)
    if ret.status_code == requests.codes.ok:
         result = ret.json()
         parserUploadResult(result)
    else:
        print 'HTTPError,Code:'+r.status_code

#创建输出ipa文件路径: ~/Desktop/{scheme}{2016-12-28_08-08-10}
def buildExportDirectory(scheme):
	dateCmd = 'date "+%Y-%m-%d_%H-%M-%S"'
	process = subprocess.Popen(dateCmd, stdout=subprocess.PIPE, shell=True)
	(stdoutdata, stderrdata) = process.communicate()
	exportDirectory = "%s%s%s" %(EXPORT_MAIN_DIRECTORY, scheme, stdoutdata.strip())
	return exportDirectory
#返回工程目录下Archive路径
def buildArchivePath(tempName):
	process = subprocess.Popen("pwd", stdout=subprocess.PIPE)
	(stdoutdata, stderrdata) = process.communicate()
	archiveName = "%s.xcarchive" %(tempName)
	archivePath = stdoutdata.strip() + '/' + archiveName
	return archivePath
#返回保存路径下ipa的路径
def getIpaPath(exportPath):
	ipaPath = exportPath + "/EClite.ipa"
	return ipaPath

#生成 *.ipa
def exportIpa(scheme, archivePath):
    exportDirectory = buildExportDirectory(scheme)
    exportCmd = "xcodebuild -exportArchive -archivePath %s -exportPath %s -exportOptionsPlist %s" %(archivePath,exportDirectory,EXPORT_OPTIONS_PLIST)
    process = subprocess.Popen(exportCmd, shell=True)
    (stdoutdata, stderrdata) = process.communicate()
    
    signReturnCode = process.returncode
    if signReturnCode != 0:
        print "export %s failed" %(scheme)
        return ""
    else:
        return exportDirectory
#run1 archive->ipa
def buildProject(project, scheme):
	archivePath = buildArchivePath(scheme)
	print "archivePath: " + archivePath
	archiveCmd = 'xcodebuild archive -project %s -scheme %s -configuration %s -archivePath %s -destination generic/platform=iOS' %(project, scheme, CONFIGURATION, archivePath)
	process = subprocess.Popen(archiveCmd, shell=True)
	process.wait()

	archiveReturnCode = process.returncode
	if archiveReturnCode != 0:
		print "archive project %s failed" %(project)
		cleanArchiveFile(archivePath)
	else:
		exportDirectory = exportIpa(scheme, project)
		cleanArchiveFile(archivePath)
		if exportDirectory != "":		
			ipaPath = getIpaPath(exportDirectory)
			uploadIpaToPgyer(ipaPath)

#run2 archive->ipa
def buildWorkspace(workspace, scheme):
    archivePath = buildArchivePath(scheme)
    print "archivePath: " + archivePath
    if os.path.exists(archivePath):
        archiveCmd = 'xcodebuild clean -workspace %s -scheme %s'%(workspace, scheme)
        process = subprocess.Popen(archiveCmd, shell=True)
        process.wait()
        archiveReturnCode = process.returncode
    else:
        archiveCmd = 'xcodebuild archive -workspace %s -scheme %s -configuration %s -archivePath %s -destination generic/platform=iOS' %(workspace, scheme, CONFIGURATION, archivePath)
        process = subprocess.Popen(archiveCmd, shell=True)
        process.wait()
        archiveReturnCode = process.returncode
    if archiveReturnCode != 0:
        print "archive workspace %s failed" %(workspace)
        #cleanArchiveFile(archivePath)
    else:
        print "\nTime-Archive:%s s"%(datetime.now()-starttime).seconds
        exportDirectory = exportIpa(scheme, archivePath)
        #cleanArchiveFile(archivePath)
        if exportDirectory != "":
            ipaPath = getIpaPath(exportDirectory)
            uploadIpaToPgyer(ipaPath)


def xcbuild(options):
	project = options.project
	workspace = options.workspace
	scheme = options.scheme
	desc = options.desc
	
	global PGYDESC
	PGYDESC = desc

	if project is None and workspace is None:
		pass
	elif project is not None:
		buildProject(project, scheme)
	elif workspace is not None:
		buildWorkspace(workspace, scheme)

def main():
	
	parser = argparse.ArgumentParser()
	parser.add_argument("-w", "--workspace", help="Build the workspace name.xcworkspace.", metavar="name.xcworkspace")
	parser.add_argument("-p", "--project", help="Build the project name.xcodeproj.", metavar="name.xcodeproj")
	parser.add_argument("-s", "--scheme", help="Build the scheme specified by schemename. Required if building a workspace.", metavar="schemename")
	parser.add_argument("-m", "--desc", help="Pgyer update description.", metavar="description")
	options = parser.parse_args()

	print "options: %s" % (options)

	xcbuild(options)

if __name__ == '__main__':
    #setup()
        main()
        print "\nTime-Total:%s s"%(datetime.now()-starttime).seconds
