package mysql

import (
	"dbm-services/common/reverse-api/config"
	"dbm-services/common/reverse-api/internal"
	"encoding/json"

	"github.com/pkg/errors"
)

const (
	AccessLayerStorage string = "storage"
	AccessLayerProxy   string = "proxy"
)

type instanceAddr struct {
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}

type commonInstanceInfo struct {
	instanceAddr
	ImmuteDomain string `json:"immute_domain"`
	Phase        string `json:"phase"`
	Status       string `json:"status"`
	AccessLayer  string `json:"access_layer"`
	MachineType  string `json:"machine_type"`
}

type StorageInstanceInfo struct {
	commonInstanceInfo
	IsStandBy         bool           `json:"is_stand_by"`
	InstanceRole      string         `json:"instance_role"`
	InstanceInnerRole string         `json:"instance_inner_role"`
	Receivers         []instanceAddr `json:"receivers"`
	Ejectors          []instanceAddr `json:"ejectors"`
}

type ProxyInstanceInfo struct {
	commonInstanceInfo
	StorageInstanceList []instanceAddr `json:"storage_instance_list"`
}

func ListInstanceInfo(bkCloudId int, ports ...int) ([]byte, string, error) {
	data, err := internal.ReverseCall(config.ReverseApiMySQLListInstanceInfo, bkCloudId, ports...)
	if err != nil {
		return nil, "", errors.Wrap(err, "failed to call ListInstanceInfo")
	}
	var r []commonInstanceInfo
	err = json.Unmarshal(data, &r)
	if err != nil {
		return nil, "", errors.Wrap(err, "failed to unmarshal ListInstanceInfo")
	}

	return data, r[0].AccessLayer, nil
}
