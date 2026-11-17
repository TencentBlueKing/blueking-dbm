package controller

import (
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func TestBuildListParamsTimezone(t *testing.T) {
	t.Setenv("TZ", "Asia/Shanghai")
	tests := []struct {
		name    string
		start   string
		end     string
		wantErr bool
	}{
		{"empty", "", "", false},
		{"valid", "2026-11-11 17:08:14", "2026-11-11 17:08:20", false},
		{"start_only", "2026-11-11 17:08:14", "", false},
		{"end_only", "", "2026-11-11 17:08:20", false},
		{"invalid_start", "invalid", "", true},
		{"invalid_end", "", "invalid", true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			query := url.Values{"startTime": {tt.start}, "endTime": {tt.end}}
			ctx, _ := gin.CreateTestContext(httptest.NewRecorder())
			ctx.Request = httptest.NewRequest("GET", "/?"+query.Encode(), nil)
			controller := ClusterRequestRecordController{}
			params, err := controller.buildListParams(ctx)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected invalid time error")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if tt.start == "" {
				if !params.StartTime.IsZero() {
					t.Fatal("empty start time must remain zero")
				}
			} else if got := params.StartTime.UTC().Format(time.DateTime); got != "2026-11-11 09:08:14" {
				t.Fatalf("incorrect start time: %s", got)
			}
			if tt.end == "" {
				if !params.EndTime.IsZero() {
					t.Fatal("empty end time must remain zero")
				}
			} else if got := params.EndTime.UTC().Format(time.DateTime); got != "2026-11-11 09:08:20" {
				t.Fatalf("incorrect end time: %s", got)
			}
		})
	}
}
