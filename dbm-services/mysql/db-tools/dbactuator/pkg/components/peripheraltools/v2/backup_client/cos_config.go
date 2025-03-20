package backup_client

import (
	"bytes"
	"dbm-services/common/go-pubpkg/cmutil"
	"os"
	"os/user"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

func (c *BackupClientComp) GenerateBucketConfig() (err error) {
	mysqlUser, err := user.Lookup("mysql")
	if err != nil {
		return err
	}
	userHome := mysqlUser.HomeDir
	if userHome != "" && cmutil.IsDirectory(userHome) {

	}
	configFile := filepath.Join(userHome, ".cosinfo.toml")
	buf := bytes.NewBuffer([]byte{})
	if err := toml.NewEncoder(buf).Encode(&c.Params.CosInfo); err != nil {
		return err
	}
	if err := os.WriteFile(configFile, buf.Bytes(), 0644); err != nil {
		return err
	}
	return nil
}
