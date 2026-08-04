package tools

import (
	"slices"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"dbm-services/common/go-pubpkg/logger"
)

func LoadTools(s *server.MCPServer) (err error) {
	var tds []*toolsDefinition
	// 启动阶段发现失败时重试一次，避免首次拉取工具列表因瞬时抖动失败
	tds, err = discover()
	if err != nil {
		logger.Warn("load tools first try failed: %s, retry once...", err.Error())
		time.Sleep(2 * time.Second)
		tds, err = discover()
	}

	if err != nil {
		return err
	}

	for name, _ := range s.ListTools() {
		if slices.IndexFunc(
			tds, func(td *toolsDefinition) bool {
				return td.OperationId == name
			},
		) < 0 {
			s.DeleteTools(name)
		}
	}
	for _, td := range tds {
		tool := mcp.NewToolWithRawSchema(
			td.OperationId,
			td.Description,
			td.InputJsonSchema,
		)
		handler := toolHandlerFactory(td)
		s.AddTool(tool, handler)
		//logger.Info("load tool: %s", td.OperationId)
	}
	return nil
}
