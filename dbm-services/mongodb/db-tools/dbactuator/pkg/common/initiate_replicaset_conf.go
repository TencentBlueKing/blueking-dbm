package common

import "encoding/json"

// JsonConfReplicaset 复制集配置
type JsonConfReplicaset struct {
	Id        string    `json:"_id"`
	ConfigSvr bool      `json:"configsvr"`
	Members   []*Member `json:"members"`
}

// Member 成员
type Member struct {
	Id       int    `json:"_id"`
	Host     string `json:"host"`
	Priority int    `json:"priority"`
	Hidden   bool   `json:"hidden"`
}

// NewJsonConfReplicaset 获取结构体
func NewJsonConfReplicaset() *JsonConfReplicaset {
	return &JsonConfReplicaset{}
}

// GetConfContent 获取配置内容
func (j *JsonConfReplicaset) GetConfContent() ([]byte, error) {
	confContent, err := json.Marshal(j)
	if err != nil {
		return nil, err
	}
	return confContent, nil
}

// NewMember 获取结构体
func NewMember() *Member {
	return &Member{}
}
