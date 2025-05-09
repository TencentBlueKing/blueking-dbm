package mysql

import (
	"dbm-services/common/reverseapi/define/mysql"
	"encoding/json"

	"github.com/pkg/errors"
)

func (c *MySQL) ListInstanceInfo(ports ...int) ([]byte, string, error) {
	data, err := c.core.ReverseCall("mysql/list_instance_info", ports...)
	if err != nil {
		return nil, "", errors.Wrap(err, "failed to call list_instance_info")
	}
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
