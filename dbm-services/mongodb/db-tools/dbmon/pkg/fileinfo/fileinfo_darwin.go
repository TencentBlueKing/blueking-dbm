package fileinfo

import (
	"os"
	"syscall"
)

// GetFileIno returns the inode number of the file.
func GetFileIno(path string) (v uint64) {
	fileInfo, err := os.Lstat(path)
	if err != nil {
		return
	}
	return fileInfo.Sys().(*syscall.Stat_t).Ino
}
