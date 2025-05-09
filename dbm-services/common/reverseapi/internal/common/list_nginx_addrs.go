package common

import (
	"encoding/json"

	"github.com/pkg/errors"
)

func (c *Common) ListNginxAddrs() ([]string, error) {
	data, err := c.core.ReverseCall("common/list_nginx_addrs")
	if err != nil {
		return nil, errors.Wrap(err, "failed to call ListNginxAddrs")
	}

	var addrs []string
	if err := json.Unmarshal(data, &addrs); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal ListNginxAddrs")
	}

	return addrs, nil
}
