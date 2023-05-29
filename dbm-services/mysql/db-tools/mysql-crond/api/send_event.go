package api

import (
	"github.com/pkg/errors"
)

// SendEvent TODO
func (m *Manager) SendEvent(name string, content string, dimension map[string]interface{}) error {
	body := struct {
		Name      string                 `json:"name"`
		Content   string                 `json:"content"`
		Dimension map[string]interface{} `json:"dimension"`
	}{
		Name:      name,
		Content:   content,
		Dimension: dimension,
	}

	_, err := m.do("/beat/event", "POST", body)
	if err != nil {
		return errors.Wrap(err, "manager call /event")
	}
	return nil
}
