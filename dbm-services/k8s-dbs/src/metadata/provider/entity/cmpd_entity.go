package entity

import "time"

type K8sCrdComponentDefinitionEntity struct {
	ID                      uint64    `json:"id"`
	AddonID                 uint64    `json:"addon_id"`
	ComponentDefinitionName string    `json:"componentdefinition_name"`
	DefaultVersion          string    `json:"default_version"`
	Metadata                string    `json:"metadata"`
	Spec                    string    `json:"spec"`
	Active                  bool      `json:"active"`
	Description             string    `json:"description"`
	CreatedBy               string    `json:"created_by"`
	CreatedAt               time.Time `json:"created_at"`
	UpdatedBy               string    `json:"updated_by"`
	UpdatedAt               time.Time `json:"updated_at"`
}
