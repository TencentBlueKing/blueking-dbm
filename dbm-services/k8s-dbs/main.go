package main

import (
	"context"
	"errors"
	"fmt"
	_ "k8s-dbs/docs"
	"k8s-dbs/src/core"
	"k8s-dbs/src/core/client"
	"k8s-dbs/src/router"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	gs "github.com/swaggo/gin-swagger"
)

// @title DBS API
// @version 1.0
// @description This is the API documentation for DBS project.
// @termsOfService http://swagger.io/terms/

// @contact.name API Support
// @contact.email support@example.com

// @license.name Apache 2.0
// @license.url http://www.apache.org/licenses/LICENSE-2.0.html

// @host localhost:8000
// @BasePath /api/v1

func main() {
	slog.Info("Start initial configuration...")

	if err := core.Init(); err != nil {
		log.Fatalf("Failed to initialize core: %v", err)
	}

	r := router.NewRouter(client.Db.GormDb)

	r.Engine.GET("/swagger/*any", gs.WrapHandler(swaggerFiles.Handler))

	slog.Info("Finish initial configuration...")

	startServer(r.Engine)
}

func startServer(r *gin.Engine) {
	server := &http.Server{
		Addr:    ":8000",
		Handler: r,
	}

	go func() {
		slog.Info("Start server...")
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("Failed to start server", "error", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	slog.Info("Shutdown Server ...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		slog.Error("Server forced to shutdown", "error", err)
		panic(fmt.Errorf("fatal error: %w", err)) // 触发 panic
	}

	slog.Info("Server exited properly")
}
