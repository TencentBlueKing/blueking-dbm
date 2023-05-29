// Package service TODO
package service

import (
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/crond"

	"github.com/gin-gonic/gin"
)

// Start TODO
func Start(version string, buildStamp string, gitHash string, quit chan struct{}, m *sync.Mutex) error {
	r := gin.New()

	r.Use(
		func(context *gin.Context) {
			start := time.Now()
			path := context.Request.URL.Path
			query := context.Request.URL.RawQuery

			context.Next()

			cost := time.Since(start)
			slog.Info(
				path,
				slog.Int("status", context.Writer.Status()),
				slog.String("method", context.Request.Method),
				slog.String("path", path),
				slog.String("query", query),
				slog.String("ip", context.ClientIP()),
				slog.String("user-agent", context.Request.UserAgent()),
				slog.String("errors", context.Errors.ByType(gin.ErrorTypePrivate).String()),
				slog.Duration("cost", cost),
			)
		},
		gin.Recovery(),
	)

	r.GET(
		"/version", func(context *gin.Context) {
			context.JSON(
				http.StatusOK, gin.H{
					"version":         version,
					"build_timestamp": buildStamp,
					"git_hash":        gitHash,
				},
			)
		},
	)

	r.GET(
		"/entries", func(context *gin.Context) {
			context.JSON(
				http.StatusOK, gin.H{
					"entries": crond.ListEntry(),
				},
			)
		},
	)
	r.POST(
		"/disable", func(context *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Disable(body.Name, *body.Permanent)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}

			context.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/pause", func(context *gin.Context) {
			body := struct {
				Name     string        `json:"name" binding:"required"`
				Duration time.Duration `json:"duration" binding:"required"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Pause(body.Name, body.Duration)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}

			context.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/create_or_replace", func(context *gin.Context) {
			body := struct {
				Job       *config.ExternalJob `json:"job" binding:"required"`
				Permanent *bool               `json:"permanent" binding:"required"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				context.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"message": err.Error()})
				return
			}
			m.Lock()
			defer func() {
				m.Unlock()
			}()
			body.Job.SetupChannel( /*config.RuntimeConfig.Ip*/ )
			entryID, err := crond.CreateOrReplace(body.Job, *body.Permanent)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}

			context.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/resume", func(context *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Resume(body.Name, *body.Permanent)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}

			context.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.GET(
		"/disabled", func(context *gin.Context) {
			context.JSON(
				http.StatusOK, gin.H{
					"jobs": crond.ListDisabledJob(),
				},
			)
		},
	)
	r.POST(
		"/delete", func(context *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Delete(body.Name, *body.Permanent)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}

			context.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/beat/event", func(context *gin.Context) {
			body := struct {
				Name      string                 `json:"name" binding:"required"`
				Content   string                 `json:"content" binding:"required"`
				Dimension map[string]interface{} `json:"dimension,omitempty"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}
			slog.Debug("api beat event", slog.Any("body", body))
			err = config.SendEvent(body.Name, body.Content, body.Dimension)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}
			context.JSON(http.StatusOK, gin.H{})
		},
	)
	r.POST(
		"/beat/metrics", func(context *gin.Context) {
			body := struct {
				Name      string                 `json:"name" binding:"required"`
				Value     int64                  `json:"value" binding:"required"`
				Dimension map[string]interface{} `json:"dimension,omitempty"`
			}{}
			err := context.BindJSON(&body)
			if err != nil {
				_ = context.AbortWithError(http.StatusBadRequest, err)
				return
			}
			slog.Debug("api beat event", slog.Any("body", body))
			err = config.SendMetrics(body.Name, body.Value, body.Dimension)
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}
			context.JSON(http.StatusOK, gin.H{})
		},
	)
	r.GET(
		"/config/jobs-config", func(context *gin.Context) {
			context.JSON(
				http.StatusOK, gin.H{
					"path": config.RuntimeConfig.JobsConfigFile,
				},
			)
		},
	)
	r.GET(
		"/config/reload", func(context *gin.Context) {
			m.Lock()
			defer func() {
				m.Unlock()
			}()
			err := crond.Reload()
			if err != nil {
				_ = context.AbortWithError(http.StatusInternalServerError, err)
				return
			}
			context.JSON(http.StatusOK, gin.H{})
		},
	)
	r.GET(
		"/quit", func(context *gin.Context) {
			quit <- struct{}{}
			context.JSON(http.StatusOK, gin.H{})
		},
	)
	return r.Run(fmt.Sprintf("127.0.0.1:%d", config.RuntimeConfig.Port))
}
