package api

import (
	"bk-dbconfig/pkg/validatestruct"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/validate"
)

// ChangeConfNameDefReq update/add/remove a conf_name definition for conf_file
type ChangeConfNameDefReq struct {
	BaseConfFileDef
	ConfNames []*UpsertConfNames `json:"conf_names" form:"conf_names"`
	// OpUser, if empty, use system,get it from Header
	OpUser string `json:"op_user" form:"op_user"`
}

// Validate validate
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
			return errors.WithMessagef(err, c.ConfName)
		}
	}
	return nil
}

// AddConfFileReq add a new conf_file definition
type AddConfFileReq struct {
	ConfFileDef
}

// RemoveConfFileReq remove a conf_file definition
type RemoveConfFileReq struct {
	BaseConfFileDef
}
