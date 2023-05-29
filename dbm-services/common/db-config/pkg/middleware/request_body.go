package middleware

import (
	"bytes"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// RequestLoggerMiddleware TODO
func RequestLoggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.Request.Method == http.MethodPost {
			var buf bytes.Buffer
			tee := io.TeeReader(c.Request.Body, &buf)
			body, _ := ioutil.ReadAll(tee)
			c.Request.Body = ioutil.NopCloser(&buf)
			log.Println(c.Request.RequestURI, simplifyHeader(c.Request.Header))
			log.Println("body:", string(body))
		} else {
			if !strings.HasPrefix(c.Request.RequestURI, "/ping") {
				log.Println(c.Request.RequestURI, simplifyHeader(c.Request.Header))
			}
		}
		c.Next()
	}
}

func simplifyHeader(header http.Header) http.Header {
	httpHeader := http.Header{}
	for k, v := range header {
		if k != "Cookie" {
			httpHeader[k] = v
		}
	}
	return httpHeader
}
