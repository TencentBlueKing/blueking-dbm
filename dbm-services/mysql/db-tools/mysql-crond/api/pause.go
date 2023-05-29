package api

import (
	"encoding/json"
	"time"

	"github.com/pkg/errors"
)

// Pause TODO
func (m *Manager) Pause(name string, duration time.Duration) (int, error) {
	body := struct {
		Name     string        `json:"name"`
		Duration time.Duration `json:"duration"`
	}{
		Name:     name,
		Duration: duration,
	}

	resp, err := m.do("/pause", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /pause")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /pause response")
	}

	return res.EntryId, nil
}
