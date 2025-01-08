package api

import "bk-dbconfig/pkg/validate"

// BatchGetConfigItemReq TODO
// 批量获取多个对象的某一配置项
type BatchGetConfigItemReq struct {
	BaseConfFileDef
	LevelName string `json:"level_name" label:"level" form:"level_name" validate:"required,enums" enums:"instance,cluster,module,app"`
	// 批量对象，比如 ["1.1.1.1:6379", ""2.2.2.2:6379""]
	LevelValues []string `json:"level_values" form:"level_values"`
	// 指定要查询的 conf_name，目前仅支持一个
	ConfName  string `json:"conf_name" form:"conf_name" example:"requirepass"`
	confNames []string
} // @name BatchGetConfigItemReq

// BatchGetConfigItemResp TODO
type BatchGetConfigItemResp struct {
	BaseConfFileDef
	LevelName string `json:"level_name" example:"instance"`
	ConfName  string `json:"conf_name" example:"requirepass"`
	// content is a {level_value: conf_value} dict like {"1.1.1.1:6379":"xxx", "2.2.2.2:6379":"yyy"}
	// content is a {level_value: {conf_name:conf_value})
	Content map[string]map[string]string `json:"content"`
} // @name BatchGetConfigItemResp

// Validate TODO
func (v *BatchGetConfigItemReq) Validate() error {

	if err := validate.GoValidateStruct(*v, true); err != nil {
		return err
	}
	return nil
}
