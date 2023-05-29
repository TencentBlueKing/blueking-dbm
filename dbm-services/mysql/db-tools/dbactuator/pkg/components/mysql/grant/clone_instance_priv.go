package grant

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// CloneInsPrivComp TODO
type CloneInsPrivComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *CloneInsPrivParam       `json:"extend"`
}

// CloneInsPrivParam TODO
type CloneInsPrivParam struct {
	// native.InsObject
	// 具体操作内容需要操作的参数
	// 当前实例的主机地址
	Host string `json:"host"  validate:"required,ip"`
	// 当前实例的端口
	Port int `json:"port"  validate:"required,lt=65536,gte=3306"`
	// 克隆权限的源实例
	SourceIns RemoteIns `json:"source_instance"`
}

// RemoteIns TODO
type RemoteIns struct {
	native.Instance
	//  对于当Host的临时超级账户
	User string `json:"user"`
	Pwd  string `json:"pwd"`
}

// CloneInsPrivRCtx 运行时上下文
type CloneInsPrivRCtx struct {
}
