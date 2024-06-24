import glob
import shutil
import aiomultiprocess
from multiprocessing import cpu_count
import asyncio
import uuid
import csv
import zipfile
import os
from pathlib import Path
from PIL import Image
from pylibdmtx.pylibdmtx import decode
import subprocess
import logging
import time


logging.basicConfig(filename='logs.txt', filemode='a',
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)


async def handle_zip(zip_filepath, work_directory_path, csv_filepath):
    num_processes = cpu_count() * 3 // 4 if cpu_count() * 3 // 4 > 1 else 1
    logger.info(f'handle zip. vCPU count: {num_processes}')
    os.makedirs(work_directory_path, exist_ok=False)
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(work_directory_path)
    await convert_to_png_parallel(work_directory_path, num_processes)
    data = await decode_png_files_parallel(work_directory_path, num_processes)
    with open(csv_filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\')
        for key, value in sorted(data.items()):
            writer.writerow([value])
    delete_directory(work_directory_path)


async def convert_to_png(file_info):
    directory, file = file_info
    input_file = os.path.join(directory, file)
    output_file = os.path.join(directory, os.path.splitext(file)[0] + ".png")

    try:
        await asyncio.to_thread(subprocess.run, ["gs", "-dSAFER", "-dQUIET", "-dNOPAUSE", "-dBATCH", "-dEPSFitPage",
                                                 "-sDEVICE=pnggray", f"-sOutputFile={output_file}", f"{input_file}"])
        # print(f"Converted {file} to {os.path.basename(output_file)}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {file}: {e}")
        logger.error(f"Error converting {file}: {e}")


async def convert_to_png_parallel(directory, num_processes):
    files = os.listdir(directory)
    file_infos = [(directory, file) for file in files]

    async with aiomultiprocess.Pool(processes=num_processes, childconcurrency=1) as pool:
        await pool.map(convert_to_png, file_infos)


async def decode_png_file(file_info):
    directory, png_file = file_info
    png_file_path = os.path.join(directory, png_file)

    try:
        img = Image.open(png_file_path)
        decoded_data = await asyncio.to_thread(decode, img)

        if decoded_data:
            decoded_string = decoded_data[0].data.decode('utf-8')
            return png_file, decoded_string
        else:
            print(f"No data found in {png_file}")
            logger.error(f"No data found in {png_file}")
            return None
    except Exception as e:
        print(f"Error decoding {png_file}: {e}")
        logger.error(f"Error decoding {png_file}: {e}")
        return None


async def decode_png_files_parallel(directory, num_processes):
    png_files = [f for f in os.listdir(directory) if f.endswith('.png')]
    file_infos = [(directory, png_file) for png_file in png_files]

    async with aiomultiprocess.Pool(processes=num_processes, childconcurrency=1) as pool:
        decoded_results = await pool.map(decode_png_file, file_infos)

    decoded_strings = {filename: decoded_string for filename, decoded_string in decoded_results if decoded_string}
    return decoded_strings


def count_files(directory):
    count = 0
    for entry in os.listdir(directory):
        entry_path = os.path.join(directory, entry)
        if os.path.isfile(entry_path):
            count += 1
    return count


def delete_directory(directory_path):
    if os.path.exists(directory_path):
        try:
            shutil.rmtree(directory_path)
            logger.info(f"Directory '{directory_path}' and its contents have been deleted successfully.")
        except OSError as e:
            logger.error(f"Error deleting directory '{directory_path}': {e}")
    else:
        logger.error(f"Directory '{directory_path}' does not exist.")


def delete_old_data_folders(directory):
    for root, dirs, files in os.walk(directory):
        for dir_ in dirs:
            if dir_.startswith('data_folder_'):
                folder_path = os.path.join(root, dir_)
                try:
                    shutil.rmtree(folder_path)
                    print(f"Deleted folder: {folder_path}")
                except Exception as e:
                    print(f"Error deleting folder {folder_path}: {e}")


def delete_zip_files_in_current_directory():
    # Get a list of all .zip and .csv files in the current directory
    files = glob.glob('*.zip') + glob.glob('*.csv')

    # Loop through the list and delete each file
    for file in files:
        os.remove(file)
        print(f"Deleted {file}")  # Optional: Print the deleted file name


def delete_files(file_paths: list):
    for file_path in file_paths:
        try:
            os.remove(file_path)
            logger.info(f"File '{file_path}' has been deleted successfully.")
        except FileNotFoundError:
            logger.error(f"File '{file_path}' does not exist.")
        except PermissionError:
            logger.error(f"Permission denied to delete file '{file_path}'.")
        except Exception as e:
            logger.error(f"An error occurred while deleting file '{file_path}': {e}")


if __name__ == '__main__':
    pass
