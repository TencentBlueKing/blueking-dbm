package controller

import (
	"encoding/json"
	dbserrors "k8s-dbs/errors"
	"k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/request"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

type batchClusterProviderStub struct {
	provider.K8sCrdClusterProvider
	find func([]uint64) ([]*entity.K8sCrdClusterEntity, error)
}

func (p *batchClusterProviderStub) FindByDbmClusterIDs(ids []uint64) ([]*entity.K8sCrdClusterEntity, error) {
	return p.find(ids)
}

func TestBatchGetClusterInfoByClusterIDsNotFound(t *testing.T) {
	stub := &batchClusterProviderStub{find: func(ids []uint64) ([]*entity.K8sCrdClusterEntity, error) {
		require.Equal(t, []uint64{999}, ids)
		return []*entity.K8sCrdClusterEntity{}, nil
	}}
	w := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(w)
	ctx.Request = httptest.NewRequest(http.MethodPost, "/metadata/cluster/dbm/batch",
		strings.NewReader(`{"clusterIds":[999]}`))
	ctx.Request.Header.Set("Content-Type", "application/json")
	NewClusterController(stub).BatchGetClusterInfoByClusterIDs(ctx)

	require.Equal(t, http.StatusOK, w.Code)
	require.JSONEq(t, `{"result":true,"code":200,"data":[],"message":"success","error":null}`, w.Body.String())
}

func TestBatchGetClusterInfoByClusterIDs(t *testing.T) {
	tests := []struct {
		name     string
		count    int
		wantCode dbserrors.ErrorCode
	}{
		{name: "maximum", count: request.MaxBatchClusterIDs, wantCode: http.StatusOK},
		{name: "over_limit", count: request.MaxBatchClusterIDs + 1, wantCode: dbserrors.ParameterInvalidError},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ids := make([]uint64, tt.count)
			for idx := range ids {
				ids[idx] = uint64(idx + 1)
			}
			body, err := json.Marshal(request.BatchGetClusterRequest{ClusterIDs: ids})
			require.NoError(t, err)
			called := false
			stub := &batchClusterProviderStub{find: func(clusterIDs []uint64) ([]*entity.K8sCrdClusterEntity, error) {
				called = true
				require.Equal(t, ids, clusterIDs)
				return []*entity.K8sCrdClusterEntity{}, nil
			}}
			w := httptest.NewRecorder()
			ctx, _ := gin.CreateTestContext(w)
			ctx.Request = httptest.NewRequest(http.MethodPost, "/metadata/cluster/dbm/batch", strings.NewReader(string(body)))
			ctx.Request.Header.Set("Content-Type", "application/json")
			NewClusterController(stub).BatchGetClusterInfoByClusterIDs(ctx)

			require.Equal(t, http.StatusOK, w.Code)
			require.Equal(t, tt.wantCode == http.StatusOK, called)
			var result struct {
				Result bool                `json:"result"`
				Code   dbserrors.ErrorCode `json:"code"`
			}
			require.NoError(t, json.Unmarshal(w.Body.Bytes(), &result))
			require.Equal(t, tt.wantCode, result.Code)
			require.Equal(t, tt.wantCode == http.StatusOK, result.Result)
		})
	}
}
