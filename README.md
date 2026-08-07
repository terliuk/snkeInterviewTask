# Snke technical task solution

by Andrii Terliuk
Interview task solution for Advanced Software Developer position at Snke. 


## Task
* Define constraints for handling sensitive patient data
* Edge device runs arm64/Linux system with apps generating writing files to local storage
* Remote server is HTTPS server that accepts `HEAD`, `GET`, `POST`, `PUT`, `PATCH` and `DELETE`
* Develop a prototype of upload application that uploads local files to remote and deletes them from local storage

## Solution 

### Constraints

The device is designed to handle sensitive patient data, what includes, but not limited to:
* name
* date of birth
* procedure
* date of procedure
* potential diagnosis
* ...

In order to avoid revealing these details to external parties, the following constraints can be implemented
* transfer via secure protocols (ssh/vpn/https)
* authentication is required for both upload and retrieval of files
* no information about patient and/or procedure should be visible in non-encrypted part:
  * domain name should be generic (`datahandling.net` - OK, `embarassingprocedure.medical.com` - not)
  * avoid open queries to servers (`datahandling.net/upload.php?surname=Doe&name=Joe&procedure=embarassing` - not good)
  * ideally avoid descriptive names like `data_Doe_embarrasing_000.dat` and best do some sort of hash `data_01a7eef_000.dat` with option of storing personal metadata inside, optionally with encryption or other access control layers

  
### Upload App

#### General idea

Upload App is written as a python class `uploader/UploaderApp.py` with a state machine with following states:
* `IDLE` - the process is not yet started or was interrupted
* `WAIT` - adds timeout between asking file system for files to avoid not necessary operations
* `STAGE` - read the list of files available in the folder, potentially with semaphore files to indicate that file is ready for transfer
* `NEXTFILE` - get the next file name to be transferred and compute its sha256 sum
* `UPLOAD` - check whether file exists using `HEAD` request:
  * if does not exist - upload using `POST` request
  * if exists - compare remote and local SHA256:
     * if identical - skip upload
     * if divergent - upload / replace file with `PUT` request
* `VERIFY` - verifies remote SHA256 to confirm that the file was correctly transferred (probably redundant)
* `REMOVELOCAL` - remove local file after successful upload (or move to trash), run if `VERIFY` is success
* `REMOVEREMOTE` - use `DELETE` requests to remove file from remote, run if `VERIFY` failed

Request `PATCH` was not used in the Upload App, since patch depends on details of how the data is generated. Given that files are expected to be removed from the local storage after successful upload, i do not expect that files will be modified after they are written. In principle, this can be implemented with more information about the data format is given. 


#### Example usage

In order to run the uploader, the helper script `run_upload_app.py` was implemented. Usage: 
```
python3 run_upload_app.py -c ./config/uploader_conf.json
```
Example of configuration file 
```
{
  "destination_url": "https://localhost:999/cgi-bin/file_handler.py",
  "source_dir" : "/home/terliuk/interview_task/snkeAdvanced/data_files/",
  "trash_dir" : "/home/terliuk/interview_task/snkeAdvanced/trash_data_files/",
  "semaphore_ext" : ".sem",
  "username": "dummyuser",
  "password": "dummypassword"
}
```
- `destination_url` - address of the remote server to upload files
- `source_dir` - local storage folder
- `trash_dir` - optional, if provided - files will be moved to trash folder instead of running unlink / remove command
- `semaphore_ext` - optional - if semaphore extension is provided, only files with existing semaphore file will be transferred
- `username` and `password` - authentication for remote server  

The uploader app supports writing and displaying logs with different levels of verbosity. 

### Helper apps

In order to facilitate development and debugging, two separate programs / scripts were written:
* CGI script on remote web server (runs apache2)
* Dummy file generator

#### Dummy file generator

A simple file generator `file_generator/DummyFileGenerator.py` was created to mimic regular file appearance. It takes JSONs for patient data to generate hashed file name. At pre-defined intervals, it writes random stream of bytes of a given size to output files and generates a semaphore file to indicate that the file is ready for transfer. 

Usage
```
python3 run_dummy_generator.py -f ./config/filegen_conf.json -p ./config/patient.json
```

#### Remote web server 

Remote web-server application was simulated by python CGI script provided in `web_server_script/file_handler.py`. 

It implements basic functionality of required `HEAD`, `GET`, `POST`, `PUT`, `DELETE` requests. The file handler is run on apache2 HTTPS werver with basic authentication procedure via httpspw.
