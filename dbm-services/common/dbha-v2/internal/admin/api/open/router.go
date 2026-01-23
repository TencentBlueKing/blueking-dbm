/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package open

import (
	"dbm-services/common/dbha-v2/internal/admin/api/open/handler"
	"dbm-services/common/dbha-v2/pkg/hanet"
)

// RegisterOpenAPI register open api
func RegisterOpenAPI(strategyHandler *handler.StrategyHandler, server *hanet.GinHTTPServer) {
	// Register strategy apis
	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPost,
		Path:    "/strategies/",
		Handler: strategyHandler.Create,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPost,
		Path:    "/strategies/batch/",
		Handler: strategyHandler.BatchCreate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPut,
		Path:    "/strategies/batch/",
		Handler: strategyHandler.BatchUpdate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodDelete,
		Path:    "/strategies/batch/",
		Handler: strategyHandler.BatchDelete,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPut,
		Path:    "/strategies/batch/status/",
		Handler: strategyHandler.BatchUpdateStatus,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodGet,
		Path:    "/strategies/",
		Handler: strategyHandler.List,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodGet,
		Path:    "/strategies/:id/",
		Handler: strategyHandler.Get,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPut,
		Path:    "/strategies/:id/",
		Handler: strategyHandler.Update,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodDelete,
		Path:    "/strategies/:id/",
		Handler: strategyHandler.Delete,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   "/api/admin",
		Method:  hanet.HttpMethodPut,
		Path:    "/strategies/:id/status/",
		Handler: strategyHandler.StatusUpdate,
	})
}
