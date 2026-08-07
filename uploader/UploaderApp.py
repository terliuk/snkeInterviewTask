from dataclasses import dataclass
from pathlib import Path
import logging
import requests
from enum import Enum
from time import time, sleep
import hashlib
import shutil
from copy import deepcopy

class UploadState(Enum):
    IDLE         = 0
    STAGE        = 1
    NEXTFILE     = 2
    UPLOAD       = 3
    VERIFY       = 4 
    REMOVELOCAL  = 5
    WAIT         = 6
    REMOVEREMOTE = 7

@dataclass(frozen=True)
class UploadConfig:
    source_dir: Path
    trash_dir: Path | None
    destination_url: str
    semaphore_ext: str | None = None

class UploaderApp:
    def __init__( self, 
                  config: UploadConfig, 
                  user = "", 
                  password = "",
                  printlevel = logging.DEBUG,
                  loglevel = logging.INFO,
                  logfile = None):
        """
        Initialize the UploaderApp with the given configuration, 
        user credentials, and logging settings.
        
        :param config: UploadConfig object containing source_dir, 
                       trash_dir, destination_url, and semaphore_ext.
        :param user: Username for authentication (optional).
        :param password: Password for authentication (optional).
        :param printlevel: Logging level for console output 
                           (default: logging.DEBUG).
        :param loglevel: Logging level for file output 
                         (default: logging.INFO).
        :param logfile: Path to the log file (optional).
        """
        from .MakeLogger import MakeLogger
        self.logger = MakeLogger(name = __name__,
                                 printlevel = printlevel,
                                 loglevel = loglevel,
                                 logfile = logfile)
        self.config = config
        self.logger.info(f"UploaderApp config: {self.config}")

        # dealing with authentication to remote
        self.user = deepcopy(user)
        self._auth_cmd = None
        if self.user and password:
            self._auth_cmd = (self.user, deepcopy(password))
            self.logger.info(f"UploaderApp user: {self.user}")
        else:
            self.logger.warning("UploaderApp initialized without user credentials. "
                                "Uploads may fail if authentication is required.")
        # files that were staged
        self.staged_files = []

        # temporary variables to hold info about current file
        self.state = UploadState.IDLE
        self._cur_file_sha256 = None

        # timer to control wait time
        self.timer = time()
        self.wait_interval = 2.0

    def process(self):
      """
      Main processing loop for the uploader application.
      This method implements a state machine to manage the upload process.
      """
      # no python 3.10+ is guaranteed, so using if-elif ladder
      if self.state == UploadState.IDLE:
          self.state = UploadState.WAIT
      
      elif self.state == UploadState.WAIT:
          # checking whether we waited long enough
          if time() - self.timer > self.wait_interval:
              self.logger.debug(f"Waited {self.wait_interval} seconds, moving to STAGE state.")
              self.timer = time()
              self.state = UploadState.STAGE
          sleep(0.1) # prevent too many calls to time / CPU
      
      elif self.state == UploadState.STAGE:
          # staging files for upload
          self.stage_files()
          if len(self.staged_files) > 0:
              self.state = UploadState.NEXTFILE
          else:
              self.state = UploadState.WAIT

      elif self.state == UploadState.NEXTFILE:
          # retrieving next file to upload
          if len(self.staged_files) == 0: 
              self.logger.debug("No more files to upload, returning to WAIT state.")
              self.state = UploadState.WAIT
          else:
              self.current_file = self.staged_files.pop(0)
              self.logger.debug(f"Processing file: {self.current_file}")
              self.state = UploadState.UPLOAD

      elif self.state == UploadState.UPLOAD:
          # uploading the current file
          self.upload_file(self.current_file)
          self.state = UploadState.VERIFY

      elif self.state == UploadState.VERIFY:
          # verifying the uploaded file
          if self.verify_file(self.current_file):
              self.state = UploadState.REMOVELOCAL
          else:
              # Skip to next file on verification failure, we can return to it later
              self.logger.error(f"Verification failed for file: {self.current_file}")
              self.state = UploadState.REMOVEREMOTE
              self.staged_files.append(self.current_file) # re-stage for later upload

      elif self.state == UploadState.REMOVEREMOTE:
          self.remove_remote_file(self.current_file)
          self.state = UploadState.NEXTFILE

      elif self.state == UploadState.REMOVELOCAL:
          self.remove_file(self.current_file)
          self.state = UploadState.NEXTFILE

    def run(self):
        """
        Run the uploader application in a loop until interrupted.
        """
        self.logger.info("UploaderApp started. Press Ctrl+C to stop.")
        try:
            while True:
                self.process()
        except KeyboardInterrupt:
            self.state = UploadState.IDLE
            self.logger.info("UploaderApp stopped by user.")

    def stage_files(self):
        """
        Check for files in the source directory that are ready for upload.
        A file is considered ready if it has a corresponding semaphore file.
        """
        _all_files = sorted([f_ for f_ in self.config.source_dir.glob(
                            ("*"+self.config.semaphore_ext) if self.config.semaphore_ext else "*")])

        if len(_all_files) == 0:
            self.logger.debug(f"No files for upload yet: {self.config.source_dir}")
            return
        # strip semaphore extension - we want to upload only the data files
        # if no semaphore extension - transfer all files 
        if self.config.semaphore_ext: 
            self.logger.debug(f"Stripping semaphore extension "\
                              f"'{self.config.semaphore_ext}' from files")
            _all_files = [f_.with_suffix("") for f_ in _all_files ]

        for f_ in _all_files:
            if f_.is_file():
                self.logger.info(f"Staged for upload: {f_}")
                self.staged_files.append(f_)
                continue
            self.logger.warning(f"Not a file, skipping: {f_}")

    def upload_file(self, file_path : Path):
        """
        Upload a single file to the destination URL.
        """
        self.logger.info(f"Uploading file: {file_path}")
        ### checking if remote file exists
        headers = {'X-Filename': file_path.name}
        response = requests.head(self.config.destination_url, 
                                 headers = headers,
                                 auth=self._auth_cmd)
        self.logger.debug(f"HEAD request response: {response.status_code} "\
                          f"for file: {file_path}")

        self._cur_file_sha256 = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
        ## 
        header = {'Content-Type': 'application/octet-stream',
                  'Content-Length': str(file_path.stat().st_size),
                  'X-Checksum-SHA256': self._cur_file_sha256,
                  'X-Filename': file_path.name}
        
        if response.status_code == 404:
            self.logger.info(f"Remote is emtpy, uploading: {file_path}")        
            with open(file_path, 'rb') as f:
                response = requests.post(self.config.destination_url,
                                          data=f,
                                          headers=header,
                                          auth=self._auth_cmd)
            self.logger.debug(f"POST request response: {response.status_code}"\
                              f" text {response.text}")
        elif ((response.status_code == 200) and 
              (response.headers.get("X-Checksum-SHA256","") != self._cur_file_sha256)):
            self.logger.warning(f"Remote file with different checksum "\
                                f", overwriting: {file_path}")
            with open(file_path, 'rb') as f:
                response = requests.put(self.config.destination_url,
                                         data=f,
                                         headers=header,
                                         auth=self._auth_cmd)
            self.logger.debug(f"PUT request response: {response.status_code} "\
                              f"text {response.text}")
        elif ((response.status_code == 200) and
              (response.headers.get("X-Checksum-SHA256","") == self._cur_file_sha256)):
            self.logger.info(f"Remote exists with matching checksum"\
                             f", skipping upload: {file_path}")
        else:
            self.logger.warning(f"Got unexpected response: {response.status_code} "\
                                f"text {response.text} for file: {file_path}")
    
    def verify_file(self, file_path : Path):
        """
        Verify that the file was uploaded successfully.
        """
        headers = {'X-Filename': file_path.name}
        response = requests.head(self.config.destination_url,
                                  headers = headers,
                                  auth=self._auth_cmd)
        self.logger.debug(f"HEAD request response: {response.status_code} for file: {file_path.name}")
        if response.status_code != 200:
            self.logger.error(f"Verification failed, remote file not found: {file_path.name}")
            return False
        remote_checksum = response.headers.get("X-Checksum-SHA256")

        if remote_checksum != self._cur_file_sha256:
            self.logger.warning(f"Verification failed, checksum mismatch for: {file_path.name}.")
            self.logger.debug(f"Local: {self._cur_file_sha256}, Remote: {remote_checksum}")
            return False
        self.logger.info(f"Verification successful for: {file_path.name}")
        return True
        
    def remove_file(self, file_path : Path):
        """
        Remove the file from the source directory after successful upload.
        """
        self._remove_one_file(file_path)

        if self.config.semaphore_ext:
            sem_file = file_path.with_suffix(file_path.suffix+self.config.semaphore_ext)
            self._remove_one_file(sem_file)
    
    def _remove_one_file(self, file_path : Path):
        """
        Remove a single file from the source directory.
        """
        if not file_path.exists():
            self.logger.warning(f"File not found for removal: {file_path}")
            return
        if self.config.trash_dir:
            trash_path = self.config.trash_dir / file_path.name
            shutil.move(file_path, trash_path)
            self.logger.debug(f"Moved file to trash: {trash_path}")
        else:
            self.logger.debug(f"Removing file: {file_path}")
            file_path.unlink()

    def remove_remote_file(self, file_path : Path):
        """
        Remove the file from the remote destination.
        """
        headers = {'X-Filename': file_path.name}
        response = requests.delete(self.config.destination_url,
                                   headers = headers,
                                   auth=self._auth_cmd)
        self.logger.debug(f"DELETE request response: {response.status_code}"\
                          f" for file: {file_path.name}")
        if response.status_code == 200:
            self.logger.info(f"Remote file deleted successfully: {file_path.name}")
        elif response.status_code == 404:
            self.logger.warning(f"Remote file not found for deletion: {file_path.name}")
        else:
            self.logger.error(f"Failed to delete remote file: {file_path.name}. "
                              f"Response code: {response.status_code}, text: {response.text}")
        
