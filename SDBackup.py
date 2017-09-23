import os
import pygtk
import gtk
import gobject
import threading
import time
import shutil
from subprocess import check_output,CalledProcessError

pygtk.require('2.0')

class CloudBackupApp:

  class BackupJob(threading.Thread):
    def __init__(self, type, fileList, outDir):
      self.stopthread = threading.Event()
      self.operationType = type
      self.fileCursor = 0
      self.errorCount = 0
      self.fileList = fileList
      self.outDir = outDir
      super(CloudBackupApp.BackupJob,self).__init__()

    def run(self):
      while self.backupNext():
        pass
        
    def backupNext(self):
      file = self.fileList[self.fileCursor]
    
      try:
        if self.operationType == 'copy':
          print 'Copy {}: ''{}'' --> {}/{}'.format(file[0],file[1],self.outDir,file[1])
          shutil.copy(file[2],self.outDir)
        if self.operationType == 'move':
          print 'Move {}: ''{}'' --> {}/{}'.format(file[0],file[1],self.outDir,file[1])
          shutil.move(file[2],self.outDir)
      except Exception, e:
        print 'Backup failed with error: {}'.format(str(e))
        self.errorCount += 1
      self.fileCursor += 1
      if self.fileCursor >= len(self.fileList):
        return False
      else:
        return True

    def stop(self):
      self.stopthread.set()

  class SyncJob(threading.Thread):
    def __init__(self):
      self.status = 'Checking status...'
      self.stopthread = threading.Event()
      super(CloudBackupApp.SyncJob,self).__init__()

    def run(self):
      while self.checkSync():
        time.sleep(0.25)
        pass

    def checkSync(self):
      try:
        self.status = check_output(['/home/pi/.odrive-agent/bin/odrive','status','--uploads'])
        if self.status == 'No uploads.\n':
          return False
        else:
          return True
      except CalledProcessError,e:
        return False

    def stop(self):
      self.stopthread.set()

  def __init__(self):
    self.inDir = '/media/pi/disk'
    self.outDir = '/media/pi/EXT-SSD/odrive'
    self.fileCursor = 0
    self.fileList = self.fileScan(self.inDir)
    self.initialDraw()

  def initialDraw(self):      
    gtk.threads_enter()
    self.window = gtk.Window()
    self.window.set_title('SDBackup')
    self.window.set_default_size(400,200)
    self.window.set_position(gtk.WIN_POS_NONE)
    self.window.set_border_width(3)
    self.window.connect('destroy', self.quit)
    self.vboxLeft = gtk.VBox(False, 0)
    self.window.add(self.vboxLeft)
    self.vboxLeft.show()
    self.hboxTop = gtk.HBox(False, 0)
    self.vboxLeft.add(self.hboxTop)
    self.hboxTop.show()
    self.lblInDir = gtk.Label("Source:")
    self.hboxTop.pack_start(self.lblInDir, False, False, 5)
    self.lblInDir.show()
    self.txtInDir = gtk.Entry()
    self.txtInDir.set_text(self.inDir)
    self.hboxTop.pack_start(self.txtInDir, True, True, 0)
    self.txtInDir.show()
    self.hboxBot = gtk.HBox(False, 0)
    self.vboxLeft.pack_start(self.hboxBot, True, True, 0)
    self.hboxBot.show()
    self.lblOutDir = gtk.Label("Destination:")
    self.hboxBot.pack_start(self.lblOutDir, False, False, 5)
    self.lblOutDir.show()
    self.txtOutDir = gtk.Entry()
    self.txtOutDir.set_text(self.outDir)
    self.hboxBot.pack_start(self.txtOutDir, True, True, 0)
    self.txtOutDir.show()
    self.hboxFiles = gtk.HBox(False, 0)
    self.hboxFiles.set_size_request(-1, 25)
    self.vboxLeft.add(self.hboxFiles)
    self.hboxFiles.show()
    self.lblFileCount = gtk.Label('{} files found'.format(str(len(self.fileList))))
    self.hboxFiles.pack_start(self.lblFileCount, True, True, 0)
    self.lblFileCount.show() 
    self.btnRefresh = gtk.Button('Refresh')
    self.btnRefresh.connect('clicked', self.btnRefreshOnClick)
    self.hboxFiles.pack_start(self.btnRefresh, False, True, 3)
    self.btnRefresh.show()
    self.btnCopy = gtk.Button('Copy')
    self.btnCopy.connect('clicked', self.btnCopyOnClick)
    self.hboxFiles.pack_start(self.btnCopy, False, True, 3)
    self.btnCopy.show()
    self.btnMove = gtk.Button('Move')
    self.btnMove.connect('clicked', self.btnMoveOnClick)
    self.hboxFiles.pack_start(self.btnMove, False, True, 3)
    self.btnMove.show()
    self.btnSync = gtk.Button('Sync')
    self.btnSync.connect('clicked', self.btnSyncOnClick)
    self.hboxFiles.pack_start(self.btnSync, False, True, 3)
    self.btnSync.show()
    self.window.show()
    gtk.threads_leave()

  def refreshDirs(self):
    self.inDir = self.txtInDir.get_text()
    self.fileList = self.fileScan(self.inDir)      
    self.lblFileCount.set_text('{} files found'.format(str(len(self.fileList))))
    self.outDir = self.txtOutDir.get_text()

  def btnRefreshOnClick(self, widget, data = None):
    self.refreshDirs()

  def btnCopyOnClick(self, widget, data = None):
    self.refreshDirs()
    self.startBackup('copy')

  def btnMoveOnClick(self, widget, data = None):
    self.refreshDirs()
    self.startBackup('move')

  def btnSyncOnClick(self, widget, data = None):
    if self.checkCloudStatus()[0] <> 0:
      self.drawCloudConnect()
    else:
      self.syncMonitor()

  def checkCloudStatus(self):
    try:
      status = check_output(['/home/pi/.odrive-agent/bin/odrive','status'])
      return (0, status)
    except CalledProcessError,e:
      return (e.returncode, e.output)

  def drawCloudConnect(self):
    dialog = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 'Connect to Cloud?')
    response = dialog.run()
    dialog.destroy()
    if response == gtk.RESPONSE_NONE or response == gtk.RESPONSE_NO:
      pass
    if response == gtk.RESPONSE_YES:
      try:
        print 'Starting odrive-agent at user request:'
        print check_output(['/home/pi/odrive/odrive-start'])
      except CalledProcessError,e:
        print 'odrive-agent failed to launch:'
        print e.output
        dialog = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, 'Could not connect to cloud!')
        dialog.run()
        dialog.destroy()
        return False
      self.syncMonitor()

  def syncMonitor(self):
    self.syncJob = self.SyncJob()
    self.syncJob.start()
    self.drawSyncWindow()
    while self.syncJob.isAlive():
      while gtk.events_pending():
        gtk.main_iteration(False)
      time.sleep(0.25)
      self.syncUpdate()
    self.syncComplete()

  def startBackup(self, type):
    self.job = self.BackupJob(type, self.fileList, self.outDir)
    self.job.start()
    self.drawProgressWindow()
    while self.job.isAlive():
      while gtk.events_pending():
        gtk.main_iteration(False)
      time.sleep(0.25)
      self.progressUpdate()
      
    self.progressComplete()

  def progressUpdate(self):
    if not self.job.isAlive():
      return False
    if self.job.operationType == 'move':
      verb = 'mov'
    else:
      verb = 'copy'
    self.lblStatus.set_text('{}ing {} ''{}'' to {}...'.format(verb.title(),self.fileList[self.job.fileCursor][0],self.fileList[self.job.fileCursor][1],self.outDir))
    self.progressBar.pulse()
    return True

  def syncUpdate(self):
    if not self.syncJob.isAlive():
      return False
    self.lblSyncStatus.set_text(self.syncJob.status)
    return True

  def progressComplete(self):
    if self.job.operationType == 'move':
      verb = 'mov'
    if self.job.operationType == 'copy':
      verb = 'copi'
    self.lblStatus.set_text('Finished with {} errors: {}ed {} files from {} to {}'.format(self.job.errorCount,verb,str(len(self.fileList)),self.inDir,self.outDir))      
    self.btnCancel.set_label('Close')
    self.progressBar.set_fraction(1.0)

  def syncComplete(self):
    self.lblSyncStatus.set_text('No active uploads.')

  def drawProgressWindow(self):
    self.progressWindow = gtk.Window()
    if self.job.operationType == 'move':
      verb = 'mov'
    else:
      verb = 'copy'
    self.progressWindow.set_title('{}ing {} files to {}...'.format(verb.title(),str(len(self.fileList)),self.outDir))
    self.progressWindow.connect('destroy', self.cancelOperation)
    self.progressWindow.set_default_size(300,100)
    self.progressWindow.set_position(gtk.WIN_POS_NONE)
    self.progressWindow.set_border_width(3)
    self.progressVBox = gtk.VBox(False, 0)
    self.progressWindow.add(self.progressVBox)
    self.progressVBox.show()
    self.lblStatus = gtk.Label("Starting {}...".format(self.job.operationType))
    self.progressVBox.pack_start(self.lblStatus, True, True, 0)
    self.lblStatus.show()
    self.progressBar = gtk.ProgressBar()
    self.progressVBox.pack_start(self.progressBar, True, True, 0)    
    self.progressBar.show()
    self.progressWindow.show()
    self.btnCancel = gtk.Button('Cancel {}'.format(self.job.operationType.title()))
    self.btnCancel.connect('clicked', self.cancelOperation)
    self.progressVBox.pack_start(self.btnCancel, False, True, 3)
    self.btnCancel.show()
    self.progressWindow.show()

  def cancelOperation(self, widget, data = None):
    self.job.stop()
    self.progressWindow.destroy()

  def drawSyncWindow(self):
    self.syncWindow = gtk.Window()
    self.syncWindow.set_title('Sync Status')
    self.syncWindow.connect('destroy', self.cancelSync)
    self.syncWindow.set_default_size(300,100)
    self.syncWindow.set_position(gtk.WIN_POS_NONE)
    self.syncWindow.set_border_width(3)
    self.syncVBox = gtk.VBox(False, 0)
    self.syncWindow.add(self.syncVBox)
    self.syncVBox.show()
    self.lblSyncStatus = gtk.Label('Checking sync status...')
    self.syncVBox.pack_start(self.lblSyncStatus, True, True, 0)
    self.lblSyncStatus.show()
    self.btnClose = gtk.Button('Close')
    self.btnClose.connect('clicked', self.cancelSync)
    self.syncVBox.pack_start(self.btnClose, False, True, 3)
    self.btnClose.show()
    self.syncWindow.show()

  def cancelSync(self, widget, data = None):
    self.syncJob.stop()
    self.syncWindow.destroy()

  def fileScan(self, searchDir):
    objList = []
    for dirname, dirnames, filenames in os.walk('{}/DCIM/100MSDCF'.format(searchDir)):
      for filename in filenames:
        objList.append(['image',filename,dirname+'/'+filename])
    for dirname, dirnames, filenames in os.walk('{}/MP_ROOT/100ANV01'.format(searchDir)):
      for filename in filenames:
        objList.append(['video',filename,dirname+'/'+filename])
    for dirname, dirnames, filenames in os.walk('{}/PRIVATE/AVCHD/BDMV/STREAM'.format(searchDir)):
      for filename in filenames:
        objList.append(['video',filename,dirname+'/'+filename])
    
    return objList

  def quit(self, widget, data = None):
    gtk.main_quit()

  def main(self):
    gtk.main()

if __name__ == '__main__':
  app = CloudBackupApp()
  app.main()
