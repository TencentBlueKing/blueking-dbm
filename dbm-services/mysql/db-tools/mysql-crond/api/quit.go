package api

import "github.com/pkg/errors"

// Quit TODO
func (m *Manager) Quit() error {
	_, err := m.do("/quit", "GET", nil)
	if err != nil {
		return errors.Wrap(err, "manager call /quit")
	}
	return nil
}
