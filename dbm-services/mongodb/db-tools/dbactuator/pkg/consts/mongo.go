package consts

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"path"

	"github.com/pkg/errors"
)

// MongoVersionV24 TODO
const MongoVersionV24 = "2.4"

// MongoVersionV30 TODO
const MongoVersionV30 = "3.0"

// MongoVersionV32 TODO
const MongoVersionV32 = "3.2"

// MongoVersionV34 TODO
const MongoVersionV34 = "3.4"

// MongoVersionV36 TODO
const MongoVersionV36 = "3.6"

// MongoVersionV40 TODO
const MongoVersionV40 = "4.0"

// MongoVersionV42 TODO
const MongoVersionV42 = "4.2"

// MongoVersionV100 TODO
const MongoVersionV100 = "100.7" // >= 4.4 https://www.mongodb.com/docs/database-tools/
// MongoInstallDir TODO
const MongoInstallDir = "/usr/local/mongodb"

// GetMongoShellBin 根据版本号获取mongodump的二进制文件名
// 2.x : 不支持
// others: mongodump.100
func GetMongoShellBin(version *mymongo.MongoVersion) (bin string, err error) {
	if version == nil {
		return "", errors.New("version is nil")
	}
	if version.Major >= 6 {
		bin = "mongosh"
	} else {
		bin = "mongo"
	}

	bin = path.Join(MongoInstallDir, "bin", bin)
	return
}
