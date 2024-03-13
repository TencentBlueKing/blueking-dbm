package common

import "encoding/json"

// MongoRole 角色
type MongoRole struct {
	Role string `json:"role"`
	Db   string `json:"db"`
}

// MongoUser 用户
type MongoUser struct {
	User  string       `json:"user"`
	Pwd   string       `json:"pwd"`
	Roles []*MongoRole `json:"roles"`
}

// NewMongoUser 生成结构体
func NewMongoUser() *MongoUser {
	return &MongoUser{}
}

// GetContent 转成json
func (m *MongoUser) GetContent() (string, error) {
	content, err := json.Marshal(m)
	if err != nil {
		return "", err
	}
	return string(content), nil
}

// NewMongoRole 生成结构体
func NewMongoRole() *MongoRole {
	return &MongoRole{}
}
