package resp

import "time"

type K8sCrdCdRespVo struct {
	Id                    uint64    `json:"id"`
	AddonID               uint64    `json:"addon_id"`
	ClusterDefinitionName string    `json:"clusterdefinition_name"`
	Metadata              string    `json:"metadata"`
	Spec                  string    `json:"spec"`
	Active                bool      `json:"active"`
	Description           string    `json:"description"`
	CreatedBy             string    `json:"created_by"`
	CreatedAt             time.Time `json:"created_at"`
	UpdatedBy             string    `json:"updated_by"`
	UpdatedAt             time.Time `json:"updated_at"`
}
