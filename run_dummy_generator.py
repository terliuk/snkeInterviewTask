#!/usr/bin/env python

if __name__ == "__main__":
    from file_generator import FileWriterConfig, PatientConfig, DummyFileGenerator
    import logging 
    import argparse
    import json 
    import os
    from pathlib import Path
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filegenconfig", type=str, dest = "FILEGENCONFIG", required=True,
                        help="path to the JSON file generator configuration file")
    parser.add_argument("-p", "--patientconfig", type=str, dest = "PATIENTCONFIG", required=True,
                        help="path to the JSON patient configuration file")
    args = parser.parse_args()
    ## ToDo - probably move json handlers soemwhere to make it more reusable
    patient_config_path = args.PATIENTCONFIG
    if patient_config_path is None or not os.path.isfile(patient_config_path):
        raise ValueError(f"Invalid patient configuration file path: {patient_config_path}")
    patient_config = None
    with open(patient_config_path, "r") as f:
        patient_config_dict = json.load(f)
        patient_config = PatientConfig(
            id = patient_config_dict.get("id"),
            surname = patient_config_dict.get("surname"),
            name = patient_config_dict.get("name"),
            birth_date = patient_config_dict.get("birth_date")
        )
    ## 
    filegen_config_path = args.FILEGENCONFIG
    if filegen_config_path is None or not os.path.isfile(filegen_config_path):
        raise ValueError(f"Invalid file generator configuration file path: {filegen_config_path}")
    filegen_config = None
    with open(filegen_config_path, "r") as f:
        filegen_config_dict = json.load(f)
        file_writer_config = FileWriterConfig(
            output_dir = Path(filegen_config_dict.get("output_dir")),
            chunk_size = filegen_config_dict.get("chunk_size"),
            semaphore_ext = filegen_config_dict.get("semaphore"),
            write_interval = filegen_config_dict.get("write_interval")
        )

    writer = DummyFileGenerator(file_writer_config=file_writer_config, 
                                patient_config=patient_config,
                                logfile = "dummy_generator.log",
                                printlevel=logging.INFO,
                                loglevel=logging.INFO)
    writer.write_files()