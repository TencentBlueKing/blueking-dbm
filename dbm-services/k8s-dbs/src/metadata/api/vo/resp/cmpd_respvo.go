package resp

import "time"

type K8sCrdCmpdRespVo struct {
	Id                      uint64    `json:"id"`
	AddonID                 uint64    `json:"addon_id"`
	ComponentDefinitionName string    `json:"componentdefinition_name" binding:"required"`
	Metadata                string    `json:"metadata"`
	Spec                    string    `json:"spec"`
	Active                  bool      `json:"active"`
	Description             string    `json:"description"`
	CreatedBy               string    `json:"created_by"`
	CreatedAt               time.Time `json:"created_at"`
	UpdatedBy               string    `json:"updated_by"`
	UpdatedAt               time.Time `json:"updated_at"`
}
