package api

import (
	"encoding/json"

	"github.com/pkg/errors"
)

// Resume TODO
func (m *Manager) Resume(name string, permanent bool) (int, error) {
	body := struct {
		Name      string `json:"name"`
		Permanent bool   `json:"permanent"`
	}{
		Name:      name,
		Permanent: permanent,
	}

	resp, err := m.do("/resume", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /resume")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /resume response")
	}

	return res.EntryId, nil
}
