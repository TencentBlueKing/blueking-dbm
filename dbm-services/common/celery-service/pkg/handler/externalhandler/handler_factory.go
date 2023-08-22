package externalhandler

func ExternalHandlers() []*Handler {
	var handlers []*Handler
	for _, item := range externalItems {
		handlers = append(handlers, newHandler(item))
	}
	return handlers
}
