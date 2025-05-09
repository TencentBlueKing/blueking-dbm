package mysql

import "github.com/pkg/errors"

func (c *MySQL) ChecksumConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/checksum_config", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call checksum_config")
	}
	return data, nil
}
