package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service"
	"encoding/json"
	"log/slog"
)

type CloneInstancePrivPara struct {
	*service.CloneInstancePrivPara
	sourceMySQLVersion int
	targetMySQLVersion int
	SystemUsers        []string `json:"system_users"`
	Uid                string   `json:"uid"`
	NodeId             string   `json:"node_id"`
	RootId             string   `json:"root_id"`
	VersionId          string   `json:"version_id"`
	logger             *slog.Logger
}

func (c *CloneInstancePrivPara) Json() string {
	b, _ := json.Marshal(c)
	return string(b)
}

func (c *CloneInstancePrivPara) Init() {
	c.logger = slog.Default().With(
		"handler", "clone instance priv v2",
		"uid", c.Uid,
		"node_id", c.NodeId,
		"root_id", c.RootId,
		"version_id", c.VersionId,
	)
}
