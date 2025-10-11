/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package pidfile provides functionality to create and manage PID files.
// A PID file typically contains the process ID of a running program and is used
// to prevent multiple instances of the same program from running concurrently.
package pidfile

import (
	"fmt"
	"os"
	"runtime"
	"syscall"
)

// CreatePIDFile creates a PID file and optionally acquires an exclusive lock on it.
// It checks if a PID file already exists and validates whether the process is still running.
// For Windows systems, it checks the process existence by PID.
// For Unix systems, it checks if the file is locked by another process.
// If the existing process is not running (or file is unlocked), it removes the stale PID file.
// Then it creates a new PID file with the current process ID and optionally locks it.
// Parameters:
//   - filename: path to the PID file
//
// Returns:
//   - *os.File: the file descriptor of the created PID file
//   - error: if any error occurs during the process
func CreatePIDFile(filename string) (*os.File, error) {
	/* If the pid file already exists */
	if _, err := os.Stat(filename); err == nil {
		{
			file, err := os.Open(filename)
			if err != nil {
				return nil, fmt.Errorf("failed to open existing PID file: %v", err)
			}
			defer file.Close()

			if runtime.GOOS == "windows" { // On Windows, ensure single instance by checking PID
				var pid int
				_, err := fmt.Fscanf(file, "%d", &pid)
				if err != nil {
					return nil, fmt.Errorf("failed to read PID from existing PID file: %v", err)
				}

				var process_exists bool
				process_exists, err = windowsProcessExists(pid)
				if err != nil {
					return nil, fmt.Errorf("failed to check process existence from existing PID file: %v", err)
				}

				if process_exists {
					return nil, fmt.Errorf("process already exists")
				}
			} else { // On Unix, ensure single instance by file lock
				isLocked, err := unixIsFileLocked(file)
				if err != nil {
					return nil, fmt.Errorf("failed to check file lock: %v", err)
				}

				if isLocked {
					return nil, fmt.Errorf("PID file is locked by another process")
				}
			}
		}

		// Remove the leftover PID file
		if err := os.Remove(filename); err != nil {
			return nil, fmt.Errorf("failed to remove existing PID file: %v", err)
		}
	}

	file, err := os.OpenFile(filename, os.O_WRONLY|os.O_CREATE|os.O_EXCL|os.O_TRUNC, 0644)
	if err != nil {
		return nil, err
	}

	_, err = fmt.Fprintf(file, "%d\n", os.Getpid())
	if err != nil {
		file.Close()
		return nil, err
	}

	// On Unix, acquire file lock to ensure single instance
	if runtime.GOOS != "windows" {
		if err := unixLockFile(file); err != nil {
			file.Close()
			return nil, err
		}
	}

	return file, nil
}

// unixIsFileLocked checks file lock status on Unix systems
func unixIsFileLocked(file *os.File) (bool, error) {
	flock := syscall.Flock_t{Type: syscall.F_WRLCK}
	if err := syscall.FcntlFlock(file.Fd(), syscall.F_GETLK, &flock); err != nil {
		return false, err
	}
	return flock.Type != syscall.F_UNLCK, nil
}

// unixLockFile acquires lock on Unix systems
func unixLockFile(file *os.File) error {
	flock := syscall.Flock_t{
		Type:   syscall.F_WRLCK,
		Whence: 0,
		Start:  0,
		Len:    0,
	}

	if err := syscall.FcntlFlock(file.Fd(), syscall.F_SETLK, &flock); err != nil {
		return fmt.Errorf("failed to lock PID file: %v", err)
	}
	return nil
}

// ReadPID reads the process ID from the specified PID file.
// It opens the file, parses the integer PID value, and returns it.
// Parameters:
//   - filename: path to the PID file
//
// Returns:
//   - pid: the process ID read from the file
//   - error: if file cannot be opened or PID format is invalid
func ReadPID(filename string) (int, error) {
	file, err := os.Open(filename)
	if err != nil {
		return 0, fmt.Errorf("failed to open PID file: %v", err)
	}
	defer file.Close()

	var pid int
	_, err = fmt.Fscanf(file, "%d", &pid)
	if err != nil {
		return 0, fmt.Errorf("invalid PID format: %v", err)
	}
	return pid, nil
}

// DeletePIDFile removes the PID file after validating that the PID in the file
// matches the current process's PID. This prevents accidental deletion of another process's PID file.
// Parameters:
//   - filename: path to the PID file to delete
//
// Returns:
//   - error: if PID mismatch occurs or file deletion fails
func DeletePIDFile(filename string) error {
	pid, err := ReadPID(filename)
	if err != nil {
		return err
	}

	currentPID := os.Getpid()
	if pid != currentPID {
		return fmt.Errorf("PID mismatch: file contains %d, current process is %d", pid, currentPID)
	}

	if err := os.Remove(filename); err != nil {
		return fmt.Errorf("failed to delete PID file: %v", err)
	}

	return nil
}

// IsProcessExists checks if a process with the given PID exists.
// It uses OS-specific implementations:
//   - Windows: calls windowsProcessExists
//   - Unix-like systems: calls unixProcessExists
//
// Parameters:
//
//	pid: process ID to check
//
// Returns:
//
//	bool: true if process exists, false otherwise
//	error: non-nil if an error occurred during checking
func IsProcessExists(pid int) (bool, error) {
	switch runtime.GOOS {
	case "windows":
		return windowsProcessExists(pid)
	default:
		return unixProcessExists(pid)
	}
}

// unixProcessExists checks process existence on Unix-like systems
// by sending signal 0 (no-op) to the process.
// Parameters:
//
//	pid: process ID to check
//
// Returns:
//
//	bool: true if process exists
//	error: non-nil if an error occurred during checking
func unixProcessExists(pid int) (bool, error) {
	err := syscall.Kill(pid, 0)

	if err == nil {
		return true, nil
	}

	switch err {
	case syscall.ESRCH:
		return false, nil
	case syscall.EPERM:
		return true, fmt.Errorf("process exists, but permission denied")
	default:
		return false, fmt.Errorf("unexpected error: %v", err)
	}
}

// windowsProcessExists checks process existence on Windows systems.
// Parameters:
//
//	pid: process ID to check
//
// Returns:
//
//	bool: true if process exists
//	error: non-nil if an error occurred during checking
func windowsProcessExists(pid int) (bool, error) {
	return false, fmt.Errorf("process existence check for Windows is not implemented")
}
