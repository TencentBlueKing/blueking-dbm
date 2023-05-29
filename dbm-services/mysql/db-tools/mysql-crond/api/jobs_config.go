package api

import (
	"encoding/json"

	"github.com/pkg/errors"
)

// JobConfig TODO
func (m *Manager) JobConfig() (string, error) {
	resp, err := m.do("/config/jobs-config", "GET", nil)
	if err != nil {
		return "", errors.Wrap(err, "manager call /config/jobs-config")
	}

	res := struct {
		Path string `json:"path"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return "", errors.Wrap(err, "manager unmarshal /config/jobs-config response")
	}

	return res.Path, nil
}
