package api

import (
	"github.com/pkg/errors"
)

// SendMetrics TODO
func (m *Manager) SendMetrics(name string, value int64, dimension map[string]interface{}) error {
	body := struct {
		Name      string                 `json:"name"`
		Value     int64                  `json:"value"`
		Dimension map[string]interface{} `json:"dimension"`
	}{
		Name:      name,
		Value:     value,
		Dimension: dimension,
	}

	_, err := m.do("/beat/metrics", "POST", body)
	if err != nil {
		return errors.Wrap(err, "manager call /metrics")
	}
	return nil
}
