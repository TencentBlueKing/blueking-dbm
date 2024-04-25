package service

import (
	"crypto/md5"
	"encoding/hex"
	"net/http"
	"slow-query-parser-service/pkg/listener"
	"strings"

	"github.com/gin-gonic/gin"
)

func Handler(ctx *gin.Context) {
	body := Request{}
	err := ctx.BindJSON(&body)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, err.Error())
		return
	}

	res, err := ParseQuery(body.Content)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, err.Error())
		return
	}
	ctx.JSON(http.StatusOK, res)
}

func ParseQuery(rawSql string) (*Response, error) {
	l := listener.NewSqlListener(rawSql)
	if l.Err() != nil {
		return nil, l.Err()
	}

	h := md5.New()
	h.Write([]byte(l.ReplacedSql()))

	return &Response{
		Command:         l.Cmd,
		TableName:       strings.Join(l.Tables, ","),
		DbName:          strings.Join(l.Databases, ","),
		QueryString:     rawSql,
		QueryDigestText: l.ReplacedSql(),
		QueryDigestMd5:  hex.EncodeToString(h.Sum(nil)),
		QueryLength:     len(rawSql),
	}, nil
}
