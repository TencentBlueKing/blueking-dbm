package safego

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
)

// Shutdowner TODO
type Shutdowner interface {
	Shutdown(context.Context) error
}

// Graceful TODO
func Graceful(ctx context.Context, s Shutdowner) error {
	// Wait for interrupt signal to gracefully shutdown the server with
	// a timeout of ctxutil.
	quit := make(chan os.Signal, 1)

	// kill (no param) default send syscall.SIGTERM
	// kill -2 is syscall.SIGINT
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	<-quit
	log.Printf("Shutting down all...")

	err := s.Shutdown(ctx)
	if err != nil {
		log.Fatalf("Forced to shutdown: %v", err)
	}

	return err
}
