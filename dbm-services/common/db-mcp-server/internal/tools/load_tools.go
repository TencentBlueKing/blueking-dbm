package tools

import (
	"bytes"
	"encoding/json"
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
	// 去重：已存在且内容(name/description/inputSchema/outputSchema)相同的工具跳过，
	// 只把真正新增/变更的工具批量 AddTools，避免每轮都给客户端狂发 tools/list_changed 通知
	var toAdd []server.ServerTool
	for _, td := range tds {
		tool := mcp.NewToolWithRawSchema(
			td.OperationId,
			td.Description,
			td.InputJsonSchema,
		)
		if len(td.OutputJsonSchema) > 0 {
			tool.RawOutputSchema = td.OutputJsonSchema
		}
		if existing := s.GetTool(td.OperationId); existing != nil {
			old, _ := json.Marshal(existing.Tool)
			neu, _ := json.Marshal(tool)
			if bytes.Equal(old, neu) {
				continue
			}
		}
		handler := toolHandlerFactory(td)
		toAdd = append(toAdd, server.ServerTool{Tool: tool, Handler: handler})
		//logger.Info("load tool: %s", td.OperationId)
	}
	if len(toAdd) > 0 {
		s.AddTools(toAdd...)
	}
	return nil
}
