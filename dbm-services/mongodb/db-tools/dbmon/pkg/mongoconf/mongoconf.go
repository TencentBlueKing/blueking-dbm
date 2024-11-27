package mongoconf

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"os"
	"path"
	"strconv"
)

// GetConfigPath get config path
func GetConfigPath(port string) (string, error) {
	pdir := consts.GetMongoDataDir(port)
	filePath := path.Join(pdir, "mongodata", port, "mongo.conf")
	_, err := os.Stat(filePath)
	return filePath, err
}

// LoadMongodConfig load mongod config
func LoadMongodConfig(port int) (*common.YamlMongoDBConf, error) {
	filePath, err := GetConfigPath(strconv.Itoa(port))
	if err != nil {
		return nil, err
	}
	return common.LoadMongoDBConfFromFile(filePath)
}

// LoadMongosConfig load mongos config
func LoadMongosConfig(port int) (*common.YamlMongoSConf, error) {
	filePath, err := GetConfigPath(strconv.Itoa(port))
	if err != nil {
		return nil, err
	}
	return common.LoadMongoSConfFromFile(filePath)
}
