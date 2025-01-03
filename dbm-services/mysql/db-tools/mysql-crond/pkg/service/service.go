// Package service TODO
package service

import (
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"github.com/pkg/errors"
	"github.com/robfig/cron"

	"dbm-services/mysql/db-tools/mysql-crond/api"
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
		"/entries", func(ctx *gin.Context) {
			name := ctx.Query("name")
			nameMatch := ctx.Query("name-match") // ctx.Request.URL.Query().Get
			status := ctx.Query("status")        // enabled,disabled
			var entries []*api.SimpleEntry
			var err error
			if name != "" { // handle param: name
				entry := crond.FindEntryByName(name)
				entries = append(entries, entry)
				ctx.JSON(http.StatusOK, gin.H{"entries": entries})
				return
			}
			entries, err = crond.FindEntryByNameLike(nameMatch, status) // handle param: name-match
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			} else {
				ctx.JSON(
					http.StatusOK, gin.H{
						"entries": entries,
					},
				)
			}
		},
	)
	r.POST(
		"/disable", func(ctx *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Disable(body.Name, *body.Permanent)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}

			ctx.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/schedule/change", func(ctx *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Schedule  string `json:"schedule" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			newJob := &config.ExternalJob{
				Name:     body.Name,
				Schedule: body.Schedule,
			}
			if _, err := cron.Parse(newJob.Schedule); err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest,
						errors.Wrapf(err, "invalid schedule format %s", newJob.Schedule)))
				return
			}

			entryID, err := crond.ScheduleChange(newJob, *body.Permanent)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}
			ctx.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/pause", func(ctx *gin.Context) {
			body := struct {
				Name     string        `json:"name" binding:"required"`
				Duration time.Duration `json:"duration" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Pause(body.Name, body.Duration)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}
			ctx.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/create_or_replace", func(ctx *gin.Context) {
			body := struct {
				Job       *config.ExternalJob `json:"job" binding:"required"`
				Permanent *bool               `json:"permanent" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}
			m.Lock()
			defer func() {
				m.Unlock()
			}()

			if !body.Job.Overlap {
				body.Job.SetupChannel( /*config.RuntimeConfig.Ip*/ )
			}

			entryID, err := crond.CreateOrReplace(body.Job, *body.Permanent)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}
			ctx.JSON(
				http.StatusOK, gin.H{
					"entry_id": entryID,
				},
			)
		},
	)
	r.POST(
		"/resume", func(ctx *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Resume(body.Name, *body.Permanent)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}

			ctx.JSON(
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
		"/delete", func(ctx *gin.Context) {
			body := struct {
				Name      string `json:"name" binding:"required"`
				Permanent *bool  `json:"permanent" binding:"required"`
			}{}
			err := ctx.BindJSON(&body)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusBadRequest,
					api.NewErrorResp(http.StatusBadRequest, errors.Wrap(err, "request param")))
				return
			}

			m.Lock()
			defer func() {
				m.Unlock()
			}()
			entryID, err := crond.Delete(body.Name, *body.Permanent)
			if err != nil {
				ctx.AbortWithStatusJSON(http.StatusInternalServerError, api.NewErrorResp(500, err))
				return
			}

			ctx.JSON(
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
