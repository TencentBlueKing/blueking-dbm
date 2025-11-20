package mysql

import (
	"dbm-services/common/reverseapi/pkg/core"

	"github.com/pkg/errors"
)

func ChecksumConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/checksum_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call checksum_config")
	}
	return data, nil
}
