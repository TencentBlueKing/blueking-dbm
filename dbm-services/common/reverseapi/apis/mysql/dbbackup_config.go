package mysql

import (
	"dbm-services/common/reverseapi/pkg/core"

	"github.com/pkg/errors"
)

func DBBackupConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/dbbackup_config/", ports...)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call dbbackup_config")
	}
	return data, nil
}
