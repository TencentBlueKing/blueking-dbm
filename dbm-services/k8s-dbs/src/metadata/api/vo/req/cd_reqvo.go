package req

import "time"

type K8sCrdCdReqVo struct {
	AddonID               uint64    `json:"addon_id" binding:"required"`
	ClusterDefinitionName string    `json:"clusterdefinition_name" binding:"required"`
	Metadata              string    `json:"metadata"`
	Spec                  string    `json:"spec"`
	Description           string    `json:"description" binding:"required"`
	CreatedBy             string    `json:"created_by"`
	CreatedAt             time.Time `json:"created_at"`
	UpdatedBy             string    `json:"updated_by"`
	UpdatedAt             time.Time `json:"updated_at"`
}
