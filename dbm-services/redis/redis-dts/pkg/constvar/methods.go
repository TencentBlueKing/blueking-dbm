package constvar

import (
	"fmt"
	"time"

	"github.com/spf13/viper"
)

// GetABSUser env ABSUSER
func GetABSUser() (absUser string) {
	absUser = viper.GetString("ABSUSER")
	if absUser == "" {
		absUser = "mysql" // default 'mysql'
	}
	return absUser
}

// GetABSPassword env ABSPASSWORD
func GetABSPassword() (absPasswd string, err error) {
	absPasswd = viper.GetString("ABSPASSWORD")
	if absPasswd == "" {
		err = fmt.Errorf("ABSPASSWORD is empty...")
		return
	}
	return
}

// GetABSPort env ABSPORT
func GetABSPort() (absPort int) {
	absPort = viper.GetInt("ABSPORT")
	if absPort == 0 {
		absPort = 36000 // default 36000
	}
	return
}

// GetABSPullBwLimit env RsyncPullBwLimit
func GetABSPullBwLimit() (pullBwLimit int64) {
	pullBwLimit = viper.GetInt64("RsyncPullBwLimit")
	if pullBwLimit == 0 {
		pullBwLimit = 400 * 1024 // default 400 kbit/s
	}
	return
}

// GetABSPullTimeout env RsyncPullTimeout
func GetABSPullTimeout() (pullTimeout time.Duration) {
	var timeout int
	timeout = viper.GetInt("RsyncPullTimeout")
	if pullTimeout == 0 {
		timeout = 36000
	}
	return time.Duration(timeout * int(time.Second))
}

// GetBkCloudID 获取本机器bk_cloud_id
func GetBkCloudID() (bkCloudID int64) {
	bkCloudID = viper.GetInt64("bkCloudID")
	return
}

// GetZoneName 获取本机器zoneName
func GetZoneName() (zoneName string) {
	zoneName = viper.GetString("zoneName")
	return
}
