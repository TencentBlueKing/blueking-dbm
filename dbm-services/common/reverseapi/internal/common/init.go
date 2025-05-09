package common

import "dbm-services/common/reverseapi/internal/core"

type Common struct {
	core *core.Core
}

func NewCommon(bkCloudId int64, nginxAddrs ...string) *Common {
	return &Common{
		core: core.NewCore(bkCloudId, nginxAddrs...),
	}
}
