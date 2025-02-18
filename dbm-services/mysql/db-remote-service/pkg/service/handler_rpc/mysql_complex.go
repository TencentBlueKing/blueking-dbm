package handler_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/rpc_core"
	"dbm-services/mysql/db-remote-service/pkg/rpc_implement/mysql_rpc"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"sync"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

func MySQLComplexHandler(c *gin.Context) {
	requestId := requestid.Get(c)

	var postRequestsMap = make(map[string]*queryRequest)
	if err := c.ShouldBindJSON(&postRequestsMap); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"code":  1,
			"data":  "",
			"error": err.Error(),
		})
		return
	}
	slog.Info(
		"enter mysql complex rpc handler",
		slog.Any("original post requests", postRequestsMap),
		slog.String("request-id", requestId),
	)

	var allDupAddr []string
	for _, postReq := range postRequestsMap {
		postReq.TrimSpace()
		if len(postReq.Timezone) == 0 {
			postReq.Timezone = config.RuntimeConfig.Timezone
		}
		if postReq.ConnectTimeout <= 0 {
			postReq.ConnectTimeout = 2
		}
		if postReq.QueryTimeout <= 0 {
			postReq.QueryTimeout = 600
		}

		dupAddrs := findDuplicateAddresses(postReq.Addresses)

		if len(dupAddrs) > 0 {
			slog.Info(
				"duplicate address",
				slog.String("addresses", strings.Join(dupAddrs, ",")),
				slog.String("request-id", requestId),
			)
			allDupAddr = append(allDupAddr, dupAddrs...)
		}
	}
	if len(allDupAddr) > 0 {
		c.JSON(
			http.StatusBadRequest, gin.H{
				"code": 1,
				"data": "",
				"msg":  fmt.Sprintf("duplicate addresses %s in some sub request", allDupAddr),
			},
		)
	}

	slog.Info(
		"enter mysql complex rpc handler",
		slog.Any("fill default post requests", postRequestsMap),
		slog.String("request-id", requestId),
	)

	var respCollect []rpc_core.OneAddressResultType
	var respChan = make(chan rpc_core.OneAddressResultType)
	var quitChange = make(chan int)
	var bucketChan = make(chan int, 30)
	go func() {
		wg := sync.WaitGroup{}
		wg.Add(len(postRequestsMap))

		for _, postReq := range postRequestsMap {
			bucketChan <- 1
			go func(postReq *queryRequest) {
				defer func() {
					<-bucketChan
					wg.Done()
				}()
				rpcWrapper := rpc_core.NewRPCWrapper(
					postReq.Addresses, postReq.Cmds,
					config.RuntimeConfig.MySQLAdminUser, config.RuntimeConfig.MySQLAdminPassword,
					postReq.ConnectTimeout, postReq.QueryTimeout, postReq.Timezone, postReq.Force,
					&mysql_rpc.MySQLRPCEmbed{},
					requestId,
				)

				for _, r := range rpcWrapper.Run() {
					slog.Info("send response", slog.Any("result", r), slog.String("request-id", requestId))
					respChan <- r
				}
			}(postReq)
		}

		wg.Wait()
		quitChange <- 1
	}()

	for {
		select {
		case r := <-respChan:
			slog.Info("collected response", slog.Any("response", r), slog.String("request-id", requestId))
			respCollect = append(respCollect, r)
		case <-quitChange:
			slog.Info("finish", slog.Any("response", respCollect), slog.String("request-id", requestId))
			c.JSON(
				http.StatusOK, gin.H{
					"code": 0,
					"data": respCollect,
					"msg":  "",
				})
			return
		}
	}
}
