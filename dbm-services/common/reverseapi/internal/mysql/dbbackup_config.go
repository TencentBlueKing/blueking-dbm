package mysql

import "github.com/pkg/errors"

func (c *MySQL) DBBackupConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/dbbackup_config", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call dbbackup_config")
	}
	return data, nil
}
