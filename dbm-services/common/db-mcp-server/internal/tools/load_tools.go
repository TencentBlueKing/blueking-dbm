package tools

import (
	"dbm-services/common/go-pubpkg/logger"
	"time"
	
	"github.com/avast/retry-go/v4"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func LoadTools(s *server.MCPServer) (err error) {
	var tds []*toolsDefinition
	err = retry.Do(
		func() error {
			tds, err = discover()
			if err != nil {
				return err
			}
			return nil
		},
		retry.Attempts(4),
		retry.Delay(5*time.Second),
		retry.DelayType(retry.FixedDelay),
		retry.OnRetry(
			func(n uint, err error) {
				logger.Warn("retry load tools %d on %s", n, err.Error())
			},
		),
	)
	
	if err != nil {
		return err
	}
	
	for _, td := range tds {
		tool := mcp.NewToolWithRawSchema(
			td.Name,
			td.Description,
			td.InputJsonSchema,
		)
		handler := toolHandlerFactory(td)
		s.AddTool(tool, handler)
		logger.Info("load tool: %s", td.String())
	}
	return nil
}
