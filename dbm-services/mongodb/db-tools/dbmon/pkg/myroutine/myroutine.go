// Package myroutine 用于实现一个简单的线程池，用于控制后台任务
package myroutine

import (
	"fmt"
	"sync"

	"go.uber.org/zap"
)

// MyRoutine is a go routine.
type MyRoutine struct {
	Id           int
	Name         string
	stopped      bool
	deleted      bool
	deletedMutex sync.Mutex
	stoppedMutex sync.Mutex

	j Job
}

func (r *MyRoutine) MarkDeleted() {
	r.deletedMutex.Lock()
	defer r.deletedMutex.Unlock()
	r.deleted = true
}

// Run starts the routine.
func (r *MyRoutine) Run() {
	r.deletedMutex.Lock()
	if r.deleted {
		r.deletedMutex.Unlock()
		return
	}
	r.deletedMutex.Unlock()

	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	if !r.stopped {
		return
	}

	go func() {
		r.stopped = false
		r.j.Run()
		r.stopped = true
	}()

}

// IsStopped stops the routine.
func (r *MyRoutine) IsStopped() bool {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	return r.stopped
}

// Stop stops the routine.
func (r *MyRoutine) Stop() {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	if r.stopped {
		return
	}
	// try to stop the routine. may be failed.
	r.j.Stop()
}

// Job is a routine that can be run and stopped.
type Job interface {
	Run()
	Stop()
}

// Pool is a collection of routines.
type Pool struct {
	routines []*MyRoutine
	logger   *zap.Logger
}

// NewPool creates a new Pool.
func NewPool(logger *zap.Logger) *Pool {
	return &Pool{
		routines: make([]*MyRoutine, 0),
		logger:   logger,
	}
}

// Add adds a routine to the pool.
func (p *Pool) Add(name string, j Job) {
	for _, r := range p.routines {
		if r.Name == name {
			return
		}
	}
	r := &MyRoutine{
		Id:           len(p.routines),
		Name:         name,
		stopped:      true,
		deleted:      false,
		j:            j,
		stoppedMutex: sync.Mutex{},
		deletedMutex: sync.Mutex{},
	}
	p.routines = append(p.routines, r)
}

func (p *Pool) find(name string) *MyRoutine {
	for i := range p.routines {
		if p.routines[i].Name == name {
			return p.routines[i]
		}
	}
	return nil
}

// Stop stops a routine in the pool.
func (p *Pool) Stop(name string) {
	var r = p.find(name)
	if r == nil {
		p.logger.Warn(fmt.Sprintf("routine %s not found\n", name))
		return
	}
	r.Stop()
}

// Remove removes a routine from the pool.
func (p *Pool) Remove(name string) error {
	var r = p.find(name)
	if r == nil {
		return fmt.Errorf("routine %s not found", name)
	}
	// try stop routine
	r.Stop()
	// mark as removed
	r.MarkDeleted()
	for i := range p.routines {
		if p.routines[i].Name == r.Name {
			p.routines = append(p.routines[:i], p.routines[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("routine %s not found", name)
}

// StopAll stops all routines in the pool.
func (p *Pool) StopAll() {
	for _, r := range p.routines {
		r.Stop()
	}
}

// StartAll starts all routines in the pool.
func (p *Pool) StartAll() {
	for _, r := range p.routines {
		r.Run()
	}
}

// Status prints the status of all routines in the pool.
func (p *Pool) Status() {
	p.logger.Info(fmt.Sprintf("len(p.routines): %d", len(p.routines)))
	for i, r := range p.routines {
		p.logger.Info(fmt.Sprintf("routine idx:%d %s %+v", i, r.Name, r))
	}
}

// GetRoutineNames  prints the status of all routines in the pool.
func (p *Pool) GetRoutineNames() []string {
	var names []string
	for _, r := range p.routines {
		names = append(names, r.Name)
	}
	return names
}
