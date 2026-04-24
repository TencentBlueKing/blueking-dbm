package rpc

import (
	"log/slog"
	"net/http"
	"sync"
	"time"

	"dbm-services/mysql/db-remote-service/pkg/config"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

type mysqlComplexRPCRequest struct {
	Payloads []*MySQLRPCRequest `json:"payloads" binding:"required"`
}

func ComplexHandler(c *gin.Context) {
	rid := requestid.Get(c)

	var req mysqlComplexRPCRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"code": 1,
			"data": "",
			"msg":  err.Error(),
		})
		return
	}

	totalAddresses := 0
	for _, p := range req.Payloads {
		p.TrimSpace()
		if p.ConnectTimeout <= 0 {
			p.ConnectTimeout = 2
		}
		if p.QueryTimeout <= 0 {
			p.QueryTimeout = 600
		}
		if p.Charset == "" {
			p.Charset = "default"
		}
		totalAddresses += len(p.Addresses)
	}

	slog.Info("v2 complex-rpc request",
		slog.String("request_id", rid),
		slog.Int("payloads", len(req.Payloads)),
		slog.Int("total_addresses", totalAddresses),
		slog.Any("payloads_detail", req.Payloads),
	)

	start := time.Now()
	user := config.RuntimeConfig.MySQLAdminUser
	password := config.RuntimeConfig.MySQLAdminPassword
	ctx := c.Request.Context()

	rChan := make(chan []MySQLOneAddressRPCResponse, len(req.Payloads))

	var wg sync.WaitGroup
	wg.Add(len(req.Payloads))

	for _, p := range req.Payloads {
		go func(p *MySQLRPCRequest) {
			defer wg.Done()
			res, _ := p.execute(ctx, user, password)
			rChan <- res
		}(p)
	}

	go func() {
		wg.Wait()
		close(rChan)
	}()

	var allRes []MySQLOneAddressRPCResponse
	for batch := range rChan {
		allRes = append(allRes, batch...)
	}

	slog.Info("v2 complex-rpc finished",
		slog.String("request_id", rid),
		slog.Duration("elapsed", time.Since(start)),
		slog.Any("response", allRes),
	)

	c.JSON(http.StatusOK, gin.H{
		"code": 0,
		"data": allRes,
		"msg":  "",
	})
}
