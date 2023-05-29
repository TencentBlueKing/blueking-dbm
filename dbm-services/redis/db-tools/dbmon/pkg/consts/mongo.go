package consts

import (
	"os/user"
	"path"
)

// meta role
const (
	MetaRoleShardsvrBackup = "shardsvr-backup"
	MetaRoleMongos         = "mongos"
)

// twemproxy monitor event categories
const (
	EventMongoRestart = "mongo_restart"
	EventMongoLogin   = "mongo_login"
)

// MongoBin 相关
const (
	MongoBin     = "/usr/local/mongodb/bin/mongo"
	MongoToolKit = "mongo-toolkit-go_Linux"
)

// GetDbToolDir 获取dbtool目录，在用户目录 dbtools/mg 下
func GetDbToolDir() string {
	currentUser, err := user.Current()
	if err != nil {
		return ""
	}
	username := currentUser.Username
	return path.Join("/home/", username, "dbtools", "mg")
}

// GetDbTool 获取dbtool目录，在用户目录 dbtools/mg 下
func GetDbTool(dbType string, bin string) string {
	currentUser, err := user.Current()
	if err != nil {
		return ""
	}
	username := currentUser.Username
	if dbType != "" {
		return path.Join("/home/", username, "dbtools", dbType, bin)
	}
	return path.Join("/home/", username, "dbtools", bin)
}
