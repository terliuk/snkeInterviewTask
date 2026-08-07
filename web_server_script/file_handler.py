#!/usr/bin/env python3
import hashlib
import os
import sys
from pathlib import Path

UPLOAD_DIR = Path("/var/www/html/upload")

def respond(status_line, headers=None, body=""):
    if headers is None:
        headers = {"Content-Type": "text/plain"}
    sys.stdout.write(f"Status: {status_line}\r\n")
    if headers:
        for key, value in headers.items():
            sys.stdout.write(f"{key}: {value}\r\n")
    sys.stdout.write("\r\n")
    if body:
        sys.stdout.write(f"{body}\r\n")

def main():
    # checking that filename exists
    filename = os.environ.get("HTTP_X_FILENAME", "")

    if not filename:
        respond("400 Bad Request", body = "400 Bad Request: missing HTTP_X_FILENAME header")
        return
    if (filename.find("/")  != -1 or
        filename.find("\\") != -1 or 
        filename.find("..") != -1 or 
        filename.find("~")  != -1 or 
        filename.find("*")  != -1 or 
        filename.find("?")  != -1 ):
        respond("400 Bad Request", body = "400 Bad Request: invalid filename")
        return
    # just because...
    if filename == "coffee.dat":
        respond("418 I'm a teapot", body = "418 I'm a teapot: coffee.dat is not allowed")
        return

    method = os.environ.get("REQUEST_METHOD", "")
    if method == "HEAD":
        head_get_func(filename, get=False)
    elif method == "GET":
        head_get_func(filename, get=True)
    elif method == "POST":
        post_func(filename)
    elif method == "PUT":
        post_func(filename, put=True)
    elif method == "DELETE":
        delete_func(filename)
        return
    elif method == "PATCH":
        respond("405 Method Not Allowed", body = "405 Method Not Allowed: PATCH is not allowed")
        return
    else:
        respond("405 Method Not Allowed", body = "405 Method Not Allowed")
        return

def delete_func(filename):
    """
    Handle a DELETE request to remove a file.
    """
    filename = os.path.basename(filename)
    dest_path = UPLOAD_DIR / filename
    if not dest_path.exists():
        respond("404 Not Found", body = f"File {filename} does not exist.")
        return
    try:
        dest_path.unlink()
        sha_file_path = dest_path.with_suffix(dest_path.suffix+".sha256")
        if sha_file_path.is_file():
            sha_file_path.unlink()
        respond("200 OK", body = f"File {filename} deleted successfully.")
    except Exception as e:
        respond("500 Internal Server Error", body = f"Error deleting file {filename}: {str(e)}")

def head_get_func(filename, get=False):
    """
    Handle a HEAD or GET request to check if a file exists.
    """    
    # checking whether file exists
    filename = os.path.basename(filename)
    dest_path = UPLOAD_DIR / filename
    if not dest_path.exists():
        respond("404 Not Found", body = f"File {filename} does not exist.")
        return
    sha_file_path = dest_path.with_suffix(dest_path.suffix+".sha256")
    if sha_file_path.is_file():
        with open(sha_file_path, "r") as f:
            sha256_checksum = f.read().strip()
    else:
        sha256_checksum = hashlib.sha256(open(dest_path, "rb").read()).hexdigest() #
    file_size = os.path.getsize(dest_path)
    header = {"Content-Type": "application/octet-stream",
              "Content-Length": str(file_size),
              "X-Content-Length": str(file_size),
              "X-Checksum-SHA256": sha256_checksum,
              "X-Filename": filename}
    respond("200 OK", headers = header)
    if get:
        with open(dest_path, "rb") as f:
            sys.stdout.flush()
            sys.stdout.buffer.write(f.read())

def post_func(filename, put=False):
    """
    Handle a POST or PUT request to upload a file
    """

    content_length = os.environ.get("CONTENT_LENGTH", 0)
    try:
        content_length = int(content_length)
    except ValueError:
        respond("400 Bad Request", body = "400 Bad Request: invalid CONTENT_LENGTH")
        return

    if content_length == 0:
        respond("400 Bad Request", body = "400 Bad Request: empty body")
        return
    body = sys.stdin.buffer.read(content_length)

    # checking whether file exists
    filename = os.path.basename(filename)
    dest_path = UPLOAD_DIR / filename
    if not put:
        # mimics inability of POST to overwrite existing files
        if dest_path.exists():
            respond("409 Conflict", body = f"409 Conflict: file {filename} already exists")
            return
    
    # checking checksums
    expected_checksum = os.environ.get("HTTP_X_CHECKSUM_SHA256")
    actual_checksum = hashlib.sha256(body).hexdigest()
    if expected_checksum and expected_checksum != actual_checksum:
        respond("400 Bad Request", 
                body = f"400 Bad Request: checksum mismatch, "\
                f"expected: {expected_checksum}, actual: {actual_checksum}," \
                f" content_length: {content_length}")
        return
    with open(dest_path, "wb") as f:
        f.write(body)
    with open(dest_path.with_suffix(dest_path.suffix+".sha256"), "w") as f:
        f.write(actual_checksum+"\r\n")
    if not put:
        body_ = f"File {filename} uploaded successfully"\
                f" to {dest_path}. Checksum: {actual_checksum}"
        respond("201 Created", body = body_)
    else:
        body_ = f"File {filename} overwritten successfully"\
                f" at {dest_path}. Checksum: {actual_checksum}"
        respond("200 OK", body = body_)

if __name__ == "__main__":
    main()

