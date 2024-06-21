import csv
from collections import defaultdict


def group_by_gtin(csv_file):
    groups = defaultdict(list)
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        for row_ in reader:
            first_element = row_[0]
            if isinstance(first_element, str): # and has_x1d_before_91_92(first_element):
                substring_ = first_element[2:16]
                groups[substring_].append(row_)
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
        csv_reader = csv.reader(csv_file, delimiter='|')
        long_strings = [row[0] for row in csv_reader]

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
                joined_string = f"{long_string}|{value1}|{value2}|{value3}|{value4}|{value5}|{value6}|{value7}|" \
                                f"{value8}|{value9}"
                joined_strings.append(joined_string)
                break
        else:
            joined_strings.append(long_string)

    # Write the joined strings to the output CSV file
    with open(output_file_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        for joined_string in joined_strings:
            csv_writer.writerow(joined_string.split(','))


if __name__ == '__main__':
    # str = '0104620236343458215/FFUr)rA2i419100C292gEK2RSV7/UA09NiQlGA4YFxdmziUMFmNgCtNu+fsfHODHLsu97Plx0UyZeUkM5QC1Yak/j3w1PKh96nCwQ1hqg=='
    # print(has_x1d_before_91_92(str))

    res = group_by_gtin('/home/usr/PycharmProjects/matrix_tags/data/csv_sample_bigger.csv')
    print(res)
