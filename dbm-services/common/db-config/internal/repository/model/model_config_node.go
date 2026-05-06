package model

// ConfigModelOp TODO
type ConfigModelOp struct {
	Config *ConfigModel
	// config model 操作类型, add,delete,update, delete_ref
	OPType string `json:"op_type"`
}

// ConfigModelVOp will replace ConfigModelOp
type ConfigModelVOp struct {
	Config *ConfigModelView
	// config model 操作类型, add,delete,update, delete_ref
	OPType string `json:"op_type"`
}

// ConfigModelView TODO
// v_tb_config_node
type ConfigModelView struct {
	ConfigModel
	Cluster string `json:"cluster" gorm:"column:cluster;type:varchar(120)"`
	Module  string `json:"module" gorm:"column:module;type:varchar(120)"`
	// todo used to replace Cluster Module, 用户存放改item的上层信息
	UpLevelInfo map[string]string `json:"up_level_info"`
}
