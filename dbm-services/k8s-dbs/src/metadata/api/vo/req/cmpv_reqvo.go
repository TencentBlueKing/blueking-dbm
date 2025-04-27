package req

import "time"

type K8sCrdCmpvReqVo struct {
	AddonID              uint64    `json:"addon_id" binding:"required"`
	ComponentVersionName string    `json:"componentversion_name" binding:"required"`
	Metadata             string    `json:"metadata"`
	Spec                 string    `json:"spec"`
	Description          string    `json:"description" binding:"required"`
	CreatedBy            string    `json:"created_by"`
	CreatedAt            time.Time `json:"created_at"`
	UpdatedBy            string    `json:"updated_by"`
	UpdatedAt            time.Time `json:"updated_at"`
}
