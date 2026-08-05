#!/usr/bin/env python

from file_generator import FileWriterConfig, PatientConfig, DummyFileGenerator
import logging 

patient_config = PatientConfig(id=12, surname="Doe", name="John", birth_date="1964-12-31")
file_writer_config = FileWriterConfig(
          output_dir="/home/terliuk/interview_task/snkeAdvanced/data_files/", 
          chunk_size=10000, semaphore=".sem", write_interval=10.0)

writer = DummyFileGenerator(file_writer_config=file_writer_config, 
                            patient_config=patient_config,
                            logfile = "dummy_generator.log",
                            printlevel=logging.WARNING,
                            loglevel=logging.DEBUG)
writer.write_files()