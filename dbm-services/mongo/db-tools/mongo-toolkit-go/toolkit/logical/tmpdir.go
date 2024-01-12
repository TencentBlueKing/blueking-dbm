package logical

import (
	"fmt"
	"os"
	"path"
	"time"

	"github.com/pkg/errors"
)

// FileExists 检查目录是否已经存在
func fileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// getMongoDumpOutPath return path Like /data/dbbak/mongodump-$unixtime
func getTmpSubDir(backupDir, subDirPrefix string) (string, string, error) {
	if !fileExists(backupDir) {
		return "", "", errors.Errorf("Dir Not Exists, Dir:%s", backupDir)
	}
	var err error
	for i := 0; i < 10; i++ {
		tmpName := fmt.Sprintf("%s-%d", subDirPrefix, time.Now().Unix())
		tmpPath := path.Join(backupDir, tmpName)
		if fileExists(tmpPath) {
			time.Sleep(time.Second)
			continue
		}
		err = os.MkdirAll(tmpPath, 0755)
		if err == nil {
			return tmpPath, tmpName, err
		}
	}
	return "", "", err
}
