package common

import "encoding/json"

// ReplicasetMemberAdd 复制集状态
type ReplicasetMemberAdd struct {
	Host     string `json:"host"` // ip:port
	Hidden   bool   `json:"hidden"`
	Priority int    `json:"priority"`
}

// NewReplicasetMemberAdd 生成结构体
func NewReplicasetMemberAdd() *ReplicasetMemberAdd {
	return &ReplicasetMemberAdd{}
}

// GetJson 获取json格式
func (t *ReplicasetMemberAdd) GetJson() (string, error) {
	byteInfo, err := json.Marshal(t)
	if err != nil {
		return "", err
	}
	return string(byteInfo), nil
}
