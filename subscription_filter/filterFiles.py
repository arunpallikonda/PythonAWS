import fnmatch
import math
import os
from itertools import islice
from os import path

from past.builtins import xrange

idc_file_path = '/Users/arun/IdeaProjects/PythonAWS/subscription_filter/files'
all_idc_subscription_files = fnmatch.filter(os.listdir(idc_file_path), '*_idc_subscription_*.txt')
number_of_files = len(all_idc_subscription_files)
contents_dict = {}
index = 1


def chunks(data, size):
    it = iter(data)
    for i in xrange(0, len(data), size):
        yield {k: data[k] for k in islice(it, size)}


for eachFile in all_idc_subscription_files:
    file_path = idc_file_path + '/' + eachFile
    if path.exists(file_path) and path.isfile(file_path):
        with open(file_path, 'r') as content_file:
            lines = content_file.read().splitlines()
            for eachLine in lines:
                if eachLine != '' and eachLine is not None:
                    contents_dict[eachLine.split('|')[0]] = eachLine
    os.rename(file_path, idc_file_path + '/' + eachFile.split('.')[0] + '_backup.txt')

print('No of contents per file: ' + str(math.ceil(len(contents_dict.values()) / number_of_files)))
for item in chunks(contents_dict, math.ceil(len(contents_dict.values()) / number_of_files)):
    file_pattern = '_idc_subscription_' + str(index) + '.txt'
    current_file = next((s for s in all_idc_subscription_files if file_pattern in s), None)
    print('Updating ' + current_file)
    line_counter = 1
    with open(idc_file_path + '/' + current_file, 'a+') as f:
        for eachValue in item.values():
            if line_counter == 1:
                f.write(eachValue)
            else:
                f.write('\n' + eachValue)
            line_counter += 1
    index += 1
