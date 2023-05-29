package api

// BaseConfFileDef TODO
type BaseConfFileDef struct {
	// 命名空间，一般指DB类型
	Namespace string `json:"namespace" form:"namespace" validate:"required" example:"tendbha"`
	// 配置类型，如 dbconf,backup
	ConfType string `json:"conf_type" form:"conf_type" validate:"required" example:"dbconf"`
	// 配置文件名，一般配置类型与配置文件一一对应，但如 mysql 5.6, 5.7 两个版本同属 dbconf 配置，所以有 MySQL-5.5, MySQL-5.6 两个配置文件
	ConfFile string `json:"conf_file" form:"conf_file" validate:"required" example:"MySQL-5.7"`
}

// ConfFileDef TODO
type ConfFileDef struct {
	BaseConfFileDef
	// 配置类型中文名
	ConfTypeLC string `json:"conf_type_lc" form:"conf_type_lc" example:"DB参数配置"`
	// 配置文件中文名，也可以是其它 locale 语言类型
	ConfFileLC string `json:"conf_file_lc" form:"conf_file_lc" example:"5.7_参数配置"`
	// namespace信息，比如数据库版本，与 conf_file 对应
	NamespaceInfo string `json:"namespace_info" form:"namespace_info" example:"MySQL 5.7"`
	// 配置文件的描述
	Description string `json:"description" form:"description"`
}

// ConfFileResp TODO
type ConfFileResp struct {
	ConfFileDef
	UpdatedBy string `json:"updated_by"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// ConfNameDef TODO
type ConfNameDef struct {
	// 配置项，也叫参数项
	ConfName string `json:"conf_name" form:"conf_name" validate:"required"`
	// 配置项中文名，可不填
	ConfNameLC string `json:"conf_name_lc" form:"conf_name_lc"`
	// 配置项的值类型，如 `STRING`,`INT`,`FLOAT`,`NUMBER`
	ValueType string `json:"value_type" form:"value_type" validate:"required,enums" enums:"STRING,INT,FLOAT,NUMBER" example:"STRING"`
	// value_type 的子类型，如果设置则用于校验 value_type 的具体类型，或者返回用于告知前端控件类型，例如 ENUM,RANGE
	ValueTypeSub string `json:"value_type_sub" form:"value_type_sub" validate:"enums" enums:",STRING,ENUM,ENUMS,RANGE,BYTES,REGEX,JSON,COMPLEX" example:"ENUM"`
	// 允许设定值，如枚举/范围等，为空时表示不限制范围
	// 当 value_type_sub=ENUM 时，value_allowed 格式 0|1 或者 ON|OFF 或者 aaa|bbb|ccc ， 会校验value的合法性
	// 当 value_type_sub=REGEX 时，会根据 value_allowed 进行正则校验
	// 当 value_type_sub=RANGE 时，也会校验value 范围的合法性.
	//  - BYTES 是一种特殊的RANGE，value允许1mm 但value_allowed 必须是数字的range
	ValueAllowed string `json:"value_allowed" form:"value_allowed"`
	// 配置项默认值
	ValueDefault string `json:"value_default" form:"value_default" example:"1"`
	// 是否需要重启生效. 默认1
	NeedRestart int8 `json:"need_restart" form:"need_restart" example:"1"`
	// 是否禁用，代表该配置项状态. 默认0启用. 1: disable，相当于软删, -1: 物理删除
	FlagDisable int8 `json:"flag_disable" form:"flag_disable" example:"0"`
	// 是否锁定. 默认0
	FlagLocked int8 `json:"flag_locked" form:"flag_locked" example:"0"`
	// 配置读写状态，1:可读可写， 2:只读不可修改，用于展示或者生成配置 -1: 不展示配置，只表示合法全量配置用于下拉
	FlagStatus int8 `json:"flag_status" form:"flag_status" example:"1"`
	// 配置项说明
	Description string `json:"description" form:"description"`
}

// ConfTypeDef TODO
type ConfTypeDef struct {
	ConfFileDef
	LevelNames        string `json:"level_names"`
	LevelVersioned    string `json:"level_versioned"`
	VersionKeepLimit  int    `json:"version_keep_limit"`
	VersionKeepDays   int    `json:"version_keep_days"`
	ConfNameValidate  int8   `json:"conf_name_validate"`
	ConfValueValidate int8   `json:"conf_value_validate"`
	ConfNameOrder     int8   `json:"conf_name_order"`
}

// UpsertConfNames TODO
type UpsertConfNames struct {
	ConfNameDef
	OperationType
}

// QueryConfigNamesReq TODO
type QueryConfigNamesReq struct {
	ConfType string `json:"conf_type" form:"conf_type" validate:"required" example:"dbconf"`
	ConfFile string `json:"conf_file" form:"conf_file" validate:"required" example:"MySQL-5.7"`
	// 如果设置，会根据前缀模糊匹配搜索
	ConfName  string `json:"conf_name" form:"conf_name"`
	Namespace string `json:"namespace" form:"namespace" example:"tendbha"`
} // @name QueryConfigNamesReq

// QueryConfigNamesResp TODO
type QueryConfigNamesResp struct {
	ConfFile  string                  `json:"conf_file"`
	ConfNames map[string]*ConfNameDef `json:"conf_names" form:"conf_names"`
} // @name QueryConfigNamesResp

// QueryConfigTypeReq TODO
type QueryConfigTypeReq struct {
	Namespace string `json:"namespace" form:"namespace" validate:"required" example:"tendbha"`
	ConfType  string `json:"conf_type" form:"conf_type" validate:"required" example:"dbconf"`
	ConfFile  string `json:"conf_file" form:"conf_file"`
} // @name QueryConfigTypeReq

// QueryConfigTypeResp TODO
type QueryConfigTypeResp struct {
	ConfTypeInfo *ConfTypeDef      `json:"conf_type_info"`
	ConfFiles    map[string]string `json:"conf_files"`
	ConfLevels   map[string]string `json:"conf_levels"`
} // @name QueryConfigTypeResp
