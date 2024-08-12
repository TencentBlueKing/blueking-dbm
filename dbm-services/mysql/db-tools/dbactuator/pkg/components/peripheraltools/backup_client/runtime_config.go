package backup_client

import (
	"bytes"
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
	"github.com/pkg/errors"
)

func (c *BackupClientComp) GenerateBinaryConfig() (err error) {
	c.configFile = filepath.Join(c.installPath, "conf/config.toml")
	buf := bytes.NewBuffer([]byte{})
	if err = toml.NewEncoder(buf).Encode(&c.Params.Config); err != nil {
		return errors.Wrapf(err, "write config file")
	}

	if err := os.WriteFile(c.configFile, buf.Bytes(), 0644); err != nil {
		return err
	}
	return nil
}
