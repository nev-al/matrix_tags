import csv
from collections import defaultdict
import logging
import time


logging.basicConfig(filename='logs.txt', filemode='a',
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)


def group_by_gtin(csv_file):
    groups = defaultdict(list)
    with open(csv_file, 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        for row in reader:
            first_element = row[0]
            if isinstance(first_element, str) and has_x1d_before_91_92(first_element):
                substring = first_element[2:16]
                groups[substring].append(row)
            else:
                print(f'csv_handler. incorrect data: {row[0]}')
                logger.error(f'{logger.parent.name} group_by_gtin. incorrect data: {row[0]}')
                
    return groups


def has_x1d_before_91_92(string):
    encoded_string = string.replace('\\x1d', '\x1d')
    if encoded_string.count('\x1d') != 2:
        return False
    r = [i for i in range(len(encoded_string)) if encoded_string.startswith('\x1d', i)]
    if encoded_string[r[0] + 1] + encoded_string[r[0] + 2] == '91' and encoded_string[r[1] + 1] + \
            encoded_string[r[1] + 2] == '92':
        return True
    else:
        return False


def join_strings(csv_file_path='/home/usr/PycharmProjects/matrix_tags/data/test/long_strings.csv',
                 txt_file_path='/home/usr/PycharmProjects/matrix_tags/data/test/short_strings.txt',
                 output_file_path='/home/usr/PycharmProjects/matrix_tags/data/test/output.csv'):
    # Open the CSV file and read the long strings
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='\t')
        long_strings = [row[0] for row in csv_reader if isinstance(row[0], str) and
                        has_x1d_before_91_92(row[0])]

    # Open the TXT file and read the shorter strings and values
    with open(txt_file_path, 'r') as txt_file:
        lines = txt_file.readlines()
        short_strings = []
        values = []
        for line in lines:
            parts = line.strip().split(',')
            short_strings.append(parts[0])
            values.append(tuple(parts[1:]))

    # Join the long strings with the values
    joined_strings = []
    for long_string in long_strings:
        for i, short_string in enumerate(short_strings):
            if short_string in long_string:
                value1, value2, value3, value4, value5, value6, value7, value8, value9 = values[i]
                joined_string = f"{long_string}\t{value1}\t{value2}\t{value3}\t{value4}\t{value5}\t{value6}\t{value7}\t" \
                                f"{value8}\t{value9}"
                joined_strings.append(joined_string)
                break

    # Write the joined strings to the output CSV file
    with open(output_file_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter='\t')
        for joined_string in joined_strings:
            csv_writer.writerow(joined_string.split('\t'))


def get_wrong_codes(csv_file_path) -> list:
    incorrect_codes = []
    with open(csv_file_path, 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        for i in reader:
            if not has_x1d_before_91_92(i[0]):
                incorrect_codes.append(i[0])
    return incorrect_codes


if __name__ == '__main__':
    # str = '0104620236343458215/FFUr)rA2i419100C292gEK2RSV7/UA09NiQlGA4YFxdmziUMFmNgCtNu+fsfHODHLsu97Plx0UyZeUkM5QC1Yak/j3w1PKh96nCwQ1hqg=='
    # print(has_x1d_before_91_92(str))

    # res = group_by_gtin('/home/usr/PycharmProjects/matrix_tags/data/csv_sample_bigger.csv')
    res = join_strings(csv_file_path='170141723.csv', txt_file_path='170141723.txt', output_file_path='out.csv')

    print(res)
