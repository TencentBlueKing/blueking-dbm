package plat

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/validatestruct"

	"dbm-services/common/go-pubpkg/validate"
)

// AddConfNameReq add a conf_name to  conf_file definition
type AddConfNameReq struct {
	api.BaseConfFileDef
	ConfNames []*api.ConfNameDef `json:"conf_names" form:"conf_names"`
}

// RemoveConfNameReq remove a conf_name from  conf_file definition
type RemoveConfNameReq struct {
	api.BaseConfFileDef
	ConfNames []string `json:"conf_names" form:"conf_names"`
}

// ChangeConfNameDefReq update/add/remove a conf_name definition for conf_file
type ChangeConfNameDefReq struct {
	api.BaseConfFileDef
	ConfNames []*api.UpsertConfNames `json:"conf_names" form:"conf_names"`
}

func (f *ChangeConfNameDefReq) Validate() error {
	if err := validate.GoValidateStruct(*f, true); err != nil {
		return err
	}
	for _, c := range f.ConfNames {
		if err := validate.GoValidateStruct(*c, true); err != nil {
			return err
		}
		valueTypeSub := validatestruct.ValueTypeDef{ValueType: c.ValueType, ValueTypeSub: c.ValueTypeSub}
		if err := valueTypeSub.Validate(); err != nil {
			return err
		}
	}
	return nil
}

// AddConfFileReq add a new conf_file definition
type AddConfFileReq struct {
	api.ConfFileDef
}

// RemoveConfFileReq remove a conf_file definition
type RemoveConfFileReq struct {
	api.BaseConfFileDef
}
