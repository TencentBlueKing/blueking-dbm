package router

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"k8s-dbs/common"
	"k8s-dbs/common/utils"
	coreclient "k8s-dbs/core/client"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	metaprovider "k8s-dbs/metadata/provider"
	providerentity "k8s-dbs/metadata/provider/entity"
	"log/slog"
	"time"

	"github.com/gin-gonic/gin"
)

// skipPaths defines a map of API paths that should bypass middleware processing.
// The key is the path string and value indicates if the path should be skipped (true).
var skipPaths = map[string]bool{
	"/v4/dbs/cluster/describe":    true,
	"/v4/dbs/cluster/status":      true,
	"/v4/dbs/component/describe":  true,
	"/v4/dbs/opsRequest/describe": true,
	"/v4/dbs/opsRequest/status":   true,
}

// GlobalRequestMiddleware is a Gin middleware function that handles common request processing.
func GlobalRequestMiddleware(
	reqProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		startTime := time.Now()
		if skipPaths[ctx.Request.URL.Path] {
			ctx.Next()
			return
		}

		requestBody, request, err := readAndParseBody(ctx)
		if requestBody == nil {
			coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.ReadRequestBodyError, err))
			return
		}

		requestRecord := buildRequestRecord(ctx, requestBody)
		k8sClient, k8sConfig, err := createK8sClient(clusterConfigProvider, request)
		if k8sClient == nil {
			coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateK8sClientError, err))
			return
		}

		err = saveRequest(reqProvider, requestRecord)
		if err != nil {
			coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		}
		injectRequestContext(ctx, requestRecord, k8sConfig, k8sClient)

		ctx.Next()
		logRequestCompletion(ctx, startTime)
	}
}

func readAndParseBody(ctx *gin.Context) ([]byte, *coreentity.Request, error) {
	if ctx.Request.Body == nil {
		return nil, nil, nil
	}

	body, err := io.ReadAll(ctx.Request.Body)
	if err != nil {
		slog.Error("Failed to read request body", "path", ctx.Request.URL.Path, "error", err)
		return nil, nil, err
	}
	ctx.Request.Body = io.NopCloser(bytes.NewBuffer(body))

	var request coreentity.Request
	if err := json.Unmarshal(body, &request); err != nil {
		slog.Error("Invalid request format", "path", ctx.Request.URL.Path, "error", err)
		return nil, nil, err
	}
	return body, &request, nil
}

func buildRequestRecord(ctx *gin.Context, body []byte) *providerentity.ClusterRequestRecordEntity {
	return &providerentity.ClusterRequestRecordEntity{
		RequestID:     utils.RequestID(),
		RequestType:   fmt.Sprintf("%s %s", ctx.Request.Method, ctx.FullPath()),
		RequestParams: string(body),
	}
}

func createK8sClient(
	provider metaprovider.K8sClusterConfigProvider,
	request *coreentity.Request,
) (*coreclient.K8sClient, *providerentity.K8sClusterConfigEntity, error) {

	config, err := provider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		slog.Error("Failed to get cluster config", "cluster", request.K8sClusterName, "error", err)
		return nil, nil, fmt.Errorf("failed to get cluster config %s : %w", request.K8sClusterName, err)
	}

	client, err := coreclient.NewK8sClient(config)
	if err != nil {
		slog.Error("Failed to create K8s client", "cluster", request.K8sClusterName, "error", err)
		return nil, nil, fmt.Errorf("failed to create K8s client %s : %w", request.K8sClusterName, err)
	}
	return client, config, nil
}

func saveRequest(
	provider metaprovider.ClusterRequestRecordProvider,
	record *providerentity.ClusterRequestRecordEntity,
) error {
	if _, err := provider.CreateRequestRecord(record); err != nil {
		slog.Error("Request record save failed", "request_id", record.RequestID, "error", err)
		return fmt.Errorf("failed to create request entity : %w", err)
	}
	return nil
}

func injectRequestContext(ctx *gin.Context, record *providerentity.ClusterRequestRecordEntity,
	config *providerentity.K8sClusterConfigEntity, client *coreclient.K8sClient) {

	ctx.Set("requestCtx", &common.RequestContext{
		RequestID:        record.RequestID,
		K8sClusterConfig: config,
		K8sClient:        client,
	})
}

func logRequestCompletion(ctx *gin.Context, startTime time.Time) {
	latency := time.Since(startTime)
	slog.Info("Request completed",
		"path", ctx.Request.URL.Path,
		"status", ctx.Writer.Status(),
		"latency", latency,
	)
}
