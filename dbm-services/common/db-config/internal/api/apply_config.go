package api

import (
	"bk-dbconfig/pkg/validate"
)

// ApplyConfigItem TODO
type ApplyConfigItem struct {
	ConfName string `json:"conf_name"`
	// 新值
	ConfValue string `json:"conf_value"`
	// 旧值
	ValueBefore string `json:"value_before"`
	// 该配置项最近由哪个版本修改的
	UpdatedRevision string `json:"updated_revision"`
	// 是否需要重启
	NeedRestart bool `json:"need_restart"`
	// 配置项定义的描述
	Description string `json:"description"`
	OPType      string `json:"op_type"`
	// 该配置来源于哪个级别
	LevelNameFrom string `json:"level_name_from"`
	// 配置项是否被该级别锁定
	FlagLocked int8 `json:"flag_locked"`
	// 是否已经应用
	Applied int8 `json:"applied"`
}

// ApplyConfigInfoReq TODO
type ApplyConfigInfoReq struct {
	BaseConfigNode
}

// ConfigItemBase TODO
type ConfigItemBase struct {
	ConfName        string `json:"conf_name"`
	ConfValue       string `json:"conf_value"`
	UpdatedRevision string `json:"updated_revision"`
}

// ConfigNameBase TODO
type ConfigNameBase struct {
	ConfName     string `json:"conf_name"`
	ValueDefault string `json:"value_default"`
	ValueAllowed string `json:"value_allowed"`
	ValueType    string `json:"value_type"`
	NeedRestart  bool   `json:"need_restart"`
	Description  string `json:"description"`
}

// ApplyConfigInfoResp TODO
type ApplyConfigInfoResp struct {
	ConfigsDiff map[string]*ApplyConfigItem `json:"configs_diff"`

	// Configs       []*ConfigItemBase          `json:"configs"`
	// ConfigsBefore []*ConfigItemBase          `json:"configs_before"`
	// ConfigNames map[string]*ConfigNameBase `json:"config_names"`

	RevisionToApply string `json:"revision_toapply"`
	RevisionBefore  string `json:"revision_before"`
	VersionID       uint64 `json:"version_id"`
	NodeID          uint64 `json:"node_id"`
}

// Validate TODO
func (a *ApplyConfigInfoReq) Validate() error {
	if err := validate.GoValidateStruct(*a, true); err != nil {
		return err
	}
	return nil
}

// VersionStatReq godoc
type VersionStatReq struct {
	BKBizIDDef
	BaseConfFileDef
	BaseLevelsDef
}

// VersionStatResp godoc
type VersionStatResp struct {
	// map key 是查询的对象，values 是状态码
	LevelValues map[string][]int `json:"level_values"`
	// 状态吗说明
	StatusInfo map[int]string `json:"status_info"`
}

// VersionStatus TODO
type VersionStatus struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// StatusMap TODO
var StatusMap = map[int]string{
	1:  "最新发布版本 已应用",
	2:  "最新发布版本 未应用",
	3:  "配置异常: 没找到已发布版本",
	4:  "配置异常：没找到已应用版本",
	10: "待发布: 存在来自上层级的配置强制更新",
}

// Validate TODO
func (a *VersionStatReq) Validate() error {
	if err := validate.GoValidateStruct(*a, true); err != nil {
		return err
	}
	return nil
}

// ApplyConfigReq 修改版本状态为已应用
type ApplyConfigReq struct {
	BaseConfigNode
	// 新的已成功应用的版本，一般为上一个 已发布版本
	RevisionApplied string `json:"revision_applied" form:"revision_applied" validate:"required"`
}

// Validate TODO
func (a *ApplyConfigReq) Validate() error {
	if err := validate.GoValidateStruct(*a, true); err != nil {
		return err
	}
	return nil
}

// VersionApplyReq level_config版本应用
// level_config 应用，必须是全部配置项应用
type VersionApplyReq struct {
	BaseConfigNode
	// 新的将应用的版本，一般为上一个 已发布版本
	RevisionApply string `json:"revision_apply" form:"revision_apply" validate:"required"`
	// 要应用给哪些直属子级，给定的子级会保存并发布，没给定的会仅保存为 1 个版本
	// ChildApplied []string `json:"child_applied" form:"child_applied"`
}

// Validate TODO
func (a *VersionApplyReq) Validate() error {
	if err := validate.GoValidateStruct(*a, true); err != nil {
		return err
	}
	return nil
}

// BaseConfigNode godoc
// bk_biz_id, namespace, conf_type, conf_file, level_name, level_value => config node_id
type BaseConfigNode struct {
	BKBizIDDef
	BaseConfFileDef
	BaseLevelDef
}

// QueryConfigOptions TODO
type QueryConfigOptions struct {
	InheritFrom           string `json:"inherit_from"`
	Module                string `json:"module" form:"module"`
	Cluster               string `json:"cluster" form:"cluster"`
	ConfName              string `json:"conf_name" form:"conf_name"`
	ConfValue             string `json:"conf_value" form:"conf_value"`
	Generate              bool
	Decrypt               bool
	Format                string `json:"format"`
	View                  string `json:"view"`
	Description           string `json:"description"`
	CreatedBy             string `json:"createdBy"`
	RowsAffected          int
	FromNodeConfigApplied bool // 请求是否来自 level_config 的应用
}

// Set TODO
func (b *BaseConfigNode) Set(bkBizID, namespace, confType, confFile, levelName, levelValue string) {
	/*
	   levelNode := &BaseConfigNode{
	       BKBizIDDef: BKBizIDDef{
	           BKBizID: bkBizID,
	       },
	       BaseConfFileDef: BaseConfFileDef{
	           Namespace: namespace,
	           ConfType:  confType,
	           ConfFile:  confFile,
	       },
	       BaseLevelDef: BaseLevelDef{
	           LevelName: levelName,
	           LevelValue: levelValue,
	       },
	   },
	*/
	b.BKBizID = bkBizID
	b.Namespace = namespace
	b.ConfType = confType
	b.ConfFile = confFile
	b.LevelName = levelName
	b.LevelValue = levelValue
}

// ConfItemApplyReq versioned_config item 应用
// versioned_config 应用，可以选择应用了哪些 conf_name
type ConfItemApplyReq struct {
	BaseConfigNode
	NodeID uint64 `json:"node_id" form:"node_id"`
	// 已应用的版本
	RevisionApply string `json:"revision_apply" form:"revision_apply" validate:"required"`
	// 应用了哪些配置项
	ConfNames []string `json:"conf_names" form:"conf_names" validate:"required"`
}

// Validate TODO
func (a *ConfItemApplyReq) Validate() error {
	if err := validate.GoValidateStruct(*a, true); err != nil {
		return err
	}
	return nil
}
