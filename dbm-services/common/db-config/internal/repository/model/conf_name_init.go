package model

type ConfigNameInitModel ConfigNameDefModel

// TableName 从 dbm saas 代码层初始化的系统 conf_names
// 定义与 tb_config_name_def 完全相同，但 tb_config_name_def 可被页面修改
func (c ConfigNameInitModel) TableName() string {
	return "tb_config_name_init"
}
