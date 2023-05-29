// Package handler TODO
package handler

import "github.com/valyala/fasthttp"

// AddToHandlers TODO
var AddToHandlers map[string]func(ctx *fasthttp.RequestCtx)

// ApiHandler TODO
type ApiHandler struct {
	Url     string
	Handler func(ctx *fasthttp.RequestCtx)
}

// AddToApiManager TODO
func AddToApiManager(m ApiHandler) {
	if AddToHandlers == nil {
		AddToHandlers = make(map[string]func(ctx *fasthttp.RequestCtx))
	}
	AddToHandlers[m.Url] = m.Handler
}
