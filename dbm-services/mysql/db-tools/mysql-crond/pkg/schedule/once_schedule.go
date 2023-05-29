package schedule

import "time"

// OnceSchedule TODO
type OnceSchedule struct {
	next     time.Time
	executed bool
}

// Next TODO
func (s *OnceSchedule) Next(t time.Time) time.Time {
	if t.Before(s.next) {
		return s.next
	}
	s.executed = true
	return time.Time{}
}

// NewOnceSchedule TODO
func NewOnceSchedule(next time.Time) *OnceSchedule {
	return &OnceSchedule{
		next:     next,
		executed: false,
	}
}

// IsExecuted TODO
func (s *OnceSchedule) IsExecuted() bool {
	return s.executed
}
