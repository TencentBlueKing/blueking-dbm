package api

import (
	"context"
	"net/http"
	"time"

	"github.com/pkg/errors"
)

func (m *Manager) UpdateInstanceInfo() error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer func() {
		cancel()
	}()

	errChan := make(chan error, 1)
	go func() {
		_, err := m.do("/third-party/update-instance-info", http.MethodGet, nil)
		errChan <- err
	}()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case err := <-errChan:
			if err != nil {
				return errors.Wrapf(err, "manager call %s", m.apiUrl)
			}
			return nil
		default:
		}
	}
}
