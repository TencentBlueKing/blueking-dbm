package common

import (
	"dbm-services/common/reverseapi/pkg/core"
	"encoding/json"

	"github.com/pkg/errors"
)

func ListNginxAddrs(core *core.Core) ([]string, error) {
	data, err := core.Get("common/list_nginx_addrs")
	if err != nil {
		return nil, errors.Wrap(err, "failed to call ListNginxAddrs")
	}

	var addrs []string
	if err := json.Unmarshal(data, &addrs); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal ListNginxAddrs")
	}

	return addrs, nil
}
