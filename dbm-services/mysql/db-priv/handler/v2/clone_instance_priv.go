package v2

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/handler"
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv"
	"encoding/json"
	"io"
	"log/slog"
	"strings"

	"github.com/gin-gonic/gin"
)

func CloneInstancePriv(c *gin.Context) {
	slog.Info("do CloneInstancePriv v2")

	var input clone_instance_priv.CloneInstancePrivPara
	ticket := strings.TrimPrefix(c.FullPath(), "/priv/v2")

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		handler.SendResponse(c, errno.ErrBind, err)
	}

	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		handler.SendResponse(c, errno.ErrBind, err)
		return
	}

	slog.Info(
		"clone instance priv",
		slog.String("body", string(body)),
		slog.String("unmarshal param", input.Json()),
	)

	err = input.CloneInstancePriv(string(body), ticket)
	handler.SendResponse(c, err, nil)
	return
}
