package mysql

import "github.com/pkg/errors"

func (c *MySQL) ExporterConfig(ports ...int) ([]byte, error) {
	data, err := c.core.ReverseCall("mysql/exporter_config/", ports...)
	if err != nil {
		return nil, errors.WithStack(err)
	}
	return data, nil
}
