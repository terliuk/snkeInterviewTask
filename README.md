# Snke technical task

Interview task for Advanced Software Developer. 

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
### Helper apps

In order to facilitate development and debugging, two separate programs / scripts were written:
* CGI script on remote web server (runs apache2)
* Dummy file generator

#### Dummy file generator

#### Remote web server 
