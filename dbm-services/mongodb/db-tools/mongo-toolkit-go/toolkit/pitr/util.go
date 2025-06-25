package pitr

import (
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"os"
	"os/exec"
	"path"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

// FileExists https://stackoverflow.com/questions/12518876/how-to-check-if-a-file-exists-in-go
func FileExists(filePath string) (bool, error) {
	if _, err := os.Stat(filePath); err == nil {
		// path/to/whatever exists
		return true, nil

	} else if os.IsNotExist(err) {
		// path/to/whatever does *not* exist
		return false, nil
	} else {
		return false, err
		// Schrodinger: file may or may not exist. See err for details.

		// Therefore, do *NOT* use !os.IsNotExist(err) to test for file existence
	}
}

// CommandExists determines if a command exists
func CommandExists(cmd string) bool {
	_, err := exec.LookPath(cmd)
	return err == nil
}

// IsDirectory determines if a file represented
// by `path` is a directory or not
func IsDirectory(path string) (bool, error) {
	fileInfo, err := os.Stat(path)
	if err != nil {
		return false, err
	}
	return fileInfo.IsDir(), err
}

// GetMongoDumpBin 根据版本号获取mongodump的二进制文件名
// 2.x : 不支持
// 3.x, 4.0, 4.2: mongodump.$v0.$v1
// others: mongodump.100
// 从 MongoDB 4.4 开始，MongoDB 数据库工具现在与 MongoDB 服务器分开发布，并使用自己的版本控制，初始版本为 100.0.0
func GetMongoDumpBin(version *mymongo.MongoVersion) (bin string, err error) {
	if version == nil {
		return "", errors.New("version is nil")
	}

	switch version.Major {
	case 2:
		return "", fmt.Errorf("not support version:%s", version.Version)
	case 3:
		bin = fmt.Sprintf("mongodump.%d.%d", version.Major, version.Minor)
	case 4:
		switch version.Minor {
		case 0, 2:
			bin = fmt.Sprintf("mongodump.%d.%d", version.Major, version.Minor)
		default:
			bin = fmt.Sprintf("mongodump.%s", MongoVersionV100) // >=4.4 100.7
		}
	default:
		bin = fmt.Sprintf("mongodump.%s", MongoVersionV100) // 100.7
	}

	binPath, err := FindBinPath(bin, consts.GetDbTool("mongotools"))
	if err != nil {
		return "", err
	}
	return binPath, nil
}

// GetMongoDumpBin 根据版本号获取mongodump的二进制文件名
// 2.x : 不支持
// 3.x, 4.0, 4.2: mongorestore (4.2)
// others: mongodump.100.7
// 从 MongoDB 4.4 开始，MongoDB 数据库工具现在与 MongoDB 服务器分开发布，并使用自己的版本控制，初始版本为 100.0.0
func GetMongoRestoreBin(version *mymongo.MongoVersion) (bin string, err error) {
	if version == nil {
		return "", errors.New("version is nil")
	}

	switch version.Major {
	case 2:
		return "", fmt.Errorf("not support version:%s", version.Version)
	case 3:
		bin = "mongorestore.4.2"
	case 4:
		switch version.Minor {
		case 0, 2:
			bin = "mongorestore.4.2"
		default:
			bin = fmt.Sprintf("mongorestore.%s", MongoVersionV100) // >=4.4 100.7
		}
	default:
		bin = fmt.Sprintf("mongorestore.%s", MongoVersionV100) // 100.7
	}

	binPath, err := FindBinPath(bin, consts.GetDbTool("mongotools"))
	if err != nil {
		return "", err
	}
	return binPath, nil
}

// MustFindBinPath 获取zstd的二进制文件路径
func MustFindBinPath(bin string, pathList ...string) (binPath string) {
	bin, err := FindBinPath(bin, pathList...)
	if err != nil {
		log.Fatalf("find bin %s failed, err: %v", bin, err)
	}
	return bin
}

// FindBinPath 获取zstd的二进制文件路径
func FindBinPath(bin string, pathList ...string) (binPath string, err error) {
	for _, ex := range pathList {
		bin = path.Join(ex, bin)
		if _, err := os.Stat(bin); err == nil {
			return bin, nil
		}
	}
	return "", errors.Errorf("bin %s not found in pathList %v", bin, pathList)
}
