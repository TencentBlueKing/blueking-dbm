package main

import (
	"bytes"
	"io"
	"io/ioutil"
	"net/http"
	"os"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
	"dbm-services/mysql/db-simulation/router"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

var buildstamp = ""
var githash = ""
var version = ""

func main() {
	app := gin.New()
	pprof.Register(app)
	app.Use(requestid.New())
	app.Use(apiLogger)
	router.RegisterRouter(app)
	app.POST("/app", func(ctx *gin.Context) {
		ctx.SecureJSON(http.StatusOK, map[string]interface{}{"buildstamp": buildstamp, "githash": githash,
			"version": version})
	})
	app.Run(config.GAppConfig.ListenAddr)
}

func init() {
	logger.New(os.Stdout, true, logger.InfoLevel, map[string]string{})
	defer logger.Sync()
}

// apiLogger TODO
func apiLogger(c *gin.Context) {
	rid := requestid.Get(c)
	c.Set("request_id", rid)
	var buf bytes.Buffer
	if c.Request.Method == http.MethodPost {
		tee := io.TeeReader(c.Request.Body, &buf)
		body, _ := ioutil.ReadAll(tee)
		c.Request.Body = ioutil.NopCloser(&buf)
		model.CreateRequestRecord(rid, string(body))
	}
	c.Next()
}
