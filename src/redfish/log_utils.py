###
# Copyright 2024 Hewlett Packard Enterprise, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

# -*- coding: utf-8 -*-
"""Utility functions for log file management and rotation"""
import gzip
import os
import glob
import shutil
import logging

LOGGER = logging.getLogger(__name__)


class RestDebugLogRotator:
    """
    Utility class for managing rest.debug.log file rotation and compression.
    """

    @staticmethod
    def rotate_rest_debug_log(log_dir, max_size_mb=2.0, max_backups=3):
        """
        Rotate and compress rest.debug.log file if it exceeds the size threshold.

        Args:
            log_dir (str): Directory containing the rest.debug.log file
            max_size_mb (int): Maximum size in MB before rotation (default: 2.0MB)
            max_backups (int): Maximum number of backup files to keep (default: 3)

        The rotation scheme:
            rest.debug.log          -> rest.debug.log.1.gz (compressed)
            rest.debug.log.1.gz     -> rest.debug.log.2.gz
            rest.debug.log.2.gz     -> rest.debug.log.3.gz
            ...
            rest.debug.log.N.gz     -> deleted (if N >= max_backups)
        """
        try:
            log_file = os.path.join(log_dir, "rest.debug.log")

            # Check if log file exists
            if not os.path.exists(log_file):
                return

            # Check file size
            file_size_mb = os.path.getsize(log_file) / (1024 * 1024)

            if file_size_mb < max_size_mb:
                LOGGER.debug(f"rest.debug.log size {file_size_mb:.2f}MB below {max_size_mb}MB, no rotation needed")
                return

            LOGGER.debug(f"rest.debug.log size ({file_size_mb:.2f}MB) exceeds threshold ({max_size_mb}MB), rotating...")

            # Get existing backup files and sort them
            backup_pattern = os.path.join(log_dir, "rest.debug.log.*.gz")
            existing_backups = sorted(glob.glob(backup_pattern), reverse=True)

            # Rotate existing backups (move .N.gz to .N+1.gz)
            for backup in existing_backups:
                # Extract the number from rest.debug.log.N.gz
                try:
                    backup_num = int(backup.rsplit('.', 2)[1])
                    new_num = backup_num + 1

                    if new_num > max_backups:
                        # Delete old backup that exceeds max_backups
                        os.remove(backup)
                        LOGGER.debug(f"Deleted old backup: {os.path.basename(backup)}")
                    else:
                        # Rename to next number
                        new_backup = os.path.join(log_dir, f"rest.debug.log.{new_num}.gz")
                        shutil.move(backup, new_backup)
                        LOGGER.debug(f"Rotated {os.path.basename(backup)} -> {os.path.basename(new_backup)}")
                except (ValueError, IndexError) as e:
                    LOGGER.warning(f"Failed to parse backup filename {backup}: {e}")
                    continue

            # Compress current log file to .1.gz
            compressed_file = os.path.join(log_dir, "rest.debug.log.1.gz")
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    f_out.flush()  # Ensure all data is written to disk
                    os.fsync(f_out.fileno())  # Force write of file to disk

            LOGGER.debug("Compressed rest.debug.log -> rest.debug.log.1.gz")

            # Remove the original log file (C++ DLL will create a new one)
            os.remove(log_file)
            LOGGER.debug("Removed original rest.debug.log, new file will be created by DLL")

        except Exception as e:
            # Don't fail if rotation fails, just log the error
            LOGGER.error(f"Failed to rotate rest.debug.log: {e}")
