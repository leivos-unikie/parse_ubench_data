# SPDX-FileCopyrightText: 2022-2024 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

import os
import csv
import pandas
import shutil

path_to_data = "/home/samuli/Desktop/test_tools/unixbench/results/Orin-NX"

# Dictionary defining locations where to extract each result value.
parse_config = [
    ('Dhrystone', 0, 'variables ', 'lps'),
    ('Whetstone', 0, 'Whetstone ', 'MWIPS'),
    ('Execl Throughput', 0, 'Throughput ', 'lps'),
    ('File Copy 1024', 0, 'maxblocks ', 'KBps'),
    ('File Copy 256', 0, 'maxblocks ', ' KBps'),
    ('File Copy 4096', 0, 'maxblocks ', 'KBps'),
    ('Pipe Throughput', 0, 'Throughput ', 'lps'),
    ('Context Switching', 0, 'Switching ', 'lps'),
    ('Process Creation', 0, 'Creation ', 'lps'),
    ('Shell Scripts (1 concurrent)', 0, ') ', 'lpm'),
    ('Shell Scripts (8 concurrent)', 0, ') ', 'lpm'),
    ('System Call Overhead', 0, 'Overhead ', ' lps')
]

# How many columns are reserved for information extracted from the file name
build_info_size = 1

def list_files(path, host):
    file_list = []
    for path, subdirs, files in os.walk(path):
        for name in files:
            if name.find(host) != -1 and name.find("csv") == -1 and name.find("html") == -1 and name.find("log") == -1:
                file_list.append(os.path.join(path, name))

    # file_list.sort(key=os.path.getctime)
    # The file creation time may differ from actual build date.
    # Let's sort according to file name (perf_results_YYYY-MM-DD_BuildMachine-BuildID) simply in ascending order.
    ordered_file_list = sorted(file_list)

    return ordered_file_list


def parse_build_info(filepath):
    # Expected file name format: ghaf-host-2024-04-15-01
    while "/" in filepath:
        filepath = filepath.split("/")[-1]

    i = [x.isdigit() for x in filepath].index(True)
    test_date = filepath[i:]
    build_info = [test_date]
    return build_info


def extract_value(file, threads, detect_str, offset, str1, str2):

    with open(file, 'r') as f:

        # read all lines using readline()
        lines = f.readlines()

        row_index = 0
        match_index = -1

        # When extracting multi-thread results cut the single-thread results away.
        # The line of cut depends on number of available threads.
        if threads == "multi":
            if "Lenovo-X1" in path_to_data or "Orin-AGX" in path_to_data:
                lines = lines[66:]
            if "Orin-NX" in path_to_data:
                lines = lines[58:]

        for row in lines:
            # find() method returns -1 if the value is not found,
            # if found it returns index of the first occurrence of the substring
            if row.find(detect_str) != -1:
                match_index = row_index
                break
            row_index += 1

        # print(match_index)

        if match_index < 0:
            print("Error in extracting '{}': Result value not found.".format(detect_str))
            return ''

        line = lines[match_index + offset]
        # print(line)
        res = ''

        try:
            # print(str1)
            # print(str2)
            # getting index of substrings
            idx1 = line.index(str1)
            idx2 = line.index(str2)
            # print(idx1)
            # print(idx2)

            # getting elements in between
            for idx in range(idx1 + len(str1), idx2):
                res = res + line[idx]

            res = float(res)
            # print("Extracting '{}': {}".format(detect_str, res))
            return res

        except:
            print("Error in extracting '{}': Result value not found.".format(detect_str))
            return res


def save_to_csv(file, config, csv_file_name, threads):

    results = parse_build_info(file)

    with open(path_to_data + "/" + csv_file_name, 'a') as f:

        writer_object = csv.writer(f)

        for i in range(len(config)):
            results.append(
                extract_value(file, threads, config[i][0], config[i][1], config[i][2], config[i][3])
            )
        # print(results)
        writer_object.writerow(results)
        f.close()


def calc_statistics(csv_file_name):
    data = pandas.read_csv(path_to_data + "/../" + csv_file_name)

    # Calculate column averages
    column_avgs = data.mean(numeric_only=True)
    print("Average for each column:")
    print(column_avgs)

    column_stds = data.std(numeric_only=True)
    print("Standard deviation for each column:")
    print(column_stds)

    column_min = data.min(numeric_only=True)
    print("Min for each column:")
    print(column_min)

    column_max = data.max(numeric_only=True)
    print("Max for each column:")
    print(column_max)

    avgs = column_avgs.tolist()[1:]
    stds = column_stds.tolist()[1:]
    min_values = column_min.tolist()[1:]
    max_values = column_max.tolist()[1:]

    data_rows = len(data.axes[0])
    # print(len(data.axes[1]))
    data_columns = len(avgs)

    # Detect significant deviations from column mean

    # Find the result which is furthest away from the column mean.
    # Not taking into account those results which are within 1 std from column mean.
    max_deviations = ['-'] * (data_columns + 4)
    for i in range(4, 4 + data_columns):
        for j in range(data_rows):
            if abs(data.iat[j, i] - avgs[i - 4]) > stds[i - 4]:
                distance = abs(data.iat[j, i] - avgs[i - 4]) / stds[i - 4]
                if max_deviations[i] == '-':
                    max_deviations[i] = distance
                elif distance > max_deviations[i]:
                    max_deviations[i] = distance

    # Check if values of the last data row are 1 std away from their column mean.
    last_row_deviations = ['-'] * (data_columns + 4)
    last_row_deviations[3] = "LRD"
    for i in range(4, 4 + data_columns):
        # if abs(data.iat[data_rows - 1, i] - avgs[i - 4]) > 3 * stds[i - 4]:
        if abs(data.iat[data_rows - 1, i] - avgs[i - 4]) > 0.2 * avgs[i - 4]:
            distance = data.iat[data_rows - 1, i] - avgs[i - 4] / stds[i - 4]
            last_row_deviations[i] = distance

    shutil.copyfile(path_to_data + "/../" + csv_file_name, path_to_data + "/../raw_" + csv_file_name)

    with open(path_to_data + "/" + csv_file_name, 'a') as f:

        writer_object = csv.writer(f)

        writer_object.writerow([])
        writer_object.writerow(last_row_deviations)
        writer_object.writerow(create_stats_row(3, "average", avgs))
        writer_object.writerow(create_stats_row(3, "std", stds))
        writer_object.writerow([])
        writer_object.writerow(create_stats_row(3, "max", max_values))
        writer_object.writerow(create_stats_row(3, "min", min_values))

        f.close()


def create_stats_row(shift, label, value_list):
    row = ['-'] * shift
    row.append(label)
    row = row + value_list
    return row


def normalize_columns(csv_file_name, normalize_to):
    # Set the various results to the same range.
    # This makes it easier to notice significant change in any of the result parameters with one glimpse
    # If columns are plotted later on the whole picture is well displayed

    data = pandas.read_csv(path_to_data + "/../" + csv_file_name)

    column_max = data.max(numeric_only=True)
    # print("Max for each column:")
    # print(column_max)
    # max_values = column_max.tolist()[1:]
    max_values = column_max

    data_rows = len(data.axes[0])
    # print(len(data.axes[1]))
    data_columns = len(max_values)

    # Normalize all columns between 0...normalize_to
    for i in range(build_info_size, build_info_size + data_columns):
        for j in range(data_rows):
            normalized = data.iat[j, i] / max_values[i - build_info_size]
            data.iloc[[j],[i]] = normalized * normalize_to
    data.to_csv(path_to_data + "/../" + "normalized_" + csv_file_name, index=False)


def create_csv_file(config, csv_file_name):

    header = ['test_date']
    for i in range(len(config)):
        header.append(config[i][0])

    with open(path_to_data + "/../" + csv_file_name, 'w') as f:
        writer = csv.writer(f, delimiter=',', lineterminator='\n')
        writer.writerow(header)
        f.close()


def data_to_csv_file(csv_file_name, host, threads="multi"):
    file_list = list_files(path_to_data, host)
    print("Going to extract result values from these files: ")
    print(file_list)
    print()

    create_csv_file(parse_config, csv_file_name)

    for f in file_list:
        save_to_csv(f, parse_config, "../" + csv_file_name, threads)

    normalize_columns(csv_file_name, 100)


def main():
    data_to_csv_file("ubench_ghaf-host_multi-thread.csv", "ghaf-host", "multi")
    data_to_csv_file("ubench_ghaf-host_1thread.csv", "ghaf-host", "single")
    data_to_csv_file("ubench_net-vm_1thread.csv", "net-vm", "single")

    # calc_statistics("ubench_ghaf-host_multi-thread.csv")
    # print()

if __name__ == '__main__':
    main()
