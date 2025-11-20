package mysql

import (
	"dbm-services/common/reverseapi/pkg/core"

	"github.com/pkg/errors"
)

func ExporterConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/exporter_config/", ports...)
	if err != nil {
		return nil, errors.WithStack(err)
	}
	return data, nil
}
