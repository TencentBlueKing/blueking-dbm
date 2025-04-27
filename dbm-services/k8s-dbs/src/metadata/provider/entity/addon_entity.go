package entity

import "time"

type K8sCrdStorageAddonEntity struct {
	ID            uint64    `json:"id"`
	AddonName     string    `json:"addon_name"`
	AddonCategory string    `json:"addon_category"`
	AddonType     string    `json:"addon_type"`
	Metadata      string    `json:"metadata"`
	Spec          string    `json:"spec"`
	Active        bool      `json:"active"`
	Description   string    `json:"description"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
