package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/reverseapi/define/mysql"
	"dbm-services/common/reverseapi/internal/core"
	"encoding/json"
	"fmt"

	"github.com/pkg/errors"
)

func ListInstanceInfo(core *core.Core, ports ...int) ([]byte, string, error) {
	data, err := core.Get("mysql/list_instance_info/", ports...)
	if err != nil {
		return nil, "", errors.Wrap(err, "failed to call list_instance_info")
	}

	logger.Info(fmt.Sprintf("raw data %s", string(data)))
	var r []mysql.CommonInstanceInfo
	err = json.Unmarshal(data, &r)
	if err != nil {
		return nil, "", errors.Wrap(err, "failed to unmarshal list_instance_info")
	}

	if len(r) == 0 {
		return nil, "", errors.New("no instance info")
	}

	return data, r[0].AccessLayer, nil
}
