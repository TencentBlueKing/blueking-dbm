package api

import (
	"encoding/json"

	"github.com/pkg/errors"
)

// DisableByName TODO
func (m *Manager) DisableByName(name string, permanent bool) (int, error) {
	body := struct {
		Name      string `json:"name"`
		Permanent bool   `json:"permanent"`
	}{
		Name:      name,
		Permanent: permanent,
	}

	resp, err := m.do("/disable", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /disable")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /disable response")
	}

	return res.EntryId, nil
}
