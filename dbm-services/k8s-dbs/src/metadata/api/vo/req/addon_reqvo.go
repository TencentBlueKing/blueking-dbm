package req

import "time"

type K8sCrdAddonReqVo struct {
	AddonName     string    `json:"addon_name" binding:"required"`
	AddonCategory string    `json:"addon_category" binding:"required"`
	AddonType     string    `json:"addon_type" binding:"required"`
	Metadata      string    `json:"metadata"`
	Spec          string    `json:"spec"`
	Description   string    `json:"description" binding:"required"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
