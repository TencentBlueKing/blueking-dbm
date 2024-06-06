package common

import (
	"encoding/json"

	mapset "github.com/deckarep/golang-set"
)

// MongoRole 角色
type MongoRole struct {
	Role string `json:"role"`
	Db   string `json:"db"`
}

// Privileges 权限
type Privileges struct {
	Db         string   `json:"db"`
	Privileges []string `json:"privileges"`
}

// MongoUser26 用户
type MongoUser26 struct {
	User  string       `json:"user"`
	Pwd   string       `json:"pwd"`
	Roles []*MongoRole `json:"roles"`
}

// MongoUser24 用户
type MongoUser24 struct {
	User  string   `json:"user"`
	Pwd   string   `json:"pwd"`
	Roles []string `json:"roles"`
}

// MongoUser 用户
type MongoUser interface {
	Init(username string, password string, privileges []Privileges)
	GetContent() (string, error)
}

// NewMongoUser 生成结构体
func NewMongoUser(dbVersion float64) MongoUser {
	if dbVersion > 2.4 {
		return &MongoUser26{}
	}
	return &MongoUser24{}
}

// GetContent 转成json
func (m *MongoUser26) GetContent() (string, error) {
	content, err := json.Marshal(m)
	if err != nil {
		return "", err
	}
	return string(content), nil
}

// GetContent 转成json
func (n *MongoUser24) GetContent() (string, error) {
	content, err := json.Marshal(n)
	if err != nil {
		return "", err
	}
	return string(content), nil
}

// Init 初始化
func (m *MongoUser26) Init(username string, password string, privileges []Privileges) {
	m.User = username
	m.Pwd = password
	for _, dbPrivileges := range privileges {
		for _, privilege := range dbPrivileges.Privileges {
			role := NewMongoRole()
			role.Role = privilege
			role.Db = dbPrivileges.Db
			m.Roles = append(m.Roles, role)
		}
	}
}

// Init 初始化
func (n *MongoUser24) Init(username string, password string, privileges []Privileges) {
	n.User = username
	n.Pwd = password
	setPrivileges := mapset.NewSet()
	for _, dbPrivileges := range privileges {
		for _, privilege := range dbPrivileges.Privileges {
			setPrivileges.Add(privilege)
		}
	}
	for _, privilege := range setPrivileges.ToSlice() {
		n.Roles = append(n.Roles, privilege.(string))
	}
}

// NewMongoRole 生成结构体
func NewMongoRole() *MongoRole {
	return &MongoRole{}
}
