package rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"net/http"

	"github.com/gin-gonic/gin"
)

func Handler(c *gin.Context) {
	_ = config.GlobalLimiter.Wait(context.Background())

	req, err := BuildRequestWithDefault(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	res, err := req.do()
	if err != nil {
		c.JSON(
			http.StatusInternalServerError,
			gin.H{
				"code": 1,
				"data": res,
				"msg":  err.Error(),
			})
		return
	}

	c.JSON(
		http.StatusOK,
		gin.H{
			"code": 0,
			"data": res,
			"msg":  "",
		})
}
