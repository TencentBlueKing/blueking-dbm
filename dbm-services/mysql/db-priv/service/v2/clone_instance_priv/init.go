package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service"
	"encoding/json"
)

type CloneInstancePrivPara struct {
	*service.CloneInstancePrivPara
	sourceMySQLVersion int
	targetMySQLVersion int
	SystemUsers        []string `json:"system_users"`
}

func (c *CloneInstancePrivPara) Json() string {
	b, _ := json.Marshal(c)
	return string(b)
}
