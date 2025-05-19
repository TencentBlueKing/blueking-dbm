package mysql

import "github.com/pkg/errors"

func (c *MySQL) RotatebinlogConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/rotatebinlog_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call rotatebinlog_config")
	}
	return data, nil
}
