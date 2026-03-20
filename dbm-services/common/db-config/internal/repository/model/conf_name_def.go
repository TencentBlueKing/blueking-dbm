package model

// ConfigNameDefModel TODO
// tb_config_name_def
type ConfigNameDefModel struct {
	ID           uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	Namespace    string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType     string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile     string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfName     string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`
	ConfNameLC   string `json:"conf_name_lc" gorm:"column:conf_name_lc;type:varchar(120);not null"`
	ValueType    string `json:"value_type" gorm:"column:value_type;type:varchar(120)"`
	ValueDefault string `json:"value_default" gorm:"column:value_default;type:varchar(120)"`
	ValueAllowed string `json:"value_allowed" gorm:"column:value_allowed;type:varchar(120)"`
	ValueTypeSub string `json:"value_type_sub" gorm:"column:value_type_sub;type:varchar(60)"`

	FlagVisible  int8 `json:"flag_visible" gorm:"column:flag_visible;type:tinyint"`
	FlagReadonly int8 `json:"flag_readonly" gorm:"column:flag_readonly;type:tinyint"`
	FlagLocked   int8 `json:"flag_locked" gorm:"column:flag_locked;type:tinyint"`
	FlagEncrypt  int8 `json:"flag_encrypt" gorm:"column:flag_encrypt;type:tinyint"`
	// 0:enable, 1:disable
	FlagDisable int8 `json:"flag_disable" gorm:"column:flag_disable;type:tinyint"`
	// 1: 显式的公共配置 0:不会显式出现在配置文件的全量配置项, 2: 显式的公共配置且只读即 visible only when rendering
	FlagStatus int8 `json:"flag_status" gorm:"column:flag_status;type:tinyint"`

	NeedRestart  int8   `json:"need_restart" gorm:"column:need_restart;type:tinyint"`
	ValueFormula string `json:"value_formula" gorm:"column:value_formula;type:varchar(120)"`
	OrderIndex   int    `json:"order_index" gorm:"column:order_index;type:int"`
	SinceVersion string `json:"since_version" gorm:"column:since_version;type:varchar(120)"`
	Description  string `json:"description" gorm:"column:description;type:text"`
	Stage        int8   `json:"stage" gorm:"column:stage;type:tinyint"`
	BaseDatetime
}

// BaseAutoTimeModel TODO
type BaseAutoTimeModel struct {
	CreatedAt string `json:"created_at" gorm:"->;column:created_at;type:varchar(30)"`
	UpdatedAt string `json:"updated_at" gorm:"->;column:updated_at;type:varchar(30)"`
}

// TableName TODO
func (c ConfigNameDefModel) TableName() string {
	return "tb_config_name_def"
}

// UniqueWhere TODO
// 定义该表唯一键的查询条件
// 都是内部传入的字段，不来自用户输入，所以不需要考虑注入问题
func (c ConfigNameDefModel) UniqueWhere() map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"namespace": c.Namespace,
		"conf_type": c.ConfType,
		"conf_file": c.ConfFile,
		"conf_name": c.ConfName,
	}
	return uniqueWhere
}

// IsReadOnly TODO
func (c ConfigNameDefModel) IsReadOnly() bool {
	if c.FlagStatus == 2 || c.FlagReadonly == 1 {
		return true
	}
	return false
}

// IsFormula TODO
func (c ConfigNameDefModel) IsFormula() bool {
	if c.ValueFormula != "" {
		return true
	}
	return false
}
