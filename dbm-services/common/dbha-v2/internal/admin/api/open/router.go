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
	RegisterStrategyApi(strategyHandler, server)
	RegisterGlobalStrategyApi(strategyHandler, server)
}

// RegisterStrategyApi register strategy api
func RegisterStrategyApi(strategyHandler *handler.StrategyHandler, server *hanet.GinHTTPServer) {
	group := "/api/admin/strategies"
	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPost,
		Path:    "/",
		Handler: strategyHandler.Create,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPost,
		Path:    "/batch/",
		Handler: strategyHandler.BatchCreate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/batch/",
		Handler: strategyHandler.BatchUpdate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodDelete,
		Path:    "/batch/",
		Handler: strategyHandler.BatchDelete,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/batch/status/",
		Handler: strategyHandler.BatchUpdateStatus,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodGet,
		Path:    "/eventnames/",
		Handler: strategyHandler.TriggerEventNamesList,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodGet,
		Path:    "/",
		Handler: strategyHandler.List,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodGet,
		Path:    "/:id/",
		Handler: strategyHandler.Get,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/:id/",
		Handler: strategyHandler.Update,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodDelete,
		Path:    "/:id/",
		Handler: strategyHandler.Delete,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/:id/status/",
		Handler: strategyHandler.StatusUpdate,
	})
}

// RegisterGlobalStrategyApi register global strategy api
func RegisterGlobalStrategyApi(strategyHandler *handler.StrategyHandler, server *hanet.GinHTTPServer) {
	group := "/api/admin/global/strategies"
	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodGet,
		Path:    "/",
		Handler: strategyHandler.GlobalList,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPost,
		Path:    "/",
		Handler: strategyHandler.GlobalCreate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodGet,
		Path:    "/:id/",
		Handler: strategyHandler.GlobalGet,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/:id/",
		Handler: strategyHandler.GlobalUpdate,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodDelete,
		Path:    "/:id/",
		Handler: strategyHandler.GlobalDelete,
	})

	server.RegisterAPI(&hanet.ResetAPI{
		Group:   group,
		Method:  hanet.HttpMethodPut,
		Path:    "/:id/status/",
		Handler: strategyHandler.GlobalStatusUpdate,
	})
}
