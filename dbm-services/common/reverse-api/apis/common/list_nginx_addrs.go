package common

import (
	"dbm-services/common/reverse-api/config"
	"dbm-services/common/reverse-api/internal"
	"encoding/json"

	"github.com/pkg/errors"
)

func ListNginxAddrs(bkCloudId int) ([]string, error) {
	data, err := internal.ReverseCall(config.ReverseApiCommonListNginxAddrs, bkCloudId)
	if err != nil {
		return nil, errors.Wrap(err, "failed to call ListNginxAddrs")
	}

	var addrs []string
	if err := json.Unmarshal(data, &addrs); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal ListNginxAddrs")
	}

	return addrs, nil
}
