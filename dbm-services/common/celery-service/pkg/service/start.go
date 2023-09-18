package service

import (
	"time"

	"golang.org/x/exp/slog"

	"celery-service/pkg/asyncsession"
)

func Start(address string) error {
	err := Init()
	if err != nil {
		return err
	}

	go func() {
		for {
			select {
			case <-time.Tick(10 * time.Minute):
				asyncsession.SessionMap.Range(func(k, v any) bool {
					sessionID := k.(string)
					session := v.(*asyncsession.Session)
					if session.Done && session.StartAt.Add(1*time.Minute).Before(time.Now()) {
						logger.Info("clean session", slog.Any(sessionID, session))
						asyncsession.SessionMap.Delete(sessionID)
					}
					return true
				})
			}
		}
	}()

	return r.Run(address)
}
