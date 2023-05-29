// Package api TODO
package api

import (
	"net/http"
)

// Manager TODO
type Manager struct {
	apiUrl string
	client *http.Client
}

// NewManager TODO
func NewManager(apiUrl string) *Manager {
	return &Manager{
		apiUrl: apiUrl,
		client: &http.Client{},
	}
}
