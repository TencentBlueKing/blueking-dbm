package resp

import (
	"time"
)

type ClusterRequestRecordRespVo struct {
	ID            uint64    `json:"id"`
	RequestId     string    `json:"request_id"`
	RequestType   string    `json:"request_type"`
	RequestParams string    `json:"request_params"`
	Status        string    `json:"status"`
	Description   string    `json:"description"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
