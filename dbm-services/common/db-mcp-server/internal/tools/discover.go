package tools

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/spf13/viper"
)

type discoverResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

type toolInfo struct {
	Path           string          `json:"path"`
	Description    string          `json:"description"`
	OperationId    string          `json:"operation_id"`
	RequestSchema  json.RawMessage `json:"request_schema"`
	ResponseSchema json.RawMessage `json:"response_schema"`
}

func discover() ([]*toolsDefinition, error) {
	discoveryUrl, err := url.JoinPath(
		viper.GetString("mcp-backend-base-url"), "/apis/ai/mcp/mcp-discovery/",
	)
	if err != nil {
		return nil, err
	}

	httpClient := &http.Client{
		Timeout: 1 * time.Second,
	}

	resp, err := httpClient.Get(discoveryUrl)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var tds []*toolsDefinition
	err = json.Unmarshal(body, &tds)
	if err != nil {
		return nil, err
	}

	//var tds []*toolsDefinition
	//err = json.Unmarshal(response.Data, &tds)
	//if err != nil {
	//	return nil, err
	//}
	return tds, nil

}
