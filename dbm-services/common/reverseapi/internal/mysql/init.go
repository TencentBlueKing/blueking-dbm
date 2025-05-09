package mysql

import "dbm-services/common/reverseapi/internal/core"

type MySQL struct {
	core *core.Core
}

func NewMySQL(bkCloudId int64, nginxAddrs ...string) *MySQL {
	return &MySQL{
		core: core.NewCore(bkCloudId, nginxAddrs...),
	}
}
