package resp

import "time"

type K8sCrdCmpvRespVo struct {
	Id                   uint64    `json:"id"`
	AddonID              uint64    `json:"addon_id"`
	ComponentVersionName string    `json:"componentversion_name" binding:"required"`
	Metadata             string    `json:"metadata"`
	Spec                 string    `json:"spec"`
	Active               bool      `json:"active"`
	Description          string    `json:"description"`
	CreatedBy            string    `json:"created_by"`
	CreatedAt            time.Time `json:"created_at"`
	UpdatedBy            string    `json:"updated_by"`
	UpdatedAt            time.Time `json:"updated_at"`
}
