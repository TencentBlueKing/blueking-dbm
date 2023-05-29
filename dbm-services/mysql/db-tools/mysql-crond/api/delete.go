package api

import (
	"encoding/json"

	"github.com/pkg/errors"
)

// Delete TODO
func (m *Manager) Delete(name string, permanent bool) (int, error) {
	body := struct {
		Name      string `json:"name"`
		Permanent bool   `json:"permanent"`
	}{
		Name:      name,
		Permanent: permanent,
	}

	resp, err := m.do("/delete", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /delete")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /delete response")
	}

	return res.EntryId, nil
}
