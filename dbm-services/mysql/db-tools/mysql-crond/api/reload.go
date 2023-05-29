package api

import "github.com/pkg/errors"

// Reload TODO
func (m *Manager) Reload() error {
	_, err := m.do("/config/reload", "GET", nil)
	if err != nil {
		return errors.Wrap(err, "manager call /reload")
	}
	return nil
}
