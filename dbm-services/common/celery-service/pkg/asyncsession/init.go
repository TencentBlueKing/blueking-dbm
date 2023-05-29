package asyncsession

import (
	"context"
	"sync"
	"time"
)

type Session struct {
	ID      string             `json:"id"`
	Message string             `json:"message"`
	Err     string             `json:"error"`
	Done    bool               `json:"done"`
	StartAt time.Time          `json:"start_at"`
	Cancel  context.CancelFunc `json:"-"`
}

var SessionMap sync.Map

func init() {
	SessionMap = sync.Map{}
}
