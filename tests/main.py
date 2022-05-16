import glob
import sys
import os
import importlib
import unittest

def main():

    # go to the right folder
    folder = os.getcwd().split(os.sep)
    while folder[-1] != "ploupy-back":
        folder.pop()
    sys.path.append(os.sep.join(folder))
    
    files = glob.glob("tests/**/*.py")
    tests = []

    for file in files:
        # remove file extension
        file = file[:-3]
        path = file.split(os.sep)
        
        test = importlib.import_module(".".join(path))
        tests.append(test)
        
        # run test
        suite = unittest.loader.findTestCases(test)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

if __name__ == "__main__":
    main()
    