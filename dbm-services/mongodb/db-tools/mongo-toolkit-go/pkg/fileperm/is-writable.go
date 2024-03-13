//go:build !windows

package fileperm

import (
	"os"
	"syscall"

	"github.com/pkg/errors"
	"golang.org/x/sys/unix"
)

// https://stackoverflow.com/questions/20026320/how-to-tell-if-folder-exists-and-is-writable

// IsFileWritable checks if the file is writable.
func IsFileWritable(filePath string) bool {
	return unix.Access(filePath, unix.W_OK) == nil
}

// IsDirWritable checks if the directory is writable (create sub dir).
func IsDirWritable(path string) (isWritable bool, err error) {
	isWritable = false
	info, err := os.Stat(path)
	if err != nil {
		return
	}

	err = nil
	if !info.IsDir() {
		return
	}

	// Check if the user bit is enabled in file permission
	if info.Mode().Perm()&(1<<(uint(7))) == 0 {
		return
	}

	var stat syscall.Stat_t
	if err = syscall.Stat(path, &stat); err != nil {
		return
	}

	err = nil
	if uint32(os.Geteuid()) != stat.Uid {
		isWritable = false
		err = errors.New("User doesn't have permission to write to this directory")
		return
	}

	isWritable = true
	return
}
