package mysql

import "github.com/pkg/errors"

func (c *MySQL) CrondConfig() ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/mysql_crond_config/")
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call mysql_crond_config")
	}
	return data, nil
}
