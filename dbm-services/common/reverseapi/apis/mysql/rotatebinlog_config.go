package mysql

import (
	"dbm-services/common/reverseapi/pkg/core"

	"github.com/pkg/errors"
)

func RotatebinlogConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/rotatebinlog_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call rotatebinlog_config")
	}
	return data, nil
}
