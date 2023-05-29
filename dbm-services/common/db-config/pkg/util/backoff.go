package util

import (
	"fmt"
	"log"
	"math/rand"
	"runtime/debug"
	"time"

	"github.com/pkg/errors"
)

// Backoff TODO
func Backoff(fn func() error, retry uint, interval int) (attempt uint, err error) {

	defer func() {
		if r := recover(); r != nil {
			stack := fmt.Sprintf("your function panic! %v ;%s", r, string(debug.Stack()))
			err = errors.New(stack)
		}
	}()

	for n := uint(0); n <= retry; n++ {
		if n > 0 {
			attempt = n
			log.Printf("retry (attempt: #%d), error: %v", attempt, err)
		}

		err = fn()
		if err == nil {
			break
		}
		time.Sleep(time.Duration(interval) * time.Second)
	}

	return attempt, err
}

// RandomBackoff TODO
func RandomBackoff(fn func() error, retry uint, maxInterval int) (attempt uint, err error) {

	defer func() {
		if r := recover(); r != nil {
			stack := fmt.Sprintf("your function panic! %v ;%s", r, string(debug.Stack()))
			err = errors.New(stack)
		}
	}()

	if maxInterval < 3 {
		maxInterval = 3
	}
	for n := uint(0); n <= retry; n++ {
		if n > 0 {
			attempt = n
			log.Printf("retry (attempt: #%d), error: %v", attempt, err)
		}

		err = fn()
		if err == nil {
			break
		}
		rand.Seed(time.Now().Unix())
		currentInterval := 1 + rand.Intn(maxInterval-1)
		time.Sleep(time.Duration(currentInterval) * time.Second)
	}
	return attempt, err
}
