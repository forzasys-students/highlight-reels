import os

def verify_file(filename):
    return filename and os.path.exists(filename) and os.path.getsize(filename) > 0

name = 'README.md'

name = verify_file(name)

print(name)