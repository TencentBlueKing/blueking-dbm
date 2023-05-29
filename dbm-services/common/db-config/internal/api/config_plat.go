package api

import (
	"bk-dbconfig/pkg/validate"
)

// UpsertConfFilePlatReq TODO
// 如果 conf_file 已经存在，则报错
// 新建 conf_file，保存操作在 def 表，发布时进入 node 表，生成revision并发布
type UpsertConfFilePlatReq struct {
	RequestType
	// 保存时如果与下层级存在冲突，提示确认，用 confirm=1 重新请求
	Confirm int8 `json:"confirm" form:"confirm"`
	// 发布描述，只在 req_type=SaveAndPublish 时有效
	Description  string      `json:"description" form:"description"`
	ConfFileInfo ConfFileDef `json:"conf_file_info" form:"conf_file_info"`
	// 新建配置文件，第一次保存返回 file_id, 后续保存/发布 需传入 file_id
	FileID uint64 `json:"file_id" form:"file_id"`
	// 如果revision为空，表示第一次保存。每次 update 操作都会返回 revision，确保在这一轮编辑操作下都是操作这个revision
	// 已发布的 revision 不能编辑
	// Revision string `json:"revision" form:"revision"`
	ConfNames []*UpsertConfNames `json:"conf_names" form:"conf_names"`
}

// UpsertConfFilePlatResp TODO
type UpsertConfFilePlatResp struct {
	BaseConfFileDef
	// 新建配置文件，第一次保存返回 file_id, 后续保存/发布 需传入 file_id

	FileID uint64 `json:"file_id"`
	// 编辑配置文件，仅保存时不会产生 revision，保存并发布时才返回
	Revision    string `json:"revision"`
	IsPublished int8   `json:"is_published"`
}

// Validate TODO
func (f *UpsertConfFilePlatReq) Validate() error {
	if err := validate.GoValidateStruct(*f, true); err != nil {
		return err
	}
	for _, c := range f.ConfNames {
		if err := validate.GoValidateStruct(*c, true); err != nil {
			return err
		}
		valueTypeSub := validate.ValueTypeDef{ValueType: c.ValueType, ValueTypeSub: c.ValueTypeSub}
		if err := valueTypeSub.Validate(); err != nil {
			return err
		}
	}
	return nil
}
