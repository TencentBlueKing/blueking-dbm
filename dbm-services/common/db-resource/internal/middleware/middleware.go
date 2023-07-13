// Package middleware TODO
package middleware

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"net/http"
	"time"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

type bodyLogWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

// Write 用于常见IO
func (w bodyLogWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// BodyLogMiddleware TODO
func BodyLogMiddleware(c *gin.Context) {
	blw := &bodyLogWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
	c.Writer = blw
	c.Next()
	statusCode := c.Writer.Status()
	// if statusCode >= 400 {
	// ok this is an request with error, let's make a record for it
	// now print body (or log in your preferred way)
	var rp controller.Response
	if blw.body == nil {
		rp = controller.Response{}
	} else {
		if err := json.Unmarshal(blw.body.Bytes(), &rp); err != nil {
			logger.Error("unmarshal respone body failed %s", err.Error())
			return
		}
	}
	if err := model.UpdateTbRequestLog(rp.RequestId, map[string]interface{}{"respone_body": blw.body.String(),
		"respone_code": statusCode, "update_time": time.Now()}); err != nil {
		logger.Warn("update request respone failed %s", err.Error())
	}
}

// ApiLogger TODO
func ApiLogger(c *gin.Context) {
	rid := requestid.Get(c)
	c.Set("request_id", rid)
	if c.Request.Method == http.MethodPost {
		// 记录重要api请求日志
		if !cmutil.HasElem(c.Request.RequestURI, []string{"/resource/pre-apply", "/resource/import", "/resource/apply",
			"/resource/confirm/apply", "/resource/update"}) {
			return
		}
		var bodyBytes []byte
		// read from the original request body
		bodyBytes, err := ioutil.ReadAll(c.Request.Body)
		if err != nil {
			return
		}
		if len(bodyBytes) <= 0 {
			bodyBytes = []byte("{}")
		}
		// create a new buffer and replace the original request body
		c.Request.Body = ioutil.NopCloser(bytes.NewBuffer(bodyBytes))
		if err := model.CreateTbRequestLog(model.TbRequestLog{
			RequestID:   rid,
			RequestUser: "",
			RequestUrl:  c.Request.RequestURI,
			RequestBody: string(bodyBytes),
			SourceIP:    c.Request.RemoteAddr,
			CreateTime:  time.Now(),
			ResponeBody: "{}",
		}); err != nil {
			logger.Warn("record request log failed %s", err.Error())
		}
	}
}
