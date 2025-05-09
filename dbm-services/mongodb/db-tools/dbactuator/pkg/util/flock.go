package util

import (
	"fmt"
	"path"

	"github.com/gofrs/flock"
	"github.com/pkg/errors"
)

var ErrAcquireLock = errors.New("could not acquire lock")

// GetFileLock 获取文件锁. filePath.0 filePath.1 filePath.2 ...
func GetFileLock(filePath string, maxConcurrent int) (lock *flock.Flock, err error) {
	dirName := path.Dir(filePath)
	if !DirExists(dirName) {
		return nil, fmt.Errorf("directory %s does not exist", dirName)
	}

	for i := 0; i < maxConcurrent; i++ {
		lockFile := path.Join(dirName, fmt.Sprintf("%s.lock.%d", path.Base(filePath), i))
		lock = flock.New(lockFile)
		if locked, _ := lock.TryLock(); locked {
			return lock, nil
		}
	}
	return nil, ErrAcquireLock
}
