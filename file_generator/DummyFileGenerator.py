from dataclasses import dataclass
import os
from pathlib import Path
import logging
import time
import hashlib
import numpy as np

@dataclass(frozen=True, eq=True)
class FileWriterConfig:
    """
    Configuration for file writing.
    
      output_dir : Path - The directory where files will be written.
      chunk_size : int - number of bytes in each chunk to be written
      semaphore : str - The name of the semaphore file used to 
                        indicate that file is ready for transfer
      write_interval : float - The interval in seconds between write 
                               operations.
    """
    output_dir: Path
    chunk_size: int 
    semaphore: str
    write_interval: float


@dataclass(frozen=True, eq=True)
class PatientConfig:
    """
    Configuration for patient data.
    
      id : int - The unique identifier for the patient.
      surname : str - The surname of the patient.
      name : str - The first name of the patient.
      birth_date : str - The birth date of the patient in YYYY-MM-DD format.
    """
    id: int
    surname: str
    name: str
    birth_date: str


class DummyFileGenerator:
    """
    A dummy file generator that simulates app writing files to a given location
    for further transfer to a remote location 
    
    Attributes:
        file_writer_config (FileWriterConfig): Configuration for file writing.
        patient_config (PatientConfig): Configuration for patient data.
    """
    
    def __init__(self,
                 file_writer_config: FileWriterConfig, 
                 patient_config: PatientConfig,
                 printlevel = logging.DEBUG,
                 loglevel = logging.INFO,
                 logfile = None
):
        log_format = logging.Formatter('%(asctime)s %(levelname)s:%(name)s %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(min(printlevel, loglevel))
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_format)
        stream_handler.setLevel(printlevel)
        self.logger.addHandler(stream_handler)
        ## writing to file if logfile is provided
        if logfile:
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(log_format)
            file_handler.setLevel(loglevel)
            self.logger.addHandler(file_handler)
            self.logger.info(f"Logging to file: {logfile}")
        
        self.logger.info(f"Initializing DummyFileGenerator")
        self.logger.info(f"Writer config: {file_writer_config}")
        self.logger.info(f"Patient config: {patient_config}")

        self.file_writer_config = file_writer_config
        self.patient_config = patient_config
        self.start_time = int(time.time()*1000) 
        self.cur_file = 0
        self.file_prefix = self.generate_prefix()
        
    def generate_prefix(self) -> str:
        """
        Generates a prefix based on the patient data and start time
        """
        _userstr = f"{self.patient_config.id}_"\
                   f"{self.patient_config.surname}_"\
                   f"{self.patient_config.name}_"\
                   f"{self.patient_config.birth_date}_"\
                   f"{self.start_time}"
        _sha1_hash = hashlib.sha1(_userstr.encode('utf-8'))
        _prefix = "df_"+_sha1_hash.hexdigest()[-8:]
        self.logger.info(f"Generated file prefix: {_prefix}")
        return _prefix

    def generate_file(self):
        """
        Simulates the generation of a file based on the provided configurations.
        This method would contain the logic to write data to a file in chunks,
        respecting the write interval and creating a semaphore file when done.
        """
        _data = np.random.bytes(self.file_writer_config.chunk_size*1000)
        _outfile_path = os.path.join( self.file_writer_config.output_dir,
                                      f"{self.file_prefix}_{self.cur_file}.dat")
        # this should not happen given that we 
        if os.path.exists(_outfile_path):
            self.logger.warning(f"File {_outfile_path} already exists, adding extra suffix")
            _outfile_path = os.path.join( self.file_writer_config.output_dir,
                                         f"{self.file_prefix}_dupl_{self.cur_file}.dat")
        # writing junk to file
        with open(_outfile_path, 'wb') as f:
            f.write(_data)
            self.logger.info(f"Wrote {self.file_writer_config.chunk_size} KB to {_outfile_path}")
        
        # adding semaphore file to indicate that file is ready for transfer
        if self.file_writer_config.semaphore:
            _semaphore_path = _outfile_path + self.file_writer_config.semaphore
            with open(_semaphore_path, 'w') as sem_file:
                sem_file.write("")
                self.logger.info(f"Created semaphore file {_semaphore_path}")
        
        self.cur_file += 1

    def write_files(self):
        """
        Continuously generates files at the specified write interval.
        This method will run indefinitely until interrupted.
        """
        self.logger.info("Starting file generation loop.")
        try:
            while True:
                self.generate_file()
                self.logger.debug(f"Sleeping for {self.file_writer_config.write_interval} seconds.")
                time.sleep(self.file_writer_config.write_interval)
        except KeyboardInterrupt:
            self.logger.info("File generation interrupted by user.")