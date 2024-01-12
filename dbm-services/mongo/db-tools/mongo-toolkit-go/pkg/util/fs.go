package util

import (
	"os"
	"os/user"
	"strconv"
)

// GetFullPath 根据版本号获取mongodump的二进制文件名
func getUid(userName string) (int, int, error) {
	group, err := user.Lookup(userName)
	if err != nil {
		return -1, -1, err
	}
	uid, _ := strconv.Atoi(group.Uid)
	gid, _ := strconv.Atoi(group.Gid)
	return uid, gid, nil
}

// Chown change file owner
func Chown(file string, user string) error {
	uid, gid, err := getUid(user)
	if err != nil {
		return err
	}
	return os.Chown(file, uid, gid)
}
