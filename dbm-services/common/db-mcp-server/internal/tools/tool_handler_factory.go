package tools

import (
	"bytes"
	"context"
	"dbm-services/common/db-mcp-server/internal/backend"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/santhosh-tekuri/jsonschema/v6"
)

func toolHandlerFactory(td *toolsDefinition) func(
	ctx context.Context, request mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		err := validateSchema("input.json", request.Params.Arguments, td.InputJsonSchema)
		if err != nil {
			return nil, err
		}

		b, err := json.Marshal(request.Params.Arguments)
		if err != nil {
			return nil, err
		}

		var res []byte
		err = retry.Do(
			func() error {
				res, err = backend.Call(td.Path, b)
				if err != nil {
					return err
				}
				return nil
			},
			retry.Attempts(4),
			retry.DelayType(retry.FixedDelay),
			retry.Delay(2*time.Second),
			retry.OnRetry(
				func(n uint, err error) {
					logger.Info("retry call backend %d on %s", n, err.Error())
				},
			),
		)

		return mcp.NewToolResultText(string(res)), nil
	}
}

func validateSchema(url string, data any, rawSchema json.RawMessage) error {
	inst, err := jsonschema.UnmarshalJSON(bytes.NewReader(rawSchema))

	compiler := jsonschema.NewCompiler()
	err = compiler.AddResource(url, inst)
	if err != nil {
		return err
	}
	schema, err := compiler.Compile(url)
	if err != nil {
		return err
	}

	err = schema.Validate(data)
	if err != nil {
		return err
	}
	return nil
}
