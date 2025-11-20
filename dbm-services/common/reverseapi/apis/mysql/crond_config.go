package mysql

import (
	"dbm-services/common/reverseapi/pkg/core"

	"github.com/pkg/errors"
)

func CrondConfig(core *core.Core, ports ...int) ([]byte, error) {
	data, err := core.Get("mysql/mysql_crond_config/")
	if err != nil {
		return nil, errors.Wrapf(err, "failed to call mysql_crond_config")
	}
	return data, nil
}
