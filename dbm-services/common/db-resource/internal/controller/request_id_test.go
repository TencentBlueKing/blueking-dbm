package controller

import (
	"encoding/json"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestSendResponseUsesContextRequestID(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Set("request_id", "92d84bc7-f74e-453f-9a70-e4ca40f0ac0b")

	var handler BaseHandler
	handler.SendResponse(c, nil, []string{"tlinux-1.2"})

	var got Response
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got.RequestId != "92d84bc7-f74e-453f-9a70-e4ca40f0ac0b" {
		t.Fatalf("request_id=%s", got.RequestId)
	}
}
