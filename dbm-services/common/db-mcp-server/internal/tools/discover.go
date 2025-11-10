package tools

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	
	"github.com/spf13/viper"
)

type discoverResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

func discover() ([]*toolsDefinition, error) {
	discoveryUrl, err := url.JoinPath(
		viper.GetString("mcp-backend-base-url"), "list_handlers/",
	)
	if err != nil {
		return nil, err
	}
	
	resp, err := http.Get(discoveryUrl)
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
	
	var response discoverResponse
	err = json.Unmarshal(body, &response)
	if err != nil {
		return nil, err
	}
	
	var tds []*toolsDefinition
	err = json.Unmarshal(response.Data, &tds)
	if err != nil {
		return nil, err
	}
	return tds, nil
	
}
