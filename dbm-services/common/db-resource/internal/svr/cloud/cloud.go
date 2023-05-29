// Package cloud TODO
package cloud

import (
	"dbm-services/common/db-resource/internal/svr/cloud/tencent"
	"fmt"
)

// Disker TODO
type Disker interface {
	// DescribeDisk TODO
	DescribeDisk(diskIds []string, region string) (diskTypeDic map[string]string, err error)
}

// NewDisker TODO
func NewDisker() (dr Disker, err error) {
	if tencent.TencentDisker.IsOk() {
		dr = tencent.TencentDisker
		return
	}
	return dr, fmt.Errorf("not found available cloud disker")
}
